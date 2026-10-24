"""LLM 어댑터 인터페이스.

파이프라인은 이 추상 타입에만 의존한다. 구체 벤더(Gemini 등)는
이 인터페이스를 구현하기만 하면 교체 가능하다 (벤더 종속 회피).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Type, TypeVar

from PIL.Image import Image
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMClient(ABC):
    """LLM 호출 공통 인터페이스."""

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        images: Optional[List[Image]] = None,
    ) -> str:
        """프롬프트(+선택적 이미지)로 자유 텍스트를 생성한다."""
        raise NotImplementedError

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        images: Optional[List[Image]] = None,
    ) -> T:
        """프롬프트(+선택적 이미지)로 schema 타입의 구조화 결과를 생성한다.

        멀티모달 입력(이미지)을 함께 넘길 수 있어 Vision 추출에도 쓰인다.
        """
        raise NotImplementedError

    @abstractmethod
    def embed(
        self,
        texts: List[str],
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> List[List[float]]:
        """텍스트 목록을 임베딩 벡터 목록으로 변환한다 (RAG용).

        task_type: 임베딩 용도 힌트.
          - RETRIEVAL_DOCUMENT: 저장할 문서(프로필 청크) 임베딩
          - RETRIEVAL_QUERY: 검색 쿼리(요구 역량) 임베딩
        """
        raise NotImplementedError
