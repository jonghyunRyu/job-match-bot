"""LLM 어댑터 레이어.

벤더 종속을 피하기 위해 LLM 호출을 추상 인터페이스(LLMClient)로 감싼다.
파이프라인 코드는 base.LLMClient 타입에만 의존하므로,
Gemini를 다른 벤더로 교체해도 파이프라인은 수정할 필요가 없다.
"""

from .base import LLMClient
from .gemini import GeminiClient, get_llm

__all__ = ["LLMClient", "GeminiClient", "get_llm"]
