"""채점 로직.

LLM이 뽑은 역량명은 표현이 조금씩 다를 수 있으므로(React vs React.js),
정규화 + 부분 포함 + 동의어 그룹으로 느슨하게 매칭해 정답 여부를 판정한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .dataset import EvalCase


def _normalize(s: str) -> str:
    """비교용 정규화: 소문자 + 공백/점/하이픈 제거."""
    return s.lower().replace(" ", "").replace(".", "").replace("-", "").strip()


def _skill_found(target: str, extracted: List[str], synonyms: dict) -> bool:
    """기대 역량(target)이 추출 목록(extracted) 안에 있는지 느슨하게 판정한다.

    - 양쪽을 정규화해 부분 포함(substring)으로 비교
    - target에 동의어 그룹이 있으면 그 중 하나라도 맞으면 인정
    """
    candidates = synonyms.get(target, [target])
    norm_extracted = [_normalize(e) for e in extracted]
    for cand in candidates:
        nc = _normalize(cand)
        for ne in norm_extracted:
            if nc and (nc in ne or ne in nc):
                return True
    return False


@dataclass
class CaseResult:
    """케이스 하나의 채점 결과."""

    name: str
    recall: float           # 기대 역량 중 몇 %를 잡았나 (0~1)
    found: List[str]        # 찾은 기대 역량
    missed: List[str]       # 놓친 기대 역량
    hallucinated: List[str] # 추출되면 안 되는데 나온 역량(금지어)
    match_rate: int         # 매칭 단계 산출 매칭률(참고용)
    skills_extracted: List[str]


def score_case(
    case: EvalCase,
    extracted_skills: List[str],
    match_rate: int,
) -> CaseResult:
    """케이스의 추출 결과를 정답과 비교해 채점한다."""
    found, missed = [], []
    for exp in case.expected_skills:
        if _skill_found(exp, extracted_skills, case.skill_synonyms):
            found.append(exp)
        else:
            missed.append(exp)

    recall = len(found) / len(case.expected_skills) if case.expected_skills else 1.0

    hallucinated = []
    for forb in case.forbidden_skills:
        # 금지어는 동의어 없이 단독 비교
        if _skill_found(forb, extracted_skills, {}):
            hallucinated.append(forb)

    return CaseResult(
        name=case.name,
        recall=recall,
        found=found,
        missed=missed,
        hallucinated=hallucinated,
        match_rate=match_rate,
        skills_extracted=extracted_skills,
    )


@dataclass
class EvalSummary:
    """전체 평가 요약."""

    num_cases: int
    avg_recall: float
    total_hallucinations: int
    results: List[CaseResult]

    @property
    def passed(self) -> bool:
        """합격 기준: 평균 재현율 0.8 이상 & 환각 0건."""
        return self.avg_recall >= 0.8 and self.total_hallucinations == 0


def summarize(results: List[CaseResult]) -> EvalSummary:
    """케이스 결과들을 종합한다."""
    n = len(results)
    avg_recall = sum(r.recall for r in results) / n if n else 0.0
    total_hall = sum(len(r.hallucinated) for r in results)
    return EvalSummary(
        num_cases=n,
        avg_recall=avg_recall,
        total_hallucinations=total_hall,
        results=results,
    )
