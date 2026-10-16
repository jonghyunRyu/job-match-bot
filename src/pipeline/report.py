"""리포트 생성 단계: 매칭 결과 → 보완 추천 포함 최종 리포트."""

from __future__ import annotations

import json

from ..llm.base import LLMClient
from ..schemas import JobRequirements, MatchResult, Report

_REPORT_PROMPT = """\
당신은 취업 커리어 코치입니다.
아래 '요구 역량'과 '매칭 결과'를 바탕으로 지원자를 위한 리포트를 작성하세요.

규칙:
- summary: 매칭 상태를 1~2문장으로 요약.
- strengths: 매칭 결과의 강점을 지원자가 공감할 표현으로 정리.
- gaps: 부족한 역량을 명확히.
- recommendations: 각 격차를 메울 '구체적인' 보완 방법을 제시하세요.
  (예: 특정 미니 프로젝트 아이디어, 학습할 주제, 포트폴리오에 추가할 것)
- 과장하지 말고 현실적으로 작성하세요.

[요구 역량]
{requirements}

[매칭 결과]
{match_result}
"""


def build_report(
    requirements: JobRequirements,
    match_result: MatchResult,
    llm: LLMClient,
) -> Report:
    """매칭 결과를 바탕으로 보완 추천이 포함된 최종 리포트를 생성한다."""
    prompt = _REPORT_PROMPT.format(
        requirements=json.dumps(
            requirements.model_dump(), ensure_ascii=False, indent=2
        ),
        match_result=json.dumps(
            match_result.model_dump(), ensure_ascii=False, indent=2
        ),
    )

    report = llm.generate_structured(prompt=prompt, schema=Report)
    # 매칭률은 매칭 단계 값을 신뢰 (리포트 LLM이 바꾸지 않도록 고정)
    report.match_rate = match_result.match_rate
    return report
