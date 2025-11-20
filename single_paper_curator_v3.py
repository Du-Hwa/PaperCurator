"""
Single Paper Curator
개별 논문을 Title/DOI로 검색하여 자동 요약 및 Notion 업로드
"""

import streamlit as st
import requests
from xml.etree import ElementTree as ET
import json
import time
import google.generativeai as genai
from notion_client import Client

# 페이지 설정
st.set_page_config(
    page_title="Single Paper Curator",
    page_icon="📄",
    layout="wide"
)

# API 설정 (Streamlit Secrets 사용)
def load_credentials():
    """Streamlit Secrets에서 자격 증명 로드"""
    try:
        notion_token = st.secrets["NOTION_TOKEN"]
        papers_database_id = st.secrets["PAPERS_DATABASE_ID"]
        gemini_api_key = st.secrets["GEMINI_API_KEY"]
        return notion_token, papers_database_id, gemini_api_key
    except:
        return None, None, None

# 논문 검색 함수
def search_by_title(title):
    """Title로 PubMed 검색"""
    try:
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        
        # 첫 번째 시도: 정확한 제목 검색 (따옴표 포함)
        params = {
            'db': 'pubmed',
            'term': f'"{title}"[Title]',
            'retmax': 10,
            'retmode': 'json',
            'sort': 'relevance'
        }
        st.info(f"🔍 검색 시도 1 (정확한 제목): {params['term']}")
        response = requests.get(url, params=params, verify=False)
        response.raise_for_status()
        data = response.json()
        pmids = data['esearchresult']['idlist']
        
        # 결과가 없으면 두 번째 시도: 모든 필드에서 검색
        if not pmids:
            st.info("⚠️ 정확한 제목 검색 실패, 전체 텍스트 검색 시도 중...")
            params['term'] = f'"{title}"'  # 필드 지정 없이
            st.info(f"🔍 검색 시도 2 (전체 텍스트): {params['term']}")
            response = requests.get(url, params=params, verify=False)
            response.raise_for_status()
            data = response.json()
            pmids = data['esearchresult']['idlist']
        
        # 여전히 결과가 없으면 세 번째 시도: 핵심 단어만 추출
        if not pmids:
            st.info("⚠️ 전체 텍스트 검색 실패, 핵심 단어 검색 시도 중...")
            # 긴 제목에서 핵심 단어 추출 (5단어 이상 → 앞 5단어만)
            words = title.split()
            if len(words) > 5:
                key_phrase = ' '.join(words[:5])
                params['term'] = f'"{key_phrase}"[Title]'
            else:
                params['term'] = f'{title}[Title]'  # 짧은 제목은 따옴표 없이
            st.info(f"🔍 검색 시도 3 (핵심 단어): {params['term']}")
            response = requests.get(url, params=params, verify=False)
            response.raise_for_status()
            data = response.json()
            pmids = data['esearchresult']['idlist']
        
        st.info(f"📡 HTTP 상태: {response.status_code}")
        st.info(f"📊 API 응답 구조: {list(data.keys())}")
        
        if pmids:
            st.success(f"✅ {len(pmids)}개 PMID 발견: {pmids[:5]}")  # 처음 5개만 표시
            if len(pmids) > 10:
                st.info(f"💡 총 {len(pmids)}개 결과 중 상위 10개를 표시합니다.")
        else:
            st.warning("⚠️ 검색 결과 없음 (빈 리스트)")
        
        return pmids if pmids else None
    except Exception as e:
        st.error(f"❌ 검색 오류: {type(e).__name__}: {e}")
        import traceback
        st.code(traceback.format_exc())
        return None

def search_by_doi(doi):
    """DOI로 PubMed 검색"""
    try:
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {
            'db': 'pubmed',
            'term': f'{doi}[DOI]',
            'retmax': 1,
            'retmode': 'json'
        }
        st.info(f"🔍 검색 쿼리: {params['term']}")
        response = requests.get(url, params=params, verify=False)
        st.info(f"📡 HTTP 상태: {response.status_code}")
        response.raise_for_status()
        data = response.json()
        st.info(f"📊 API 응답 구조: {list(data.keys())}")
        pmids = data['esearchresult']['idlist']
        if pmids:
            st.success(f"✅ {len(pmids)}개 PMID 발견: {pmids}")
        else:
            st.warning("⚠️ 검색 결과 없음 (빈 리스트)")
        return pmids if pmids else None
    except Exception as e:
        st.error(f"❌ 검색 오류: {type(e).__name__}: {e}")
        import traceback
        st.code(traceback.format_exc())
        return None

def fetch_paper_details(pmid):
    """PMID로 논문 상세 정보 가져오기"""
    try:
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        params = {
            'db': 'pubmed',
            'id': pmid,
            'retmode': 'xml'
        }
        
        response = requests.get(url, params=params, verify=False)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        article = root.find('.//PubmedArticle')
        
        if not article:
            return None
        
        # PMID
        pmid_elem = article.find('.//PMID')
        pmid = pmid_elem.text if pmid_elem is not None else ''
        
        # Title
        title_elem = article.find('.//ArticleTitle')
        title = title_elem.text if title_elem is not None else 'No title'
        
        # Abstract
        abstract_texts = article.findall('.//AbstractText')
        abstract_parts = []
        for at in abstract_texts:
            text_parts = [at.text or '']
            for elem in at.iter():
                if elem.text:
                    text_parts.append(elem.text)
                if elem.tail:
                    text_parts.append(elem.tail)
            abstract_parts.append(' '.join(text_parts).strip())
        abstract = ' '.join(abstract_parts) if abstract_parts else ''
        
        # Authors
        authors = []
        author_list = article.findall('.//Author')
        for author in author_list[:3]:
            lastname = author.find('LastName')
            initials = author.find('Initials')
            if lastname is not None and initials is not None:
                authors.append(f"{lastname.text} {initials.text}")
        
        if len(author_list) > 6:
            authors.append("...")
            for author in author_list[-3:]:
                lastname = author.find('LastName')
                initials = author.find('Initials')
                if lastname is not None and initials is not None:
                    authors.append(f"{lastname.text} {initials.text}")
        elif len(author_list) > 3:
            for author in author_list[3:]:
                lastname = author.find('LastName')
                initials = author.find('Initials')
                if lastname is not None and initials is not None:
                    authors.append(f"{lastname.text} {initials.text}")
        
        authors_str = ', '.join(authors)
        
        # Journal
        journal_elem = article.find('.//Journal/Title')
        journal = journal_elem.text if journal_elem is not None else 'Unknown journal'
        
        # Publication Date
        year_elem = article.find('.//PubDate/Year')
        month_elem = article.find('.//PubDate/Month')
        year = year_elem.text if year_elem is not None else ''
        month = month_elem.text if month_elem is not None else ''
        pub_date_str = f"{year} {month}".strip()
        
        # DOI
        doi = ''
        elocation_ids = article.findall('.//ELocationID')
        for eloc in elocation_ids:
            if eloc.get('EIdType') == 'doi':
                doi = eloc.text
                break
        
        return {
            'pmid': str(pmid),
            'doi': doi if doi else '',
            'title': str(title),
            'authors': authors_str,
            'journal': str(journal),
            'pub_date': pub_date_str,
            'abstract': str(abstract),
            'pubmed_url': f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        }
    
    except Exception as e:
        st.error(f"논문 정보 가져오기 실패: {e}")
        return None

def summarize_with_gemini(paper, api_key):
    """Gemini로 논문 요약"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
You are analyzing a research paper abstract. Focus ONLY on the NEW discoveries and novel mechanisms reported in THIS paper.

Title: {paper['title']}
Authors: {paper['authors']}
Journal: {paper['journal']} ({paper['pub_date']})
Abstract: {paper['abstract']}

CRITICAL: Distinguish between:
- Background information (known from previous studies - IGNORE THIS)
- NEW findings reported in THIS paper (focus here - look for words like "Here we demonstrate", "We show that", "We find that", "Our studies")

Provide your response in this JSON format:

{{
    "main_summary": "Summarize the NEW mechanism or discovery in 2-3 sentences using third-person perspective (e.g., 'The study reveals...', 'This paper demonstrates...', 'The authors found...'). Focus on what was NOT known before.",
    "main_findings": [
        "NEW finding 1: Describe the novel molecular mechanism in third-person (e.g., 'The study demonstrates that...', 'This paper reveals...'). Include specific protein interactions, phase separation, or assembly mechanisms.",
        "NEW finding 2: Report specific molecular details in third-person. Include protein names, binding sites, regulatory mechanisms.",
        "NEW finding 3: Describe unexpected results in third-person. Include spatiotemporal, quantitative, or mechanistic insights."
    ],
    "keywords": ["Keyword1", "Keyword2", "Keyword3", "Keyword4", "Keyword5", "Keyword6", "Keyword7"]
}}

IMPORTANT:
1. Use technical, scientific language (phase separation, condensates, regulatory circuits, etc.)
2. Only include findings that are NEW in THIS paper
3. Be specific about molecules, proteins, and mechanisms
4. Use third-person perspective
5. Output ONLY the JSON, no other text

JSON OUTPUT:
"""
        
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # 마크다운 제거
        if text.startswith('```json'):
            text = text[7:]
        if text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
        
        result = json.loads(text.strip())
        return result
    
    except Exception as e:
        st.error(f"요약 실패: {e}")
        return None

def upload_to_notion(paper, summary_data, notion_token, database_id):
    """Notion에 논문 업로드"""
    try:
        notion = Client(auth=notion_token)
        
        # Publication Year 추출
        pub_year = None
        if paper['pub_date']:
            try:
                pub_year = int(paper['pub_date'].split()[0])
            except:
                pass
        
        # 페이지 속성
        properties = {
            "Name": {
                "title": [{"text": {"content": paper['title']}}]
            },
            "Author": {
                "rich_text": [{"text": {"content": paper['authors']}}]
            },
            "Journal": {
                "rich_text": [{"text": {"content": paper['journal']}}]
            },
            "Research Area": {
                "multi_select": [{"name": kw} for kw in summary_data.get('keywords', [])[:5]]
            }
        }
        
        if pub_year:
            properties["Publication Year"] = {"number": pub_year}
        
        if paper.get('doi'):
            properties["DOI"] = {"url": f"https://doi.org/{paper['doi']}"}
        
        if paper.get('pubmed_url'):
            properties["PubMed"] = {"url": paper['pubmed_url']}
        
        # 페이지 내용
        children = []
        
        # Summary
        children.append({
            "object": "block",
            "type": "heading_1",
            "heading_1": {"rich_text": [{"text": {"content": "Summary"}}]}
        })
        children.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"text": {"content": summary_data.get('main_summary', '')}}]}
        })
        
        # Key Findings
        children.append({
            "object": "block",
            "type": "heading_1",
            "heading_1": {"rich_text": [{"text": {"content": "Key Findings"}}]}
        })
        for finding in summary_data.get('main_findings', []):
            children.append({
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": [{"text": {"content": finding}}]}
            })
        
        # Keywords
        children.append({
            "object": "block",
            "type": "heading_1",
            "heading_1": {"rich_text": [{"text": {"content": "Keywords"}}]}
        })
        keywords_text = ', '.join(summary_data.get('keywords', []))
        children.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"text": {"content": keywords_text}}]}
        })
        
        # Abstract
        children.append({
            "object": "block",
            "type": "heading_1",
            "heading_1": {"rich_text": [{"text": {"content": "Abstract"}}]}
        })
        abstract = paper.get('abstract', '')
        for i in range(0, len(abstract), 2000):
            chunk = abstract[i:i+2000]
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": chunk}}]}
            })
        
        # Links
        children.append({
            "object": "block",
            "type": "heading_1",
            "heading_1": {"rich_text": [{"text": {"content": "Links"}}]}
        })
        if paper.get('pubmed_url'):
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"text": {"content": "PubMed: "}},
                        {"text": {"content": paper['pubmed_url'], "link": {"url": paper['pubmed_url']}}}
                    ]
                }
            })
        if paper.get('doi'):
            doi_url = f"https://doi.org/{paper['doi']}"
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"text": {"content": "DOI: "}},
                        {"text": {"content": doi_url, "link": {"url": doi_url}}}
                    ]
                }
            })
        
        # Notion 페이지 생성
        page = notion.pages.create(
            parent={"database_id": database_id},
            properties=properties,
            children=children
        )
        
        return page['url']
    
    except Exception as e:
        st.error(f"Notion 업로드 실패: {e}")
        return None

# 메인 UI
st.title("📄 Single Paper Curator")
st.markdown("개별 논문을 Title 또는 DOI로 검색하여 자동 요약 및 Notion 업로드")
st.markdown("---")

# Credentials 로드
notion_token, papers_database_id, gemini_api_key = load_credentials()

# 사이드바 - 설정
with st.sidebar:
    st.header("⚙️ 설정")
    
    if not (notion_token and papers_database_id and gemini_api_key):
        st.error("⚠️ Streamlit Secrets 설정 필요")
        st.markdown("""
        Streamlit Cloud → App settings → Secrets에 추가:
        ```
        NOTION_TOKEN = "your_token"
        PAPERS_DATABASE_ID = "your_db_id"
        GEMINI_API_KEY = "your_api_key"
        ```
        """)
    else:
        st.success("✅ API 설정 완료")
    
    st.markdown("---")
    st.markdown("### 📚 사용 방법")
    st.markdown("""
    1. Title 또는 DOI 입력
    2. 검색 결과 확인
    3. 요약 및 업로드 실행
    """)

# 메인 영역
col1, col2 = st.columns([2, 1])

with col1:
    search_type = st.radio("검색 방식", ["Title", "DOI", "PMID"], horizontal=True)
    
    if search_type == "Title":
        query = st.text_input("논문 제목 입력", placeholder="예: Florigen activation complex...")
    elif search_type == "DOI":
        query = st.text_input("DOI 입력", placeholder="예: 10.1038/s41586-025-09704-6")
    else:  # PMID
        query = st.text_input("PMID 입력", placeholder="예: 36137053")
    
    search_button = st.button("🔍 검색", type="primary", use_container_width=True)

with col2:
    st.markdown("### 💡 Tip")
    if search_type == "Title":
        st.info("제목의 일부만 입력해도 검색됩니다")
    elif search_type == "DOI":
        st.info("DOI는 정확하게 입력해주세요")
    else:  # PMID
        st.info("PMID는 가장 정확한 검색 방법입니다")

st.markdown("---")

# 검색 실행
if search_button and query:
    with st.spinner("검색 중..."):
        if search_type == "Title":
            pmids = search_by_title(query)
        elif search_type == "DOI":
            pmids = search_by_doi(query)
        else:  # PMID
            # PMID는 직접 사용
            pmids = [query.strip()]
            st.success(f"✅ PMID 입력: {pmids[0]}")
        
        if not pmids:
            st.error("❌ 검색 결과가 없습니다. 다시 시도해주세요.")
        else:
            st.success(f"✅ {len(pmids)}개 논문 발견!")
            
            # 논문 정보 가져오기
            papers = []
            for pmid in pmids[:5]:  # 최대 5개
                paper = fetch_paper_details(pmid)
                if paper:
                    papers.append(paper)
            
            # Session state에 저장
            st.session_state['search_results'] = papers

# 검색 결과 표시
if 'search_results' in st.session_state and st.session_state['search_results']:
    st.subheader("🔍 검색 결과")
    
    for i, paper in enumerate(st.session_state['search_results']):
        with st.expander(f"📄 {paper['title']}", expanded=(i==0)):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**저자:** {paper['authors']}")
                st.markdown(f"**저널:** {paper['journal']} ({paper['pub_date']})")
                st.markdown(f"**PMID:** {paper['pmid']}")
                if paper['doi']:
                    st.markdown(f"**DOI:** {paper['doi']}")
                
                with st.expander("📖 초록 보기"):
                    if paper['abstract']:
                        st.write(paper['abstract'])
                    else:
                        st.warning("초록 없음")
                
                st.markdown(f"🔗 [PubMed]({paper['pubmed_url']})")
            
            with col2:
                if st.button("✅ 이 논문 선택", key=f"select_{paper['pmid']}", use_container_width=True):
                    st.session_state['selected_paper'] = paper
                    st.success("선택됨!")
                    st.rerun()

# 선택된 논문 처리
if 'selected_paper' in st.session_state:
    st.markdown("---")
    st.subheader("📝 선택된 논문")
    
    paper = st.session_state['selected_paper']
    
    st.info(f"**{paper['title']}**")
    st.markdown(f"*{paper['authors']}* | {paper['journal']} | {paper['pub_date']}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 요약 및 Notion 업로드", type="primary", use_container_width=True):
            if not (notion_token and papers_database_id and gemini_api_key):
                st.error("⚠️ API 설정을 먼저 완료해주세요")
            elif not paper.get('abstract'):
                st.warning("⚠️ 초록이 없어 요약 품질이 낮을 수 있습니다. 계속하시겠습니까?")
            else:
                with st.spinner("⏳ Gemini로 요약 중..."):
                    summary = summarize_with_gemini(paper, gemini_api_key)
                    time.sleep(2)
                
                if summary:
                    st.success("✅ 요약 완료!")
                    
                    with st.expander("📝 요약 결과 미리보기"):
                        st.markdown(f"**Summary:** {summary.get('main_summary', '')}")
                        st.markdown("**Key Findings:**")
                        for j, finding in enumerate(summary.get('main_findings', []), 1):
                            st.markdown(f"{j}. {finding}")
                        st.markdown(f"**Keywords:** {', '.join(summary.get('keywords', []))}")
                    
                    with st.spinner("⏳ Notion에 업로드 중..."):
                        notion_url = upload_to_notion(paper, summary, notion_token, papers_database_id)
                    
                    if notion_url:
                        st.success("✅ Notion 업로드 완료!")
                        st.balloons()
                        st.markdown(f"[🔗 Notion에서 보기]({notion_url})")
                        
                        # 초기화
                        if st.button("🔄 새로운 논문 검색"):
                            del st.session_state['selected_paper']
                            del st.session_state['search_results']
                            st.rerun()
    
    with col2:
        if st.button("↩️ 다른 논문 선택", use_container_width=True):
            del st.session_state['selected_paper']
            st.rerun()

# Footer
st.markdown("---")
st.markdown("**Single Paper Curator** | Part of PaperCurator System")
