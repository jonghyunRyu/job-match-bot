"""프로필 벡터 스토어 (Chroma + Gemini 임베딩).

흐름:
  1) profile.md를 섹션(마크다운 헤더) 단위 청크로 분할
  2) 각 청크를 Gemini 임베딩으로 벡터화해 Chroma에 저장
  3) 요구 역량을 쿼리로 관련 청크 top-k 검색

임베딩은 Gemini 어댑터(LLMClient.embed)를 통해 생성해 벤더 일관성을 유지한다.
Chroma에는 "직접 만든 임베딩"을 그대로 넣는다(Chroma 내장 임베딩 미사용).
"""

from __future__ import annotations

import hashlib
import re
from typing import List

from ..config import PROJECT_ROOT
from ..llm.base import LLMClient

# Chroma 로컬 영속 디렉터리 (.gitignore에 포함됨)
_CHROMA_DIR = PROJECT_ROOT / ".chroma"
_COLLECTION_NAME = "profile"


def chunk_profile(profile_text: str) -> List[str]:
    """프로필 텍스트를 의미 단위 청크로 분할한다.

    마크다운 헤더('#', '##', '###')를 경계로 섹션을 나눈다.
    각 섹션(헤더 + 본문)이 하나의 "경험/항목" 청크가 된다.
    헤더가 전혀 없으면 빈 줄(문단) 기준으로 나눈다.
    """
    text = profile_text.strip()
    if not text:
        return []

    # 헤더 라인 앞에서 분할 (헤더는 다음 청크의 시작이 되도록 유지)
    if re.search(r"^#{1,6}\s", text, flags=re.MULTILINE):
        parts = re.split(r"(?=^#{1,6}\s)", text, flags=re.MULTILINE)
    else:
        parts = re.split(r"\n\s*\n", text)

    chunks = [p.strip() for p in parts if p.strip()]
    # 너무 짧은 청크(헤더만 있는 경우 등)는 걸러낸다
    return [c for c in chunks if len(c) >= 10]


class ProfileStore:
    """프로필 청크를 임베딩해 저장하고 검색하는 벡터 스토어."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm
        self._client = None
        self._collection = None

    def _ensure_client(self) -> None:
        """Chroma 클라이언트를 지연 초기화한다."""
        if self._client is not None:
            return
        import chromadb

        self._client = chromadb.PersistentClient(path=str(_CHROMA_DIR))

    @staticmethod
    def _profile_hash(profile_text: str) -> str:
        """프로필 내용 해시. 내용이 바뀌면 재인덱싱 여부 판단에 쓴다."""
        return hashlib.sha256(profile_text.encode("utf-8")).hexdigest()[:16]

    def index(self, profile_text: str) -> int:
        """프로필을 청크로 나눠 임베딩 후 Chroma에 저장한다.

        같은 내용이 이미 인덱싱돼 있으면 건너뛴다(해시 비교).
        반환값: 저장된 청크 수.
        """
        self._ensure_client()
        chunks = chunk_profile(profile_text)
        if not chunks:
            return 0

        content_hash = self._profile_hash(profile_text)

        # 기존 컬렉션이 같은 해시로 인덱싱돼 있으면 재사용
        existing = self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        meta = existing.metadata or {}
        if (
            meta.get("profile_hash") == content_hash
            and existing.count() == len(chunks)
        ):
            self._collection = existing
            return existing.count()

        # 내용이 바뀌었으면 컬렉션을 새로 만든다
        self._client.delete_collection(_COLLECTION_NAME)
        self._collection = self._client.create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine", "profile_hash": content_hash},
        )

        embeddings = self._llm.embed(chunks, task_type="RETRIEVAL_DOCUMENT")
        self._collection.add(
            ids=[f"chunk-{i}" for i in range(len(chunks))],
            documents=chunks,
            embeddings=embeddings,
        )
        return len(chunks)

    def search(self, query: str, top_k: int = 4) -> List[str]:
        """쿼리와 관련된 프로필 청크를 top_k개 검색한다."""
        if self._collection is None:
            self._ensure_client()
            self._collection = self._client.get_or_create_collection(
                name=_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )

        count = self._collection.count()
        if count == 0:
            return []

        query_emb = self._llm.embed([query], task_type="RETRIEVAL_QUERY")[0]
        result = self._collection.query(
            query_embeddings=[query_emb],
            n_results=min(top_k, count),
        )
        docs = result.get("documents") or [[]]
        return docs[0]
