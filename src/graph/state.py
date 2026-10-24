"""그래프 상태 정의.

노드들이 공유하는 데이터 묶음. 각 노드는 이 상태의 일부를 읽고,
자신이 만든 결과를 부분 업데이트(dict)로 반환한다.
"""

from __future__ import annotations

from typing import Optional, TypedDict

from ..ingest.loader import JobInput
from ..llm.base import LLMClient
from ..rag.profile_store import ProfileStore
from ..schemas import JobRequirements, MatchResult, Report


class MatchState(TypedDict, total=False):
    """파이프라인 그래프의 공유 상태.

    total=False: 모든 키가 항상 존재하지는 않음(노드가 점진적으로 채움).
    """

    # --- 입력 (그래프 호출 시 주어짐) ---
    job_input: JobInput
    profile_text: str
    llm: LLMClient
    store: Optional[ProfileStore]
    use_rag: bool

    # --- 노드가 채우는 중간/최종 산출물 ---
    requirements: JobRequirements
    match_result: MatchResult
    report: Report

    # --- 흐름 제어 ---
    error: str
