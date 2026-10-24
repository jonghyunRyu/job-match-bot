"""Gemini 구현 (google-genai 통합 SDK).

google-generativeai(구 SDK)는 2025-11-30 지원 종료되어 통합 SDK
google-genai 를 사용한다. 텍스트 + Vision 멀티모달을 모두 지원한다.
"""

from __future__ import annotations

import time
from functools import lru_cache
from typing import Callable, List, Optional, Type, TypeVar

from PIL.Image import Image
from pydantic import BaseModel

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from ..config import get_settings
from .base import LLMClient

T = TypeVar("T", bound=BaseModel)
R = TypeVar("R")

# 재시도할 일시적 서버 오류 상태 코드
#   429: 요청 과다(rate limit)
#   500: 내부 서버 오류
#   503: 일시적 과부하(UNAVAILABLE)
#   504: 게이트웨이 타임아웃
_RETRIABLE_STATUS = {429, 500, 503, 504}


def _status_of(exc: Exception) -> Optional[int]:
    """google-genai 예외에서 HTTP 상태 코드를 추출한다."""
    code = getattr(exc, "code", None)
    if isinstance(code, int):
        return code
    # 일부 버전은 status_code 속성을 사용
    code = getattr(exc, "status_code", None)
    return code if isinstance(code, int) else None


def _call_with_retry(fn: Callable[[], R], max_retries: int) -> R:
    """일시적 서버 오류(503/429 등)면 지수 백오프로 재시도한다.

    영구 오류(400 등)나 재시도 불가 오류는 즉시 다시 던진다.
    """
    attempt = 0
    while True:
        try:
            return fn()
        except genai_errors.APIError as exc:
            status = _status_of(exc)
            if status not in _RETRIABLE_STATUS or attempt >= max_retries:
                raise
            # 2, 4, 8, 16초... (최대 30초) 대기 후 재시도
            wait = min(2 ** (attempt + 1), 30)
            time.sleep(wait)
            attempt += 1


class GeminiClient(LLMClient):
    """Google Gemini 어댑터."""

    def __init__(
        self,
        api_key: str,
        model: str,
        embed_model: str,
        max_retries: int = 4,
    ) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._embed_model = embed_model
        self._max_retries = max_retries

    def _build_contents(
        self, prompt: str, images: Optional[List[Image]]
    ) -> list:
        """프롬프트와 이미지를 contents 리스트로 조립한다.

        google-genai 는 PIL.Image 객체를 contents 에 직접 넣는 것을 지원한다.
        """
        contents: list = [prompt]
        if images:
            contents.extend(images)
        return contents

    def generate_text(
        self,
        prompt: str,
        images: Optional[List[Image]] = None,
    ) -> str:
        response = _call_with_retry(
            lambda: self._client.models.generate_content(
                model=self._model,
                contents=self._build_contents(prompt, images),
            ),
            self._max_retries,
        )
        return (response.text or "").strip()

    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        images: Optional[List[Image]] = None,
    ) -> T:
        response = _call_with_retry(
            lambda: self._client.models.generate_content(
                model=self._model,
                contents=self._build_contents(prompt, images),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            ),
            self._max_retries,
        )
        # SDK가 response_schema로 파싱한 객체를 우선 사용
        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, schema):
            return parsed
        # 폴백: 원문 JSON을 직접 검증
        return schema.model_validate_json(response.text or "{}")

    def embed(
        self,
        texts: List[str],
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> List[List[float]]:
        if not texts:
            return []
        response = _call_with_retry(
            lambda: self._client.models.embed_content(
                model=self._embed_model,
                contents=texts,
                config=types.EmbedContentConfig(task_type=task_type),
            ),
            self._max_retries,
        )
        return [list(e.values) for e in response.embeddings]


@lru_cache(maxsize=1)
def get_llm() -> GeminiClient:
    """설정 기반 Gemini 어댑터 싱글턴.

    반환 타입을 LLMClient 로 다루면 벤더 교체 시 호출부 수정이 없다.
    """
    settings = get_settings()
    if not settings.has_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY가 설정되지 않았습니다. .env 파일에 키를 넣어주세요. "
            "(.env.example 참고)"
        )
    return GeminiClient(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        embed_model=settings.gemini_embed_model,
        max_retries=settings.llm_max_retries,
    )
