"""평가 데이터셋: 정답이 있는 테스트 케이스 모음.

각 케이스는 '공고 텍스트'와 '그 공고에서 반드시 나와야 하는 핵심 역량'을 담는다.
역량 추출이 이 핵심 역량들을 얼마나 잡아내는지로 품질을 측정한다.

직무를 일부러 다양하게(프론트/백엔드/데이터/비개발) 섞어, 봇이 특정 직무에
치우치지 않고 범용으로 동작하는지 함께 검증한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class EvalCase:
    """평가 케이스 하나."""

    name: str
    job_text: str
    # 추출 결과(필수+우대)에 반드시 포함돼야 하는 핵심 역량(정답)
    expected_skills: List[str]
    # 이 중 하나라도 나오면 정답으로 인정하는 "동의어 그룹"
    #   예: React 공고에서 "React" 또는 "React.js" 둘 다 허용
    skill_synonyms: dict = field(default_factory=dict)
    # 공고에 아예 없어 추출되면 안 되는 역량(환각 검출용, 선택)
    forbidden_skills: List[str] = field(default_factory=list)


DATASET: List[EvalCase] = [
    EvalCase(
        name="프론트엔드 신입",
        job_text=(
            "[프론트엔드 개발자 신입 채용]\n"
            "담당업무: React 기반 웹 서비스 UI 개발, 사내 어드민 대시보드 유지보수\n"
            "자격요건(필수): React 및 JavaScript 개발 경험, HTML/CSS, Git 협업 경험\n"
            "우대사항: TypeScript, Next.js, 데이터 시각화(차트), 상태관리 라이브러리(Zustand/Redux), 반응형 웹"
        ),
        expected_skills=["React", "JavaScript", "TypeScript", "Next.js"],
        skill_synonyms={
            "React": ["React", "React.js", "리액트"],
            "JavaScript": ["JavaScript", "JS", "자바스크립트"],
        },
        forbidden_skills=["Django", "간호"],
    ),
    EvalCase(
        name="백엔드(파이썬)",
        job_text=(
            "[백엔드 개발자]\n"
            "담당업무: REST API 개발, 데이터베이스 설계, 대용량 트래픽 처리\n"
            "필수: Python, Django 또는 FastAPI 경험, SQL(RDBMS), Git\n"
            "우대: AWS 클라우드, Docker, Redis, 메시지 큐(Kafka 등)"
        ),
        expected_skills=["Python", "SQL", "Docker", "AWS"],
        skill_synonyms={
            "SQL": ["SQL", "RDBMS", "데이터베이스", "MySQL", "PostgreSQL"],
            "AWS": ["AWS", "클라우드", "Amazon Web Services"],
        },
        forbidden_skills=["React"],
    ),
    EvalCase(
        name="데이터 분석가",
        job_text=(
            "[데이터 분석가 채용]\n"
            "담당업무: 사업 지표 분석, 대시보드 구축, A/B 테스트 설계\n"
            "필수: SQL 능숙, Python(pandas) 데이터 처리, 통계적 사고\n"
            "우대: Tableau 또는 Looker, 머신러닝 기초, BigQuery"
        ),
        expected_skills=["SQL", "Python", "통계"],
        skill_synonyms={
            "Python": ["Python", "pandas", "파이썬"],
            "통계": ["통계", "통계적 사고", "statistics", "통계학"],
        },
        forbidden_skills=["Spring"],
    ),
    EvalCase(
        name="비개발(마케터)",
        job_text=(
            "[퍼포먼스 마케터 신입]\n"
            "담당업무: 디지털 광고 캠페인 운영, 성과 분석, 콘텐츠 기획\n"
            "필수: 데이터 기반 사고, GA(구글 애널리틱스) 이해, 커뮤니케이션 능력\n"
            "우대: 광고 매체(메타/구글애즈) 집행 경험, SQL 기초, 콘텐츠 제작"
        ),
        expected_skills=["Google Analytics", "광고"],
        skill_synonyms={
            "Google Analytics": ["GA", "구글 애널리틱스", "Google Analytics", "애널리틱스"],
            "광고": ["광고", "광고 매체", "메타", "구글애즈", "캠페인"],
        },
        forbidden_skills=["React", "Python 백엔드"],
    ),
]
