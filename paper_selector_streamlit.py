"""
PaperCurator - Streamlit Paper Selector
GitHub Repository에서 최신 논문을 자동으로 로드
"""

import streamlit as st
import json
import requests
from datetime import datetime

# 페이지 설정
st.set_page_config(
    page_title="PaperCurator - Paper Selector",
    page_icon="📚",
    layout="wide"
)

# GitHub 설정
GITHUB_USER = "Du-Hwa"
GITHUB_REPO = "PaperCurator"
GITHUB_BRANCH = "main"
LATEST_PAPERS_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/latest_papers.json"

@st.cache_data(ttl=300)  # 5분 캐시
def load_latest_papers():
    """GitHub Repository에서 최신 논문 JSON 자동 로드"""
    try:
        response = requests.get(LATEST_PAPERS_URL)
        response.raise_for_status()
        papers = response.json()
        return papers, None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return None, "아직 검색 결과가 없습니다. GitHub Actions가 실행될 때까지 기다려주세요."
        return None, f"데이터 로드 실패: {str(e)}"
    except Exception as e:
        return None, f"오류 발생: {str(e)}"

def save_selected_papers(selected_papers):
    """선택된 논문을 JSON으로 생성 (다운로드용)"""
    return json.dumps(selected_papers, indent=2, ensure_ascii=False)

# 메인 UI
st.title("📚 PaperCurator - Paper Selector")
st.markdown("---")

# 자동 로드
with st.spinner("최신 검색 결과를 불러오는 중..."):
    papers, error = load_latest_papers()

if error:
    st.error(error)
    st.info("💡 GitHub Actions가 실행되면 자동으로 논문이 표시됩니다.")
    st.stop()

if papers:
    st.success(f"✅ {len(papers)}개 논문 자동 로드 완료!")
    
    # 마지막 업데이트 시간
    if papers and 'fetch_date' in papers[0]:
        st.info(f"🕒 검색 일시: {papers[0]['fetch_date']}")
    
    # Session state 초기화
    if 'papers' not in st.session_state:
        st.session_state.papers = papers
        st.session_state.votes = {}

# 사이드바 - 통계
with st.sidebar:
    st.header("📊 통계")
    
    if 'papers' in st.session_state and st.session_state.papers:
        st.metric("총 논문 수", len(st.session_state.papers))
        
        if 'votes' in st.session_state:
            up_count = sum(1 for v in st.session_state.votes.values() if v == 'up')
            down_count = sum(1 for v in st.session_state.votes.values() if v == 'down')
            st.metric("👍 선택", up_count)
            st.metric("👎 제외", down_count)
            
            if up_count > 0:
                st.progress(up_count / len(st.session_state.papers))
    
    st.markdown("---")
    
    # 새로고침 버튼
    if st.button("🔄 최신 검색 결과 다시 불러오기", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# 논문이 로드된 경우
if 'papers' in st.session_state and st.session_state.papers:
    papers = st.session_state.papers
    
    # 필터링 옵션
    st.subheader("🔍 필터")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        show_filter = st.selectbox(
            "표시",
            ["전체", "선택됨", "제외됨", "미투표"]
        )
    
    with col2:
        query_groups = ["전체"] + sorted(list(set([p.get('query_group', 'Unknown') for p in papers])))
        query_filter = st.selectbox("쿼리 그룹", query_groups)
    
    with col3:
        journals = ["전체"] + sorted(list(set([p.get('journal', 'Unknown') for p in papers])))
        journal_filter = st.selectbox("저널", journals)
    
    # 필터 적용
    filtered_papers = papers
    
    if show_filter != "전체":
        if show_filter == "선택됨":
            filtered_papers = [p for p in papers if st.session_state.votes.get(p['pmid']) == 'up']
        elif show_filter == "제외됨":
            filtered_papers = [p for p in papers if st.session_state.votes.get(p['pmid']) == 'down']
        elif show_filter == "미투표":
            filtered_papers = [p for p in papers if p['pmid'] not in st.session_state.votes]
    
    if query_filter != "전체":
        filtered_papers = [p for p in filtered_papers if p.get('query_group') == query_filter]
    
    if journal_filter != "전체":
        filtered_papers = [p for p in filtered_papers if p.get('journal') == journal_filter]
    
    st.markdown(f"**필터링 결과: {len(filtered_papers)}개 논문**")
    st.markdown("---")
    
    # 논문 표시
    if filtered_papers:
        for paper in filtered_papers:
            pmid = paper['pmid']
            current_vote = st.session_state.votes.get(pmid, None)
            
            # 투표 상태에 따른 표시
            if current_vote == 'up':
                badge = "✅"
            elif current_vote == 'down':
                badge = "❌"
            else:
                badge = "📄"
            
            col1, col2 = st.columns([5, 1])
            
            with col1:
                st.markdown(f"### {badge} {paper['title']}")
                st.markdown(f"*{paper['authors']}*")
                st.markdown(f"📚 {paper['journal']} | 📅 {paper['pub_date']} | 🔖 {paper.get('query_group', 'Unknown')}")
                
                with st.expander("📖 초록 보기"):
                    st.write(paper['abstract'] if paper['abstract'] else "초록 없음")
                
                st.markdown(f"🔗 [PubMed]({paper['pubmed_url']})")
            
            with col2:
                st.markdown("#### 선택")
                
                col_up, col_down = st.columns(2)
                
                with col_up:
                    if st.button("👍", key=f"up_{pmid}", use_container_width=True):
                        st.session_state.votes[pmid] = 'up'
                        st.rerun()
                
                with col_down:
                    if st.button("👎", key=f"down_{pmid}", use_container_width=True):
                        st.session_state.votes[pmid] = 'down'
                        st.rerun()
            
            st.markdown("---")
        
        # 하단 액션 버튼
        st.markdown("## 🎯 완료")
        
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            if st.button("💾 선택 완료 - 저장", type="primary", use_container_width=True):
                selected = [p for p in papers if st.session_state.votes.get(p['pmid']) == 'up']
                
                if selected:
                    json_str = save_selected_papers(selected)
                    
                    st.success(f"✅ {len(selected)}개 논문 선택 완료!")
                    st.balloons()
                    
                    # 다운로드 버튼
                    st.download_button(
                        label="📥 selected_papers.json 다운로드",
                        data=json_str,
                        file_name="selected_papers.json",
                        mime="application/json",
                        use_container_width=True
                    )
                    
                    st.info("💡 다운로드한 JSON 파일을 지정된 위치에 저장하면 자동 요약이 시작됩니다.")
                else:
                    st.warning("선택된 논문이 없습니다!")
        
        with col2:
            if st.button("🔄 선택 초기화", use_container_width=True):
                st.session_state.votes = {}
                st.rerun()
        
        with col3:
            up_count = sum(1 for v in st.session_state.votes.values() if v == 'up')
            st.metric("선택", up_count)
    
    else:
        st.info("필터 조건에 맞는 논문이 없습니다.")

# Footer
st.markdown("---")
st.markdown("**PaperCurator** | Automated Paper Management System | 🤖 Auto-loads from GitHub")
