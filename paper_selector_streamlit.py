"""
PaperCurator - Streamlit Paper Selector
GitHub Actions에서 생성된 JSON을 읽고, 선택된 논문을 저장
"""

import streamlit as st
import json
import os
from datetime import datetime
import requests

# 페이지 설정
st.set_page_config(
    page_title="PaperCurator - Paper Selector",
    page_icon="📚",
    layout="wide"
)

# GitHub raw URL 설정
GITHUB_USER = "Du-Hwa"  # GitHub 사용자명
GITHUB_REPO = "PaperCurator"
GITHUB_BRANCH = "main"

def load_latest_papers_from_github():
    """GitHub Actions Artifacts에서 최신 논문 JSON 가져오기"""
    # GitHub API를 통해 최신 workflow run 가져오기
    api_url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/actions/runs"
    
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        runs = response.json()
        
        if runs['workflow_runs']:
            # 가장 최근 성공한 run 찾기
            for run in runs['workflow_runs']:
                if run['conclusion'] == 'success':
                    # Artifacts URL
                    artifacts_url = run['artifacts_url']
                    artifacts_response = requests.get(artifacts_url)
                    artifacts_data = artifacts_response.json()
                    
                    if artifacts_data['artifacts']:
                        # 첫 번째 artifact 다운로드
                        artifact_url = artifacts_data['artifacts'][0]['archive_download_url']
                        st.info(f"최신 검색 결과: {run['created_at']}")
                        st.warning("⚠️ GitHub Artifacts는 인증이 필요합니다. 로컬 JSON 파일을 업로드해주세요.")
                        return None
        
        st.warning("최근 성공한 workflow run을 찾을 수 없습니다.")
        return None
    
    except Exception as e:
        st.error(f"GitHub에서 데이터를 가져오는데 실패했습니다: {e}")
        return None

def save_selected_papers(selected_papers, filename="selected_papers.json"):
    """선택된 논문을 JSON 파일로 저장"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(selected_papers, f, indent=2, ensure_ascii=False)
    return filename

# 메인 UI
st.title("📚 PaperCurator - Paper Selector")
st.markdown("---")

# 사이드바 - 파일 업로드
with st.sidebar:
    st.header("📥 논문 데이터 로드")
    
    # 방법 1: 파일 업로드
    uploaded_file = st.file_uploader(
        "JSON 파일 업로드",
        type=['json'],
        help="GitHub Actions에서 다운로드한 weekly_papers_*.json 파일을 업로드하세요"
    )
    
    st.markdown("---")
    
    # 통계 정보
    if 'papers' in st.session_state and st.session_state.papers:
        st.metric("총 논문 수", len(st.session_state.papers))
        if 'votes' in st.session_state:
            up_count = sum(1 for v in st.session_state.votes.values() if v == 'up')
            down_count = sum(1 for v in st.session_state.votes.values() if v == 'down')
            st.metric("👍 선택", up_count)
            st.metric("👎 제외", down_count)

# 데이터 로드
papers = []

if uploaded_file:
    try:
        papers = json.load(uploaded_file)
        st.success(f"✅ {len(papers)}개 논문 로드 완료!")
        
        # Session state 초기화
        if 'papers' not in st.session_state:
            st.session_state.papers = papers
            st.session_state.votes = {}
            st.session_state.current_index = 0
    except Exception as e:
        st.error(f"JSON 파일 로드 실패: {e}")

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
        query_filter = st.selectbox(
            "쿼리 그룹",
            ["전체"] + list(set([p.get('query_group', 'Unknown') for p in papers]))
        )
    
    with col3:
        journal_filter = st.selectbox(
            "저널",
            ["전체"] + sorted(list(set([p.get('journal', 'Unknown') for p in papers])))
        )
    
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
        for i, paper in enumerate(filtered_papers):
            pmid = paper['pmid']
            current_vote = st.session_state.votes.get(pmid, None)
            
            # 투표 상태에 따른 배경색
            if current_vote == 'up':
                st.markdown("### ✅ 선택됨")
            elif current_vote == 'down':
                st.markdown("### ❌ 제외됨")
            else:
                st.markdown("### 📄")
            
            col1, col2 = st.columns([4, 1])
            
            with col1:
                # 제목
                st.markdown(f"**{paper['title']}**")
                
                # 저자 및 저널
                st.markdown(f"*{paper['authors']}*")
                st.markdown(f"📚 {paper['journal']} | 📅 {paper['pub_date']} | 🔖 Query: {paper.get('query_group', 'Unknown')}")
                
                # 초록 (접기)
                with st.expander("초록 보기"):
                    st.write(paper['abstract'] if paper['abstract'] else "초록 없음")
                
                # 링크
                st.markdown(f"🔗 [PubMed]({paper['pubmed_url']})")
            
            with col2:
                st.markdown("#### 선택")
                
                # 투표 버튼
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
                # 선택된 논문만 필터링
                selected = [p for p in papers if st.session_state.votes.get(p['pmid']) == 'up']
                
                if selected:
                    filename = save_selected_papers(selected)
                    st.success(f"✅ {len(selected)}개 논문 저장 완료: {filename}")
                    st.balloons()
                    
                    # 다운로드 버튼
                    with open(filename, 'r', encoding='utf-8') as f:
                        st.download_button(
                            label="📥 JSON 다운로드",
                            data=f.read(),
                            file_name=filename,
                            mime="application/json"
                        )
                else:
                    st.warning("선택된 논문이 없습니다!")
        
        with col2:
            if st.button("🔄 초기화", use_container_width=True):
                st.session_state.votes = {}
                st.rerun()
        
        with col3:
            up_count = sum(1 for v in st.session_state.votes.values() if v == 'up')
            st.metric("선택됨", up_count)
    
    else:
        st.info("필터 조건에 맞는 논문이 없습니다.")

else:
    st.info("👈 왼쪽 사이드바에서 JSON 파일을 업로드해주세요.")
    
    st.markdown("### 사용 방법")
    st.markdown("""
    1. GitHub Actions에서 생성된 `weekly_papers_*.json` 파일 다운로드
    2. 왼쪽 사이드바에서 파일 업로드
    3. 논문 리뷰하며 👍/👎 선택
    4. "선택 완료 - 저장" 클릭
    5. `selected_papers.json` 생성됨 → 자동 요약 시작
    """)

# Footer
st.markdown("---")
st.markdown("**PaperCurator** | Automated Paper Management System")
