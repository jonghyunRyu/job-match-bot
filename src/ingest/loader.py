"""입력 타입 판별 및 정규화.

1차 MVP: 텍스트, 이미지 지원.
2차 단계: PDF (pypdf 텍스트 추출 → 글자 거의 없으면 pdf2image 이미지 폴백) 추가 예정.
파이프라인은 아래 JobInput 하나만 보면 되도록 입력을 통일한다.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import List, Optional

from PIL import Image as PILImage
from PIL.Image import Image

from ..schemas import InputType


@dataclass
class JobInput:
    """정규화된 공고 입력. 추출 단계는 이 형태만 소비한다."""

    input_type: InputType
    text: str = ""
    images: List[Image] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.text.strip() and not self.images


def load_text(raw: str) -> JobInput:
    """텍스트 입력을 정규화한다."""
    return JobInput(input_type=InputType.TEXT, text=raw.strip())


def load_image(data: bytes) -> JobInput:
    """이미지 바이트(업로드 캡처)를 PIL 이미지로 열어 정규화한다.

    OCR 라이브러리는 쓰지 않는다. Gemini Vision에 이미지를 직접 전달한다.
    """
    image = PILImage.open(io.BytesIO(data))
    # 일부 포맷(예: palette/P 모드) 호환을 위해 RGB로 변환
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    return JobInput(input_type=InputType.IMAGE, images=[image])


# 이 글자 수 미만이면 "스캔형(이미지) PDF"로 판단해 Vision 경로로 폴백한다.
_MIN_TEXT_CHARS = 50
# 스캔형 PDF를 이미지화할 때 Vision에 넘길 최대 페이지 수 (비용/속도 보호)
_MAX_PDF_PAGES = 5


class PdfProcessingError(RuntimeError):
    """PDF 처리 중 복구 불가능한 오류 (예: poppler 미설치)."""


def _extract_pdf_text(data: bytes) -> str:
    """pypdf로 PDF의 모든 페이지에서 텍스트를 추출한다."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    parts: List[str] = []
    for page in reader.pages:
        extracted = page.extract_text() or ""
        if extracted.strip():
            parts.append(extracted.strip())
    return "\n\n".join(parts).strip()


def _render_pdf_to_images(data: bytes) -> List[Image]:
    """스캔형 PDF를 페이지별 이미지로 변환한다 (pdf2image + poppler).

    poppler가 설치돼 있지 않으면 PdfProcessingError로 명확히 안내한다.
    """
    try:
        from pdf2image import convert_from_bytes
    except ImportError as exc:  # pragma: no cover - 의존성 미설치
        raise PdfProcessingError(
            "pdf2image가 설치되지 않았습니다. requirements.txt를 설치해주세요."
        ) from exc

    try:
        pages = convert_from_bytes(
            data, first_page=1, last_page=_MAX_PDF_PAGES
        )
    except Exception as exc:  # pdf2image는 poppler 미설치 시 여기서 실패
        raise PdfProcessingError(
            "PDF를 이미지로 변환하지 못했습니다. 스캔형 PDF 처리는 시스템에 "
            "poppler 설치가 필요합니다.\n"
            "  Windows: https://github.com/oschwartz10612/poppler-windows "
            "에서 받아 PATH에 등록하세요.\n"
            "  (대안: 공고를 텍스트로 붙여넣거나 이미지로 캡처해 올려주세요.)"
        ) from exc

    images: List[Image] = []
    for page in pages:
        images.append(page.convert("RGB") if page.mode not in ("RGB", "L") else page)
    return images


def load_pdf(data: bytes) -> JobInput:
    """PDF 입력을 정규화한다.

    로직:
      1) pypdf로 텍스트 추출 시도
      2) 추출 글자가 충분하면(텍스트형) 텍스트 경로로 처리
      3) 글자가 거의 없으면(스캔형) pdf2image로 페이지를 이미지화해 Vision 폴백
    """
    text = _extract_pdf_text(data)
    if len(text) >= _MIN_TEXT_CHARS:
        return JobInput(input_type=InputType.PDF, text=text)

    # 스캔형으로 판단 → 이미지 경로 폴백
    images = _render_pdf_to_images(data)
    if not images:
        raise PdfProcessingError(
            "PDF에서 텍스트도 이미지도 추출하지 못했습니다. "
            "다른 형식(텍스트/이미지)으로 입력해주세요."
        )
    return JobInput(input_type=InputType.PDF, images=images)
