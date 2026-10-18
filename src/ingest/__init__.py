"""입력 수집 레이어: 공고 입력의 타입을 판별하고 공통 형태로 정규화한다."""

from .loader import (
    JobInput,
    PdfProcessingError,
    load_image,
    load_pdf,
    load_text,
)

__all__ = [
    "JobInput",
    "PdfProcessingError",
    "load_image",
    "load_pdf",
    "load_text",
]
