"""매칭 분석 단계: 요구 역량 vs 내 프로필 → 매칭률/격차.

1차 MVP: 프로필 텍스트 전체를 LLM 프롬프트에 넣어 판정한다.
2차 단계: 이 지점이 Chroma 벡터 검색(관련 경험만 검색)으로 교체된다.
"""

from __future__ import annotations

import json

from ..llm.base import LLMClient
from ..schemas import JobRequirements, MatchResult

_MATCH_PROMPT = """\
당신은 채용 매칭 분석가입니다.
아래 '요구 역량'과 '지원자 프로필'을 비교해 매칭 결과를 산출하세요.

규칙:
- 각 요구 역량마다 프로필에 관련 경험이 있는지(matched) 판정하세요.
- matched=true면 evidence에 근거가 된 프로필 내용을 짧게 인용하세요.
- 필수 역량(is_required=true)은 우대 역량보다 매칭률에 더 크게 반영하세요.
- match_rate는 0~100 정수로, 필수 역량 충족도를 중심으로 산정하세요.
- strengths: 지원자가 특히 강한 부분. gaps: 부족해서 보완이 필요한 역량.
- 프로필에 없는 내용을 지어내지 마세요.

[요구 역량]
{requirements}

[지원자 프로필]
{profile}
"""


def match_profile(
    requirements: JobRequirements,
    profile_text: str,
    llm: LLMClient,
) -> MatchResult:
    """요구 역량과 프로필을 비교해 매칭 결과를 산출한다."""
    if not profile_text.strip():
        raise ValueError("프로필이 비어 있습니다. data/profile.md를 채워주세요.")

    requirements_json = json.dumps(
        requirements.model_dump(), ensure_ascii=False, indent=2
    )
    prompt = _MATCH_PROMPT.format(
        requirements=requirements_json,
        profile=profile_text,
    )

    return llm.generate_structured(prompt=prompt, schema=MatchResult)
