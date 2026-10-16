"""처리 파이프라인.

각 모듈은 하나의 단계이며, 2차 단계에서 LangGraph 노드로 그대로 승격된다.
  extract  : 공고 → 요구 역량 추출 (멀티모달)
  match    : 요구 역량 vs 내 프로필 → 매칭률/격차
  report   : 매칭 결과 → 보완 추천 포함 최종 리포트
"""

from .extract import extract_requirements
from .match import match_profile
from .report import build_report

__all__ = ["extract_requirements", "match_profile", "build_report"]
