"""파이프라인 전체에서 공유하는 데이터 구조 (Pydantic 모델).

각 파이프라인 단계(추출 → 매칭 → 리포트)의 입출력을 타입으로 고정해
LLM 응답을 구조화 JSON으로 강제하고, 단계 간 계약을 명확히 한다.
"""

from __future__ import annotations

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class InputType(str, Enum):
    """공고 입력의 종류."""

    TEXT = "text"
    IMAGE = "image"
    PDF = "pdf"  # 2차 단계


class Skill(BaseModel):
    """공고에서 추출한 하나의 요구 역량."""

    name: str = Field(..., description="역량/기술 이름 (예: Python, LangChain)")
    category: str = Field(
        default="기타",
        description="역량 분류: 필수 / 우대 / 경력 / 기타 중 하나",
    )
    reason: str = Field(
        default="",
        description="공고의 어떤 문구에서 이 역량이 요구되는지 근거",
    )


class JobRequirements(BaseModel):
    """공고에서 추출된 요구 역량 전체 (역량 추출 단계의 산출물)."""

    job_title: str = Field(default="", description="공고 직무명")
    company: str = Field(default="", description="회사명 (추출 가능한 경우)")
    required_skills: List[Skill] = Field(
        default_factory=list, description="필수 역량 목록"
    )
    preferred_skills: List[Skill] = Field(
        default_factory=list, description="우대 역량 목록"
    )
    summary: str = Field(default="", description="공고 핵심 요약 1~2문장")


class SkillMatch(BaseModel):
    """요구 역량 하나에 대한 매칭 판정."""

    skill: str = Field(..., description="요구 역량 이름")
    matched: bool = Field(..., description="내 프로필에 관련 경험이 있는지")
    evidence: str = Field(
        default="", description="매칭 근거가 된 내 프로필 내용 (있을 때)"
    )
    is_required: bool = Field(
        default=True, description="필수 역량이면 True, 우대면 False"
    )


class MatchResult(BaseModel):
    """매칭 분석 단계의 산출물."""

    match_rate: int = Field(
        ..., ge=0, le=100, description="종합 매칭률 (0~100 정수)"
    )
    matches: List[SkillMatch] = Field(
        default_factory=list, description="역량별 매칭 판정 목록"
    )
    strengths: List[str] = Field(
        default_factory=list, description="두드러지는 강점"
    )
    gaps: List[str] = Field(
        default_factory=list, description="부족하거나 보완이 필요한 역량"
    )


class Report(BaseModel):
    """최종 리포트 (리포트 생성 단계의 산출물)."""

    match_rate: int = Field(..., ge=0, le=100)
    summary: str = Field(default="", description="한눈 요약")
    strengths: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(
        default_factory=list,
        description="격차를 메우기 위한 보완 프로젝트/학습 추천",
    )
