"""환경변수 로드 및 설정 중앙 관리."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# 프로젝트 루트 (src/config.py 기준 두 단계 위)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PROFILE_PATH = DATA_DIR / "profile.md"

# .env 로드 (있으면)
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    """런타임 설정. 환경변수에서 읽어온다."""

    def __init__(self) -> None:
        self.gemini_api_key: str = os.getenv("GEMINI_API_KEY", "").strip()
        self.gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-flash-latest").strip()
        self.gemini_embed_model: str = os.getenv(
            "GEMINI_EMBED_MODEL", "gemini-embedding-001"
        ).strip()
        # RAG 검색 시 매칭에 넣을 프로필 청크 수
        self.rag_top_k: int = int(os.getenv("RAG_TOP_K", "4"))
        # 일시적 서버 오류(503/429 등) 시 최대 재시도 횟수
        self.llm_max_retries: int = int(os.getenv("LLM_MAX_RETRIES", "4"))

    @property
    def has_api_key(self) -> bool:
        return bool(self.gemini_api_key) and self.gemini_api_key != "your_api_key_here"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """설정 싱글턴. 테스트에서 교체하려면 cache_clear() 사용."""
    return Settings()


def load_profile() -> str:
    """내 프로필 텍스트를 읽어온다. 1차 MVP의 매칭 기준 데이터."""
    if PROFILE_PATH.exists():
        return PROFILE_PATH.read_text(encoding="utf-8")
    return ""
