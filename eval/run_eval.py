"""평가 실행 스크립트.

각 평가 케이스를 봇에 넣어 역량 추출/매칭을 수행하고, 정답과 비교해 채점한다.

사용법:
    python -m eval.run_eval              # 전체 케이스 실행
    python -m eval.run_eval --case 프론트  # 이름에 '프론트' 포함된 케이스만

LangSmith 추적(선택):
    .env에 LANGSMITH_API_KEY가 있으면 각 LLM 호출이 LangSmith로 추적된다.
    없어도 평가는 정상 동작한다.
"""

from __future__ import annotations

import argparse
import sys

from src.config import load_profile
from src.ingest.loader import load_text
from src.llm.gemini import QuotaExceededError, get_llm
from src.pipeline import extract_requirements, match_profile

from .dataset import DATASET
from .metrics import score_case, summarize


def _maybe_enable_langsmith() -> bool:
    """LANGSMITH_API_KEY가 있으면 추적을 켠다. 켜졌는지 여부를 반환."""
    import os

    if os.getenv("LANGSMITH_API_KEY"):
        os.environ.setdefault("LANGSMITH_TRACING", "true")
        os.environ.setdefault("LANGSMITH_PROJECT", "job-match-bot-eval")
        return True
    return False


def run(case_filter: str | None = None) -> int:
    tracing = _maybe_enable_langsmith()
    print(f"LangSmith 추적: {'ON' if tracing else 'OFF (키 없음, 평가는 정상 동작)'}")
    print("=" * 60)

    llm = get_llm()
    profile = load_profile()

    cases = DATASET
    if case_filter:
        cases = [c for c in DATASET if case_filter in c.name]
        if not cases:
            print(f"'{case_filter}'에 해당하는 케이스가 없습니다.")
            return 1

    results = []
    errored = []
    for case in cases:
        print(f"\n[{case.name}] 분석 중...")
        try:
            job = load_text(case.job_text)
            req = extract_requirements(job, llm)
            extracted = [s.name for s in req.required_skills] + [
                s.name for s in req.preferred_skills
            ]
            # 매칭률도 함께 측정 (참고 지표)
            match = match_profile(req, profile, llm, use_rag=True)
        except QuotaExceededError as exc:
            # 할당량 초과면 이후 케이스도 모두 실패할 것이므로 즉시 중단
            print(f"  ✗ 할당량 초과: {exc}")
            print("\n할당량이 소진되어 평가를 중단합니다. 리셋 후 다시 시도하세요.")
            return 3
        except Exception as exc:  # noqa: BLE001
            # 한 케이스가 실패해도(예: 장시간 503) 나머지는 계속 평가
            errored.append(case.name)
            print(f"  ✗ 실패(건너뜀): {type(exc).__name__}: {str(exc)[:80]}")
            continue

        result = score_case(case, extracted, match.match_rate)
        results.append(result)

        print(f"  추출 역량: {extracted}")
        print(f"  재현율(recall): {result.recall:.0%}  "
              f"(찾음 {result.found} / 놓침 {result.missed})")
        if result.hallucinated:
            print(f"  ⚠ 환각(금지어 추출): {result.hallucinated}")
        print(f"  매칭률: {result.match_rate}%")

    if errored:
        print(f"\n(참고) 서버 오류 등으로 건너뛴 케이스: {errored}")

    if not results:
        print("\n모든 케이스가 실패했습니다(서버 혼잡 가능). 잠시 후 다시 시도하세요.")
        return 3

    summary = summarize(results)
    print("\n" + "=" * 60)
    print("평가 요약")
    print(f"  케이스 수      : {summary.num_cases}")
    print(f"  평균 재현율    : {summary.avg_recall:.1%}")
    print(f"  환각(총합)     : {summary.total_hallucinations}건")
    print(f"  합격 여부      : {'PASS' if summary.passed else 'FAIL'} "
          f"(기준: 재현율>=80%, 환각 0건)")
    print("=" * 60)

    return 0 if summary.passed else 2


def main() -> None:
    parser = argparse.ArgumentParser(description="공고 매칭봇 평가 실행")
    parser.add_argument(
        "--case", default=None, help="이름에 이 문자열이 포함된 케이스만 실행"
    )
    args = parser.parse_args()
    sys.exit(run(args.case))


if __name__ == "__main__":
    main()
