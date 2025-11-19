"""
PaperCurator - 자동 요약 및 Notion 업로드
selected_papers.json을 읽어서 Gemini로 요약하고 Notion에 업로드
"""

import json
import time
from datetime import datetime
import google.generativeai as genai
from notion_client import Client

class PaperSummarizer:
    def __init__(self, settings_file='notion_settings.json'):
        """설정 파일 로드"""
        with open(settings_file, 'r') as f:
            self.settings = json.load(f)
        
        # Gemini 설정
        genai.configure(api_key=self.settings['gemini_api_key'])
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Notion 설정
        self.notion = Client(auth=self.settings['notion_token'])
        self.database_id = self.settings['papers_database_id']
    
    def summarize_paper(self, paper):
        """Gemini로 논문 요약"""
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
        
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            # 마크다운 코드 블록 제거
            if text.startswith('```json'):
                text = text[7:]
            if text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
            
            result = json.loads(text.strip())
            print(f"✅ 요약 완료: {paper['title'][:50]}...")
            return result
        
        except Exception as e:
            print(f"❌ 요약 실패 ({paper['title'][:30]}...): {e}")
            return {
                "main_summary": "자동 요약 실패",
                "main_findings": [],
                "keywords": []
            }
    
    def create_notion_page(self, paper, summary_data):
        """Notion에 논문 페이지 생성"""
        try:
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
            
            # Publication Year 추가 (있을 경우)
            if pub_year:
                properties["Publication Year"] = {"number": pub_year}
            
            # DOI 추가 (있을 경우)
            if paper.get('doi'):
                properties["DOI"] = {"url": f"https://doi.org/{paper['doi']}"}
            
            # PubMed 추가
            if paper.get('pubmed_url'):
                properties["PubMed"] = {"url": paper['pubmed_url']}
            
            # 페이지 내용 구성
            children = []
            
            # Summary 섹션
            children.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"text": {"content": "Summary"}}]
                }
            })
            
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"text": {"content": summary_data.get('main_summary', 'No summary available')}}]
                }
            })
            
            # Key Findings 섹션
            children.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"text": {"content": "Key Findings"}}]
                }
            })
            
            for i, finding in enumerate(summary_data.get('main_findings', []), 1):
                children.append({
                    "object": "block",
                    "type": "numbered_list_item",
                    "numbered_list_item": {
                        "rich_text": [{"text": {"content": finding}}]
                    }
                })
            
            # Keywords 섹션
            children.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"text": {"content": "Keywords"}}]
                }
            })
            
            keywords_text = ', '.join(summary_data.get('keywords', []))
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"text": {"content": keywords_text}}]
                }
            })
            
            # Abstract 섹션
            children.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"text": {"content": "Abstract"}}]
                }
            })
            
            # Abstract를 2000자 단위로 분할 (Notion 제한)
            abstract = paper.get('abstract', 'No abstract available')
            for i in range(0, len(abstract), 2000):
                chunk = abstract[i:i+2000]
                children.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": chunk}}]
                    }
                })
            
            # Links 섹션
            children.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"text": {"content": "Links"}}]
                }
            })
            
            # PubMed 링크
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
            
            # DOI 링크
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
            page = self.notion.pages.create(
                parent={"database_id": self.database_id},
                properties=properties,
                children=children
            )
            
            print(f"✅ Notion 업로드: {paper['title'][:50]}...")
            return page['url']
        
        except Exception as e:
            print(f"❌ Notion 업로드 실패 ({paper['title'][:30]}...): {e}")
            return None
    
    def process_selected_papers(self, json_file='selected_papers.json'):
        """선택된 논문들 처리"""
        print("="*60)
        print("PaperCurator - 자동 요약 및 Notion 업로드 시작")
        print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")
        
        # JSON 로드
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                papers = json.load(f)
            print(f"📚 {len(papers)}개 논문 로드\n")
        except FileNotFoundError:
            print(f"❌ {json_file} 파일을 찾을 수 없습니다.")
            return
        except Exception as e:
            print(f"❌ 파일 로드 실패: {e}")
            return
        
        results = []
        
        for i, paper in enumerate(papers, 1):
            print(f"\n[{i}/{len(papers)}] 처리 중: {paper['title'][:50]}...")
            
            # 1. Gemini 요약
            summary_data = self.summarize_paper(paper)
            time.sleep(2)  # API rate limit
            
            # 2. Notion 업로드
            notion_url = self.create_notion_page(paper, summary_data)
            
            results.append({
                'title': paper['title'],
                'pmid': paper['pmid'],
                'notion_url': notion_url,
                'success': notion_url is not None
            })
            
            time.sleep(1)  # Rate limit
        
        # 결과 요약
        success_count = sum(1 for r in results if r['success'])
        
        print("\n" + "="*60)
        print(f"✅ 완료: {success_count}/{len(papers)}개 성공")
        print("="*60)
        
        return results


if __name__ == "__main__":
    summarizer = PaperSummarizer()
    summarizer.process_selected_papers()
