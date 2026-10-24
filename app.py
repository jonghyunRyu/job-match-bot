"""공고 매칭봇 - Streamlit 1차 MVP UI.

흐름: 공고 입력(텍스트/이미지) → 역량 추출 → 프로필 매칭 → 리포트
실행: streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from src.config import PROFILE_PATH, get_settings, load_profile
from src.ingest.loader import PdfProcessingError, load_image, load_pdf, load_text
from src.llm.gemini import get_llm
from src.graph import run_graph

st.set_page_config(page_title="공고 매칭봇", page_icon="🎯", layout="wide")


def _check_api_key() -> bool:
    settings = get_settings()
    if not settings.has_api_key:
        st.error(
            "GEMINI_API_KEY가 설정되지 않았습니다.\n\n"
            "프로젝트 루트의 `.env.example`을 `.env`로 복사하고 "
            "발급받은 Gemini API 키를 넣어주세요.\n"
            "(키 발급: https://aistudio.google.com/apikey)"
        )
        return False
    return True


def render_sidebar() -> str:
    """사이드바에서 프로필을 보여주고 편집할 수 있게 한다."""
    st.sidebar.header("내 프로필")
    st.sidebar.caption(f"파일: {PROFILE_PATH}")

    profile = load_profile()
    edited = st.sidebar.text_area("프로필 (매칭 기준)", value=profile, height=400)

    if st.sidebar.button("프로필 저장"):
        PROFILE_PATH.write_text(edited, encoding="utf-8")
        st.sidebar.success("저장했습니다.")

    return edited


def render_report(report, match_result) -> None:
    """리포트를 화면에 렌더링한다."""
    st.subheader("매칭 리포트")

    rate = report.match_rate
    color = "🟢" if rate >= 70 else ("🟡" if rate >= 40 else "🔴")
    st.metric("종합 매칭률", f"{rate}%", help="필수 역량 충족도 중심")
    st.progress(rate / 100)
    st.write(f"{color} {report.summary}")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 강점")
        for s in report.strengths or ["(없음)"]:
            st.markdown(f"- {s}")
    with col2:
        st.markdown("### 부족/격차")
        for g in report.gaps or ["(없음)"]:
            st.markdown(f"- {g}")

    st.markdown("### 보완 추천")
    for r in report.recommendations or ["(없음)"]:
        st.markdown(f"- {r}")

    with st.expander("역량별 매칭 상세 보기"):
        for m in match_result.matches:
            mark = "✅" if m.matched else "❌"
            tag = "필수" if m.is_required else "우대"
            line = f"{mark} **[{tag}] {m.skill}**"
            if m.matched and m.evidence:
                line += f" — 근거: {m.evidence}"
            st.markdown(line)


def run_pipeline(job_input, profile_text: str) -> None:
    """LangGraph 파이프라인(추출→매칭→리포트)을 실행하고 결과를 렌더링한다."""
    llm = get_llm()

    with st.status("분석 중... (추출 → 매칭 → 리포트)", expanded=True) as status:
        st.write("공고 분석 그래프 실행 중...")
        final_state = run_graph(job_input, profile_text, llm)
        status.update(label="분석 완료", state="complete", expanded=False)

    requirements = final_state.get("requirements")
    match_result = final_state.get("match_result")
    report = final_state.get("report")

    # 추출 단계에서 역량을 하나도 못 찾아 그래프가 조기 종료된 경우
    if report is None or match_result is None:
        st.warning(
            "공고에서 요구 역량을 추출하지 못했습니다. "
            "공고 내용이 충분한지 확인하거나 다른 입력으로 시도해주세요."
        )
        return

    if requirements and (requirements.job_title or requirements.company):
        header = " / ".join(
            x for x in (requirements.company, requirements.job_title) if x
        )
        st.info(f"분석 대상: {header}")

    render_report(report, match_result)


def main() -> None:
    st.title("🎯 공고 매칭봇")
    st.caption("채용 공고를 넣으면 내 역량과의 매칭률과 보완점을 분석해줍니다.")

    profile_text = render_sidebar()

    if not _check_api_key():
        return

    tab_text, tab_image, tab_pdf = st.tabs(
        ["텍스트 입력", "이미지(캡처) 입력", "PDF 입력"]
    )

    with tab_text:
        job_text = st.text_area("채용 공고 전문을 붙여넣으세요", height=300)
        if st.button("분석하기", key="analyze_text"):
            if not job_text.strip():
                st.warning("공고 내용을 입력해주세요.")
            else:
                try:
                    run_pipeline(load_text(job_text), profile_text)
                except Exception as e:  # noqa: BLE001
                    st.exception(e)

    with tab_image:
        uploaded = st.file_uploader(
            "공고 캡처 이미지 업로드", type=["png", "jpg", "jpeg", "webp"]
        )
        if uploaded is not None:
            st.image(uploaded, caption="업로드한 공고 이미지", width=400)
        if st.button("분석하기", key="analyze_image"):
            if uploaded is None:
                st.warning("이미지를 업로드해주세요.")
            else:
                try:
                    run_pipeline(load_image(uploaded.getvalue()), profile_text)
                except Exception as e:  # noqa: BLE001
                    st.exception(e)

    with tab_pdf:
        st.caption(
            "텍스트형 PDF는 자동으로 글자를 추출하고, 스캔형 PDF는 이미지로 변환해 "
            "Vision으로 분석합니다. (스캔형은 시스템에 poppler 설치 필요)"
        )
        pdf_file = st.file_uploader("공고 PDF 업로드", type=["pdf"])
        if st.button("분석하기", key="analyze_pdf"):
            if pdf_file is None:
                st.warning("PDF 파일을 업로드해주세요.")
            else:
                try:
                    job = load_pdf(pdf_file.getvalue())
                    if job.text:
                        st.success("텍스트형 PDF로 인식: 글자를 추출했습니다.")
                    else:
                        st.info(
                            f"스캔형 PDF로 인식: {len(job.images)}개 페이지를 "
                            "이미지로 변환해 분석합니다."
                        )
                    run_pipeline(job, profile_text)
                except PdfProcessingError as e:
                    st.error(str(e))
                except Exception as e:  # noqa: BLE001
                    st.exception(e)


if __name__ == "__main__":
    main()
