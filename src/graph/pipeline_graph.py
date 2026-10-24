"""파이프라인 상태 그래프 (LangGraph).

흐름:
    START → extract → [분기] → match → report → END
                         │
                         └─(요구 역량 없음)→ END

각 노드는 기존 pipeline 함수를 호출하는 얇은 래퍼다.
"""

from __future__ import annotations

from typing import Optional

from langgraph.graph import END, START, StateGraph

from ..ingest.loader import JobInput
from ..llm.base import LLMClient
from ..pipeline import build_report, extract_requirements, match_profile
from ..rag.profile_store import ProfileStore
from .state import MatchState


# --- 노드 정의 ---
# 각 노드는 상태의 일부를 읽고, 변경분(dict)만 반환한다.


def extract_node(state: MatchState) -> dict:
    """공고 입력에서 요구 역량을 추출한다."""
    requirements = extract_requirements(state["job_input"], state["llm"])
    return {"requirements": requirements}


def match_node(state: MatchState) -> dict:
    """요구 역량과 프로필을 매칭한다 (RAG 사용)."""
    match_result = match_profile(
        state["requirements"],
        state["profile_text"],
        state["llm"],
        store=state.get("store"),
        use_rag=state.get("use_rag", True),
    )
    return {"match_result": match_result}


def report_node(state: MatchState) -> dict:
    """매칭 결과로 리포트를 생성한다."""
    report = build_report(
        state["requirements"],
        state["match_result"],
        state["llm"],
    )
    return {"report": report}


# --- 조건 분기 ---


def _has_requirements(state: MatchState) -> str:
    """추출 결과에 역량이 하나라도 있으면 매칭으로, 없으면 종료로 분기."""
    req = state.get("requirements")
    if req and (req.required_skills or req.preferred_skills):
        return "match"
    return "end"


def build_graph():
    """파이프라인 상태 그래프를 구성하고 컴파일한다."""
    graph = StateGraph(MatchState)

    graph.add_node("extract", extract_node)
    graph.add_node("match", match_node)
    graph.add_node("report", report_node)

    graph.add_edge(START, "extract")
    # 추출 후: 역량이 있으면 match, 없으면 종료
    graph.add_conditional_edges(
        "extract",
        _has_requirements,
        {"match": "match", "end": END},
    )
    graph.add_edge("match", "report")
    graph.add_edge("report", END)

    return graph.compile()


# 컴파일된 그래프 재사용 (구조는 불변이므로 모듈 레벨 캐시)
_compiled_graph = None


def run_graph(
    job_input: JobInput,
    profile_text: str,
    llm: LLMClient,
    store: Optional[ProfileStore] = None,
    use_rag: bool = True,
) -> MatchState:
    """그래프를 실행해 추출→매칭→리포트를 수행하고 최종 상태를 반환한다."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()

    initial: MatchState = {
        "job_input": job_input,
        "profile_text": profile_text,
        "llm": llm,
        "store": store,
        "use_rag": use_rag,
    }
    return _compiled_graph.invoke(initial)
