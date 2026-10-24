"""매칭 분석 단계: 요구 역량 vs 내 프로필 → 매칭률/격차.

RAG 적용:
  - 프로필을 Chroma 벡터DB에 임베딩해두고, 공고 요구 역량과 관련된 청크만
    검색해 매칭 프롬프트에 넣는다 (프로필 전체를 통째로 넣지 않음).
  - 인덱싱/검색이 실패하거나 결과가 비면 프로필 전체 텍스트로 폴백한다(안정성).
"""

from __future__ import annotations

import json
from typing import Optional

from ..config import get_settings
from ..llm.base import LLMClient
from ..rag.profile_store import ProfileStore
from ..schemas import JobRequirements, MatchResult

_MATCH_PROMPT = """\
당신은 채용 매칭 분석가입니다.
아래 '요구 역량'과 '지원자 프로필(관련 경험)'을 비교해 매칭 결과를 산출하세요.

규칙:
- 각 요구 역량마다 프로필에 관련 경험이 있는지(matched) 판정하세요.
- matched=true면 evidence에 근거가 된 프로필 내용을 짧게 인용하세요.
- 필수 역량(is_required=true)은 우대 역량보다 매칭률에 더 크게 반영하세요.
- match_rate는 0~100 정수로, 필수 역량 충족도를 중심으로 산정하세요.
- strengths: 지원자가 특히 강한 부분. gaps: 부족해서 보완이 필요한 역량.
- 프로필에 없는 내용을 지어내지 마세요.

[요구 역량]
{requirements}

[지원자 프로필(관련 경험)]
{profile}
"""


def _requirements_to_query(requirements: JobRequirements) -> str:
    """요구 역량을 벡터 검색용 쿼리 문자열로 합친다."""
    names = [s.name for s in requirements.required_skills]
    names += [s.name for s in requirements.preferred_skills]
    parts = []
    if requirements.job_title:
        parts.append(requirements.job_title)
    if requirements.summary:
        parts.append(requirements.summary)
    parts.extend(names)
    return " / ".join(parts) if parts else (requirements.summary or "직무 역량")


def _retrieve_relevant_profile(
    requirements: JobRequirements,
    profile_text: str,
    llm: LLMClient,
    store: Optional[ProfileStore],
) -> str:
    """RAG로 관련 프로필 청크를 검색한다. 실패 시 전체 텍스트로 폴백."""
    settings = get_settings()
    try:
        store = store or ProfileStore(llm)
        store.index(profile_text)
        query = _requirements_to_query(requirements)
        chunks = store.search(query, top_k=settings.rag_top_k)
        if chunks:
            return "\n\n---\n\n".join(chunks)
    except Exception:
        # 벡터DB/임베딩 문제 시 조용히 전체 텍스트로 폴백 (매칭 자체는 계속 동작)
        pass
    return profile_text


def match_profile(
    requirements: JobRequirements,
    profile_text: str,
    llm: LLMClient,
    store: Optional[ProfileStore] = None,
    use_rag: bool = True,
) -> MatchResult:
    """요구 역량과 프로필을 비교해 매칭 결과를 산출한다.

    use_rag=True(기본): 관련 프로필 청크만 검색해 사용.
    use_rag=False: 프로필 전체 텍스트를 그대로 사용(기존 방식).
    """
    if not profile_text.strip():
        raise ValueError("프로필이 비어 있습니다. data/profile.md를 채워주세요.")

    profile_for_prompt = (
        _retrieve_relevant_profile(requirements, profile_text, llm, store)
        if use_rag
        else profile_text
    )

    requirements_json = json.dumps(
        requirements.model_dump(), ensure_ascii=False, indent=2
    )
    prompt = _MATCH_PROMPT.format(
        requirements=requirements_json,
        profile=profile_for_prompt,
    )

    return llm.generate_structured(prompt=prompt, schema=MatchResult)
