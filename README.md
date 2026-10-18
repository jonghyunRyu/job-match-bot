# 🎯 공고 매칭봇 (job-match-bot)

채용 공고를 입력하면 요구 역량을 추출하고, 내 프로필과 비교해 **매칭률 / 부족 역량 / 보완 추천** 리포트를 생성하는 LLM 기반 도구입니다.

## 현재 상태

```
텍스트 / 이미지(캡처) / PDF 입력 → Gemini 역량 추출 → 프로필 매칭 → 리포트 → Streamlit UI
```

- 이미지는 Gemini Vision에 직접 전달하므로 별도 OCR이 필요 없습니다.
- PDF는 텍스트형이면 `pypdf`로 글자를 추출하고, 스캔형이면 `pdf2image`로 페이지를 이미지화해 Vision으로 폴백합니다.
  - 스캔형 PDF 처리는 시스템에 **poppler** 설치가 필요합니다. (텍스트형은 불필요)
- LLM 호출은 어댑터 레이어(`src/llm`)로 감싸 벤더 교체가 가능합니다.

## 스택

| 영역 | 기술 |
|------|------|
| 언어 | Python |
| LLM | Google Gemini (`google-genai` 통합 SDK, 멀티모달) |
| UI | Streamlit |
| 검증 | Pydantic (구조화 출력) |

> 완료: 1차 MVP(텍스트/이미지) → PDF 처리
> 다음 예정: RAG(Chroma) → LangGraph 에이전트화 → 평가셋 → 배포

## 설치 & 실행

### 1. 가상환경 + 의존성

```bash
python -m venv .venv
# Windows (bash)
source .venv/Scripts/activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

### 2. API 키 설정

```bash
cp .env.example .env
```

`.env`를 열어 `GEMINI_API_KEY`에 발급받은 키를 넣으세요.
(키 발급: https://aistudio.google.com/apikey)

### 3. 프로필 작성

`data/profile.md`에 본인의 경력/프로젝트/기술 스택을 채웁니다. (앱 사이드바에서도 편집·저장 가능)

### 4. (선택) 스캔형 PDF를 쓸 경우 poppler 설치

텍스트형 PDF는 추가 설치가 필요 없습니다. **스캔(이미지) PDF**를 분석하려면 poppler가 필요합니다.

- Windows: https://github.com/oschwartz10612/poppler-windows 에서 받아 `bin` 폴더를 PATH에 등록
- macOS: `brew install poppler`
- Ubuntu/Debian: `sudo apt-get install poppler-utils`

### 5. 실행

```bash
streamlit run app.py
# 가상환경 활성화가 안 될 때는:
# .venv/Scripts/python.exe -m streamlit run app.py
```

## 프로젝트 구조

```
job-match-bot/
├── app.py                 # Streamlit 진입점
├── requirements.txt
├── .env.example
├── data/
│   └── profile.md         # 내 프로필 (매칭 기준)
└── src/
    ├── config.py          # 설정/환경변수
    ├── schemas.py         # Pydantic 모델 (단계 간 계약)
    ├── llm/
    │   ├── base.py        # LLM 어댑터 인터페이스
    │   └── gemini.py      # Gemini 구현 (텍스트 + Vision)
    ├── ingest/
    │   └── loader.py      # 입력 타입 판별/정규화
    └── pipeline/
        ├── extract.py     # 역량 추출
        ├── match.py       # 프로필 매칭
        └── report.py      # 리포트 생성
```

각 `pipeline` 모듈은 2차 단계에서 LangGraph 노드로 승격되고,
`match.py`의 프로필 비교는 Chroma 벡터 검색으로 교체될 예정입니다.
