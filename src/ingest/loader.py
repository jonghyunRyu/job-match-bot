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


def load_pdf(data: bytes) -> JobInput:  # noqa: ARG001
    """PDF 처리 자리표시자 (2차 단계에서 구현).

    계획된 로직:
      1) pypdf로 텍스트 추출 시도
      2) 추출 글자가 거의 없으면(스캔형) pdf2image로 페이지를 이미지화
      3) 이미지 경로는 Gemini Vision으로 폴백
    """
    raise NotImplementedError("PDF 처리는 2차 단계에서 구현 예정입니다.")
