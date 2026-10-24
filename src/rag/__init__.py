"""RAG(검색 증강 생성) 레이어.

내 프로필을 청크로 나눠 Chroma 벡터DB에 임베딩해두고,
공고 요구 역량과 관련된 청크만 검색해 매칭에 사용한다.
"""

from .profile_store import ProfileStore, chunk_profile

__all__ = ["ProfileStore", "chunk_profile"]
