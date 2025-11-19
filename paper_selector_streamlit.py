"""
PaperCurator - Streamlit Paper Selector
GitHub Repository에서 최신 논문을 자동으로 로드하고, 선택 후 GitHub에 자동 커밋
"""

import streamlit as st
import json
import requests
from datetime import datetime
import base64

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

@st.cache_data(ttl=300)
def load_latest_papers():
    """GitHub Repository에서 최신 논문 JSON 자동 로드"""
    try:
        response = requests.get(LATEST_PAPERS_URL)
        response.raise_for_status()
        papers = response.json()
        return papers, None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return None, "아직 검색 결과가 없습니다."
        return None, f"데이터 로드 실패: {str(e)}"
    except Exception as e:
        return None, f"오류 발생: {str(e)}"

def commit_to_github(selected_papers, github_token):
    """선택된 논문을 GitHub에 자동 커밋"""
    try:
        # GitHub API URL
        api_url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/selected_papers.json"
        
        # JSON 데이터 준비
        content = json.dumps(selected_papers, indent=2, ensure_ascii=False)
        encoded_content = base64.b64encode(content.encode()).decode()
        
        # 기존 파일 SHA 가져오기 (있으면)
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        get_response = requests.get(api_url, headers=headers)
        sha = None
        if get_response.status_code == 200:
            sha = get_response.json()['sha']
        
        # 커밋 데이터
        commit_data = {
            "message": f"📝 Selected papers - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "content": encoded_content,
            "branch": GITHUB_BRANCH
        }
        
        if sha:
            commit_data["sha"] = sha
        
        # GitHub에 커밋
        response = requests.put(api_url, headers=headers, json=commit_data)
        response.raise_for_status()
        
        return True, "✅ GitHub에 자동 커밋 완료! 자동 요약이 곧 시작됩니다."
    
    except Exception as e:
        return False, f"❌ GitHub 커밋 실패: {str(e)}"

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
    
    if papers and 'fetch_date' in papers[0]:
        st.info(f"🕒 검색 일시: {papers[0]['fetch_date']}")
    
    if 'papers' not in st.session_state:
        st.session_state.papers = papers
        st.session_state.votes = {}

# 사이드바
with st.sidebar:
    st.header("📊 통계")
    
    if 'papers' in st.session_state:
        st.metric("총 논문 수", len(st.session_state.papers))
        
        if 'votes' in st.session_state:
            up_count = sum(1 for v in st.session_state.votes.values() if v == 'up')
            down_count = sum(1 for v in st.session_state.votes.values() if v == 'down')
            st.metric("👍 선택", up_count)
            st.metric("👎 제외", down_count)
            
            if up_count > 0:
                st.progress(up_count / len(st.session_state.papers))
    
    st.markdown("---")
    
    # GitHub Token 입력
    st.subheader("🔑 GitHub 설정")
    github_token = st.text_input(
        "GitHub Personal Access Token",
        type="password",
        help="Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token (repo 권한 필요)"
    )
    
    if github_token:
        st.success("✅ Token 입력 완료")
    else:
        st.warning("⚠️ 자동 커밋을 위해 Token이 필요합니다")
    
    st.markdown("---")
    
    if st.button("🔄 최신 검색 결과 다시 불러오기", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# 논문 표시
if 'papers' in st.session_state and st.session_state.papers:
    papers = st.session_state.papers
    
    # 필터링
    st.subheader("🔍 필터")
    col1, col2, col3, col4 = st.columns(4)  # 4개 컬럼으로 변경
    
    with col1:
        show_filter = st.selectbox("표시", ["전체", "선택됨", "제외됨", "미투표"])
    
    with col2:
        query_groups = ["전체"] + sorted(list(set([p.get('query_group', 'Unknown') for p in papers])))
        query_filter = st.selectbox("쿼리 그룹", query_groups)
    
    with col3:
        journals = ["전체"] + sorted(list(set([p.get('journal', 'Unknown') for p in papers])))
        journal_filter = st.selectbox("저널", journals)
    
    with col4:  # 초록 필터 추가
        abstract_filter = st.selectbox("초록", ["전체", "초록 있음", "초록 없음"])
    
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
    
    # 초록 필터 적용
    if abstract_filter == "초록 있음":
        filtered_papers = [p for p in filtered_papers if p.get('abstract') and len(p['abstract']) > 50]
    elif abstract_filter == "초록 없음":
        filtered_papers = [p for p in filtered_papers if not p.get('abstract') or len(p['abstract']) <= 50]
    
    st.markdown(f"**필터링 결과: {len(filtered_papers)}개 논문**")
    st.markdown("---")
    
    # 논문 리스트
    if filtered_papers:
        for paper in filtered_papers:
            pmid = paper['pmid']
            current_vote = st.session_state.votes.get(pmid, None)
            
            # 초록 상태 표시 추가
            has_abstract = paper.get('abstract') and len(paper['abstract']) > 50
            
            if current_vote == 'up':
                badge = "✅"
            elif current_vote == 'down':
                badge = "❌"
            else:
                badge = "📄"
            
            # 초록 없으면 경고 표시
            if not has_abstract:
                badge = f"{badge} ⚠️"
            
            col1, col2 = st.columns([5, 1])
            
            with col1:
                st.markdown(f"### {badge} {paper['title']}")
                st.markdown(f"*{paper['authors']}*")
                st.markdown(f"📚 {paper['journal']} | 📅 {paper['pub_date']} | 🔖 {paper.get('query_group', 'Unknown')}")
                
                with st.expander("📖 초록 보기"):
                    if has_abstract:
                        st.write(paper['abstract'])
                    else:
                        st.warning("⚠️ 초록 없음 - 요약 품질이 낮을 수 있습니다")
                
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
        
        # 완료 버튼
        st.markdown("## 🎯 완료")
        
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            if st.button("🚀 선택 완료 - 자동 요약 시작", type="primary", use_container_width=True):
                selected = [p for p in papers if st.session_state.votes.get(p['pmid']) == 'up']
                
                if not selected:
                    st.warning("선택된 논문이 없습니다!")
                elif not github_token:
                    st.error("⚠️ GitHub Token을 입력해주세요! (왼쪽 사이드바)")
                else:
                    # 초록 없는 논문 경고
                    no_abstract = [p for p in selected if not p.get('abstract') or len(p['abstract']) <= 50]
                    if no_abstract:
                        st.warning(f"⚠️ {len(no_abstract)}개 논문에 초록이 없습니다. 요약 품질이 낮을 수 있습니다.")
                    
                    with st.spinner("GitHub에 커밋하는 중..."):
                        success, message = commit_to_github(selected, github_token)
                    
                    if success:
                        st.success(message)
                        st.balloons()
                        st.info("📧 자동 요약이 완료되면 이메일로 알림을 받게 됩니다.")
                        
                        # GitHub Actions 링크
                        st.markdown(f"[🔗 GitHub Actions에서 진행 상황 확인](https://github.com/{GITHUB_USER}/{GITHUB_REPO}/actions)")
                    else:
                        st.error(message)
        
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
st.markdown("**PaperCurator** | Automated Paper Management System")
st.markdown("💡 **Tip**: GitHub Token 생성 → [Settings → Developer settings → Personal access tokens](https://github.com/settings/tokens)")
