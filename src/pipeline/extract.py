"""역량 추출 단계: 공고 입력 → 구조화된 요구 역량(JobRequirements).

텍스트/이미지 모두 동일한 함수로 처리한다. 이미지는 Gemini Vision에
직접 전달되므로 별도 OCR이 필요 없다.
"""

from __future__ import annotations

from ..ingest.loader import JobInput
from ..llm.base import LLMClient
from ..schemas import JobRequirements

_EXTRACT_PROMPT = """\
당신은 채용 공고 분석 전문가입니다.
아래에 주어진 채용 공고(텍스트 또는 이미지)에서 요구 역량을 추출하세요.

규칙:
- 공고에 실제로 적힌 내용만 사용하고, 없는 역량을 지어내지 마세요.
- 각 역량은 '필수(required)'와 '우대(preferred)'로 구분하세요.
- 역량 이름은 간결한 기술/스킬 단위로 분리하세요 (예: "Python", "RESTful API 설계").
- reason에는 공고의 어떤 문구에서 그 역량이 나왔는지 근거를 짧게 적으세요.
- 회사명/직무명을 알 수 있으면 채우고, 모르면 빈 문자열로 두세요.

{job_text}
"""


def extract_requirements(job: JobInput, llm: LLMClient) -> JobRequirements:
    """공고 입력에서 요구 역량을 구조화 JSON으로 추출한다."""
    if job.is_empty:
        raise ValueError("공고 입력이 비어 있습니다.")

    job_text = (
        f"공고 내용:\n{job.text}"
        if job.text
        else "공고가 이미지로 제공되었습니다. 이미지를 분석하세요."
    )
    prompt = _EXTRACT_PROMPT.format(job_text=job_text)

    return llm.generate_structured(
        prompt=prompt,
        schema=JobRequirements,
        images=job.images or None,
    )
