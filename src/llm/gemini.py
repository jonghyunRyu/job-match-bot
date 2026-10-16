"""Gemini 구현 (google-genai 통합 SDK).

google-generativeai(구 SDK)는 2025-11-30 지원 종료되어 통합 SDK
google-genai 를 사용한다. 텍스트 + Vision 멀티모달을 모두 지원한다.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional, Type, TypeVar

from PIL.Image import Image
from pydantic import BaseModel

from google import genai
from google.genai import types

from ..config import get_settings
from .base import LLMClient

T = TypeVar("T", bound=BaseModel)


class GeminiClient(LLMClient):
    """Google Gemini 어댑터."""

    def __init__(self, api_key: str, model: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

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
        response = self._client.models.generate_content(
            model=self._model,
            contents=self._build_contents(prompt, images),
        )
        return (response.text or "").strip()

    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        images: Optional[List[Image]] = None,
    ) -> T:
        response = self._client.models.generate_content(
            model=self._model,
            contents=self._build_contents(prompt, images),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )
        # SDK가 response_schema로 파싱한 객체를 우선 사용
        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, schema):
            return parsed
        # 폴백: 원문 JSON을 직접 검증
        return schema.model_validate_json(response.text or "{}")


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
    return GeminiClient(api_key=settings.gemini_api_key, model=settings.gemini_model)
