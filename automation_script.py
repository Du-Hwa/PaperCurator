"""
PaperCurator - 통합 자동화 스크립트
Notion 쿼리 → PubMed 검색 → 결과 저장 → 알림
"""

import json
import sys
from datetime import datetime
import requests
from Bio import Entrez
from xml.etree import ElementTree as ET
import time
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class PaperCuratorAutomation:
    def __init__(self, settings_file='notion_settings.json'):
        """설정 파일 로드"""
        with open(settings_file, 'r') as f:
            self.settings = json.load(f)
        
        self.notion_token = self.settings['notion_token']
        self.query_database_id = self.settings['query_database_id']
        
        # PubMed 이메일 설정
        Entrez.email = "duhwalee@khu.ac.kr"  # 실제 이메일로 변경
    
    def read_notion_queries(self):
        """Notion에서 쿼리 설정 읽기"""
        print("📖 Notion에서 쿼리 설정 읽는 중...")
        
        url = f"https://api.notion.com/v1/databases/{self.query_database_id}/query"
        headers = {
            "Authorization": f"Bearer {self.notion_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, headers=headers, json={})
        data = response.json()
        
        query_groups = []
        default_search_days = 7
        
        for page in data.get('results', []):
            props = page['properties']
            
            # Active 체크
            active = props.get('Active', {}).get('checkbox', False)
            if not active:
                continue
            
            name = props['Name']['title'][0]['plain_text'] if props['Name']['title'] else ''
            description = props['Description']['rich_text'][0]['plain_text'] if props['Description']['rich_text'] else ''
            journals_str = props['Journals']['rich_text'][0]['plain_text'] if props['Journals']['rich_text'] else ''
            title_kw = props['Title Keywords']['rich_text'][0]['plain_text'] if props['Title Keywords']['rich_text'] else ''
            abstract_kw = props['Abstract Keywords']['rich_text'][0]['plain_text'] if props['Abstract Keywords']['rich_text'] else ''
            title_match = props['Title Match Type']['select']['name'] if props['Title Match Type'].get('select') else 'OR'
            abstract_match = props['Abstract Match Type']['select']['name'] if props['Abstract Match Type'].get('select') else 'OR'
            require_abstract = props['Require Abstract Keywords']['checkbox']
            search_days = props['Search Days Back']['number'] if props['Search Days Back']['number'] else 7
            
            default_search_days = search_days
            
            query_group = {
                "name": name,
                "description": description,
                "journals": [j.strip() for j in journals_str.split(',') if j.strip()],
                "title_keywords": [k.strip() for k in title_kw.split(',') if k.strip()],
                "abstract_keywords": [k.strip() for k in abstract_kw.split(',') if k.strip()],
                "title_match_type": title_match,
                "abstract_match_type": abstract_match,
                "require_abstract_keywords": require_abstract
            }
            query_groups.append(query_group)
        
        config = {
            "query_groups": query_groups,
            "search_days_back": int(default_search_days),
            "max_results_per_query": 100
        }
        
        print(f"✅ {len(query_groups)}개 Active 쿼리 로드 완료")
        return config
    
    def build_pubmed_query(self, query_group, search_days_back):
        """PubMed 쿼리 문자열 생성"""
        from datetime import timedelta
        
        query_parts = []
        
        # Journal filter
        if query_group["journals"]:
            journal_queries = [f'"{j}"[Journal]' for j in query_group["journals"]]
            journal_part = "(" + " OR ".join(journal_queries) + ")"
            query_parts.append(journal_part)
        
        # Title keywords
        if query_group["title_keywords"]:
            title_queries = [f'{kw}[Title]' for kw in query_group["title_keywords"]]
            match_type = query_group["title_match_type"]
            title_part = "(" + f" {match_type} ".join(title_queries) + ")"
            query_parts.append(title_part)
        
        # Abstract keywords
        if query_group["abstract_keywords"] and query_group["require_abstract_keywords"]:
            abstract_queries = [f'{kw}[Title/Abstract]' for kw in query_group["abstract_keywords"]]
            match_type = query_group["abstract_match_type"]
            abstract_part = "(" + f" {match_type} ".join(abstract_queries) + ")"
            query_parts.append(abstract_part)
        
        full_query = " AND ".join(query_parts)
        
        # Date filter
        date_from = (datetime.now() - timedelta(days=search_days_back)).strftime("%Y/%m/%d")
        date_to = datetime.now().strftime("%Y/%m/%d")
        full_query += f' AND ("{date_from}"[Date - Publication] : "{date_to}"[Date - Publication])'
        
        return full_query
    
    def search_pubmed(self, query, max_results=100):
        """PubMed 검색"""
        try:
            url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            params = {
                'db': 'pubmed',
                'term': query,
                'retmax': max_results,
                'sort': 'pub_date',
                'retmode': 'json',
                'email': Entrez.email
            }
            response = requests.get(url, params=params, verify=False)
            response.raise_for_status()
            data = response.json()
            return data['esearchresult']['idlist']
        except Exception as e:
            print(f"❌ 검색 오류: {e}")
            return []
    
    def fetch_paper_details(self, pmids):
        """논문 상세 정보 가져오기"""
        if not pmids:
            return []
        
        papers = []
        
        try:
            batch_size = 20
            for i in range(0, len(pmids), batch_size):
                batch_pmids = pmids[i:i+batch_size]
                pmid_string = ','.join(batch_pmids)
                
                url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
                params = {
                    'db': 'pubmed',
                    'id': pmid_string,
                    'retmode': 'xml',
                    'email': Entrez.email
                }
                
                response = requests.get(url, params=params, verify=False)
                response.raise_for_status()
                
                root = ET.fromstring(response.content)
                
                for article in root.findall('.//PubmedArticle'):
                    paper = self.parse_paper_xml(article)
                    if paper:
                        papers.append(paper)
                
                time.sleep(0.5)
        
        except Exception as e:
            print(f"❌ 정보 가져오기 오류: {e}")
        
        return papers
    
    def parse_paper_xml(self, article):
        """XML 파싱"""
        try:
            pmid_elem = article.find('.//PMID')
            pmid = pmid_elem.text if pmid_elem is not None else ''
            
            title_elem = article.find('.//ArticleTitle')
            title = title_elem.text if title_elem is not None else 'No title'
            
            abstract_texts = article.findall('.//AbstractText')
            abstract = ' '.join([at.text for at in abstract_texts if at.text]) if abstract_texts else ''
            
            authors = []
            author_list = article.findall('.//Author')
            
            # 앞 3명
            for author in author_list[:3]:
                lastname = author.find('LastName')
                initials = author.find('Initials')
                if lastname is not None and initials is not None:
                    authors.append(f"{lastname.text} {initials.text}")
            
            # 저자가 7명 이상이면 ... 추가하고 뒤 3명
            if len(author_list) > 6:
                authors.append("...")
                for author in author_list[-3:]:
                    lastname = author.find('LastName')
                    initials = author.find('Initials')
                    if lastname is not None and initials is not None:
                        authors.append(f"{lastname.text} {initials.text}")
            elif len(author_list) > 3:
                # 4-6명이면 그냥 다 표시
                for author in author_list[3:]:
                    lastname = author.find('LastName')
                    initials = author.find('Initials')
                    if lastname is not None and initials is not None:
                        authors.append(f"{lastname.text} {initials.text}")
            
            authors_str = ', '.join(authors)
            
            journal_elem = article.find('.//Journal/Title')
            journal = journal_elem.text if journal_elem is not None else 'Unknown journal'
            
            year_elem = article.find('.//PubDate/Year')
            month_elem = article.find('.//PubDate/Month')
            year = year_elem.text if year_elem is not None else ''
            month = month_elem.text if month_elem is not None else ''
            pub_date_str = f"{year} {month}".strip()
            
            doi = ''
            elocation_ids = article.findall('.//ELocationID')
            for eloc in elocation_ids:
                if eloc.get('EIdType') == 'doi':
                    doi = eloc.text
                    break
            
            keywords = []
            keyword_list = article.findall('.//Keyword')
            keywords = [kw.text for kw in keyword_list if kw.text]
            
            return {
                'pmid': str(pmid),
                'doi': doi if doi else '',
                'title': str(title),
                'authors': authors_str,
                'journal': str(journal),
                'pub_date': pub_date_str,
                'abstract': str(abstract),
                'keywords': keywords,
                'pubmed_url': f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                'fetch_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        except Exception as e:
            return None
    
    def run_all_queries(self, config):
        """모든 쿼리 실행"""
        all_results = {}
        
        print(f"\n{'='*60}")
        print("PubMed 검색 시작")
        print(f"{'='*60}\n")
        
        for query_group in config["query_groups"]:
            print(f"📚 {query_group['name']}")
            
            query = self.build_pubmed_query(query_group, config["search_days_back"])
            print(f"   쿼리: {query[:100]}...")
            
            pmids = self.search_pubmed(query, config["max_results_per_query"])
            print(f"   ✅ {len(pmids)}개 논문 발견")
            
            if pmids:
                papers = self.fetch_paper_details(pmids)
                for paper in papers:
                    paper['query_group'] = query_group['name']
                all_results[query_group['name']] = papers
                print(f"   ✅ {len(papers)}개 정보 수집 완료\n")
            else:
                all_results[query_group['name']] = []
        
        return all_results
    
    def save_results(self, results):
        """결과 저장"""
        # 모든 논문 합치기
        all_papers = []
        for query_name, papers in results.items():
            all_papers.extend(papers)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"weekly_papers_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_papers, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 결과 저장: {filename}")
        print(f"   총 {len(all_papers)}개 논문")
        
        return filename, len(all_papers)
    
    def send_notification(self, filename, total_papers):
        """알림 발송 (이메일/Slack)"""
        # TODO: 이메일 또는 Slack 알림 구현
        print(f"\n📧 알림 발송 (구현 예정)")
        print(f"   파일: {filename}")
        print(f"   논문 수: {total_papers}")
        print(f"   Streamlit URL: http://localhost:8501")
    
    def run(self):
        """전체 워크플로우 실행"""
        print("="*60)
        print("PaperCurator 자동화 시작")
        print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # 1. Notion 쿼리 읽기
        config = self.read_notion_queries()
        
        # 2. PubMed 검색
        results = self.run_all_queries(config)
        
        # 3. 결과 저장
        filename, total_papers = self.save_results(results)
        
        # 4. 알림 발송
        self.send_notification(filename, total_papers)
        
        print("\n" + "="*60)
        print("✅ 자동화 완료!")
        print("="*60)
        
        return filename


if __name__ == "__main__":
    automation = PaperCuratorAutomation()
    automation.run()
