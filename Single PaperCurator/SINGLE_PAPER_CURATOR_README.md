# Single Paper Curator - 실행 가이드

## 📋 개요
단일 논문을 Title 또는 DOI로 검색하여 Gemini로 자동 요약하고 Notion에 업로드하는 Streamlit 앱

## 🔧 필수 요구사항

### Python 패키지
```bash
pip install streamlit biopython requests google-generativeai notion-client
```

또는 기존 requirements.txt 사용:
```bash
pip install -r requirements.txt
```

### API 키 필요
1. **Notion Integration Token**
   - https://www.notion.so/my-integrations 에서 생성
   - Papers Database에 연결 필요

2. **Notion Papers Database ID**
   - 기존 PaperCurator의 Papers Database ID 사용
   - URL: https://notion.so/workspace/{database_id}?v=...

3. **Google Gemini API Key**
   - https://makersuite.google.com/app/apikey 에서 생성
   - gemini-2.5-flash 모델 사용

## 🚀 로컬 실행 방법

### 1. Secrets 설정 파일 생성

프로젝트 루트에 `.streamlit` 폴더를 만들고 `secrets.toml` 파일 생성:

```bash
mkdir -p .streamlit
```

`.streamlit/secrets.toml` 파일 내용:
```toml
NOTION_TOKEN = "secret_xxxxxxxxxxxxxxxxxxxxx"
PAPERS_DATABASE_ID = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
GEMINI_API_KEY = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

⚠️ **중요**: `.streamlit/secrets.toml`은 `.gitignore`에 추가하여 GitHub에 업로드되지 않도록 하세요!

### 2. Streamlit 실행

```bash
streamlit run single_paper_curator.py
```

브라우저에서 자동으로 `http://localhost:8501` 열림

## ☁️ Streamlit Cloud 배포 방법

### 1. GitHub에 코드 푸시
```bash
git add single_paper_curator.py
git commit -m "Add Single Paper Curator"
git push
```

### 2. Streamlit Cloud 설정
1. https://share.streamlit.io 접속
2. "New app" 클릭
3. Repository: `Du-Hwa/PaperCurator` 선택
4. Branch: `main`
5. Main file path: `single_paper_curator.py`

### 3. Secrets 설정
Streamlit Cloud → App settings → Secrets:

```toml
NOTION_TOKEN = "secret_xxxxxxxxxxxxxxxxxxxxx"
PAPERS_DATABASE_ID = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
GEMINI_API_KEY = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

## 📖 사용 방법

### Title로 검색
1. "Title" 선택
2. 논문 제목 입력 (부분 검색 가능)
   - 예: "Florigen activation complex"
3. 검색 버튼 클릭
4. 결과에서 원하는 논문 선택
5. "요약 및 Notion 업로드" 클릭

### DOI로 검색
1. "DOI" 선택
2. DOI 정확히 입력
   - 예: "10.1038/s41586-025-09704-6"
3. 검색 버튼 클릭
4. 논문 확인 후 "요약 및 Notion 업로드" 클릭

## 🔄 워크플로우

```
사용자 입력 (Title/DOI)
    ↓
PubMed 검색
    ↓
논문 정보 표시 (확인)
    ↓
Gemini 요약 생성
    ↓
Notion 자동 업로드
    ↓
완료! (Notion URL 제공)
```

## ⚠️ 주의사항

1. **초록 없는 논문**: 일부 논문은 초록이 없을 수 있으며, 이 경우 요약 품질이 낮을 수 있습니다.

2. **API Rate Limit**: 
   - Gemini API: 요청 간 2초 대기
   - PubMed API: 초당 3회 제한

3. **Notion Database 스키마**: 
   - 기존 PaperCurator의 Papers Database와 동일한 구조 사용
   - 필수 속성: Name (Title), Author, Journal, Research Area, Publication Year

## 🐛 문제 해결

### "⚠️ Streamlit Secrets 설정 필요" 오류
- `.streamlit/secrets.toml` 파일 확인
- API 키가 정확한지 확인

### "검색 결과가 없습니다" 오류
- Title: 철자 확인, 부분 검색 시도
- DOI: 정확한 형식 확인 (10.xxxx/xxxxx)

### "Notion 업로드 실패" 오류
- Notion Integration이 Database에 연결되어 있는지 확인
- Database ID가 정확한지 확인

## 🔗 관련 링크
- Notion API: https://developers.notion.com
- Google AI Studio: https://makersuite.google.com
- PubMed E-utilities: https://www.ncbi.nlm.nih.gov/books/NBK25501/

## 📝 기능 확장 아이디어
- [ ] 여러 논문 일괄 처리
- [ ] 검색 히스토리 저장
- [ ] 중복 논문 감지
- [ ] PDF 직접 업로드 지원
- [ ] ArXiv 검색 지원
