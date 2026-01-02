"""
네이버 뉴스 날짜별 개별 스크래핑 및 엑셀 저장
- 각 날짜별로 개별 스크래핑
- title, link, date만 수집
- 날짜별로 엑셀 파일 저장
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode
import time
import pandas as pd
import os
from datetime import datetime, timedelta
import sys


class NaverNewsScraper:
    def __init__(self):
        self.base_url = "https://search.naver.com/search.naver"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        }
    
    def build_search_url(self, query, target_date, sort=0, start=1):
        """
        특정 날짜의 검색 URL 생성
        
        Args:
            query: 검색 키워드
            target_date: 대상 날짜 (YYYY.MM.DD 형식)
            sort: 정렬 옵션 (0: 관련도순, 1: 최신순)
            start: 시작 위치 (페이지네이션용, 1, 11, 21, ...)
        """
        params = {
            "ssc": "tab.news.all",
            "query": query,
            "sm": "tab_opt",
            "sort": sort,
            "photo": 0,
            "field": 0,
            "pd": 3,  # 기간 직접 입력
            "ds": target_date,  # 시작일
            "de": target_date,  # 종료일 (같은 날짜)
            "start": start,
        }
        
        return f"{self.base_url}?{urlencode(params)}"
    
    def parse_news_list(self, html):
        """검색 결과 페이지에서 뉴스 목록 파싱 (title, link, date만)"""
        soup = BeautifulSoup(html, "html.parser")
        articles = []
        
        # 제목 링크들 찾기
        title_links = soup.select('a[data-heatmap-target=".tit"]')
        
        for title_link in title_links:
            try:
                # 제목 추출
                title_span = title_link.select_one("span.sds-comps-text")
                if not title_span:
                    title_span = title_link
                title = title_span.get_text(strip=True)
                
                # 링크 추출
                link = title_link.get("href", "")
                if link and link.startswith('/'):
                    link = f"https://search.naver.com{link}"
                
                # 부모 요소 찾기 (날짜가 같은 부모에 있음)
                parent = title_link.find_parent(["div", "section", "article"])
                if not parent:
                    parent = title_link
                
                # 날짜 추출
                date_text = ""
                date_spans = parent.select(".sds-comps-profile-info-subtext span.sds-comps-text")
                for span in date_spans:
                    text = span.get_text(strip=True)
                    # 날짜 형식 확인 (YYYY.MM.DD 형식 우선)
                    if "." in text and len(text) >= 8:  # YYYY.MM.DD 형식
                        date_text = text
                        break
                    elif "전" in text or "분" in text or "시간" in text:
                        date_text = text
                        break
                
                # 중복 제거 (같은 링크가 이미 있는지 확인)
                if link and not any(art.get('link') == link for art in articles):
                    articles.append({
                        "title": title,
                        "link": link,
                        "date": date_text,
                    })
                
            except Exception as e:
                continue
        
        return articles
    
    def scrape_by_date(self, query, target_date, max_pages=50, delay=1.0):
        """
        특정 날짜의 뉴스 스크래핑
        
        Args:
            query: 검색 키워드
            target_date: 대상 날짜 (YYYY.MM.DD 형식)
            max_pages: 최대 페이지 수
            delay: 요청 간 딜레이 (초)
        
        Returns:
            list: 수집된 기사 목록 (title, link, date만)
        """
        all_articles = []
        
        for page in range(max_pages):
            start = page * 10 + 1
            url = self.build_search_url(query, target_date, sort=0, start=start)
            
            print(f"  [페이지 {page + 1}] 수집 중... (start={start})")
            
            try:
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
                
                articles = self.parse_news_list(response.text)
                
                if not articles:
                    print(f"  → 더 이상 기사가 없습니다.")
                    break
                
                all_articles.extend(articles)
                print(f"  → {len(articles)}개 기사 수집 (누적: {len(all_articles)}건)")
                
                time.sleep(delay)
                
            except requests.RequestException as e:
                print(f"  → 요청 오류: {e}")
                break
        
        return all_articles
    
    def save_to_excel(self, articles, target_date, keyword):
        """
        결과를 엑셀 파일로 저장 (날짜별)
        
        Args:
            articles: 수집된 기사 목록
            target_date: 대상 날짜 (YYYY.MM.DD 형식)
            keyword: 검색 키워드
        """
        if not articles:
            print(f"  → 저장할 기사가 없습니다.")
            return None
        
        df = pd.DataFrame(articles)
        
        # 도커 컨테이너 내부 경로 설정
        output_dir = "/app/ksubscribe_share/test/news_scarppings"
        os.makedirs(output_dir, exist_ok=True)
        
        # 파일명 생성 (날짜별)
        date_str = target_date.replace(".", "")
        filename = f"naver_news_{keyword}_{date_str}.xlsx"
        filepath = os.path.join(output_dir, filename)
        
        # 엑셀 저장
        df.to_excel(filepath, index=False, engine='openpyxl')
        print(f"  → 엑셀 저장 완료: {filepath} ({len(df)}건)")
        
        return filepath


def scrape_date_range(keyword, start_date_str, end_date_str):
    """
    날짜 범위별로 개별 스크래핑 및 엑셀 저장
    
    Args:
        keyword: 검색 키워드
        start_date_str: 시작일 (YYYY.MM.DD 형식)
        end_date_str: 종료일 (YYYY.MM.DD 형식)
    """
    scraper = NaverNewsScraper()
    
    # 날짜 범위 생성
    start_date = datetime.strptime(start_date_str, "%Y.%m.%d")
    end_date = datetime.strptime(end_date_str, "%Y.%m.%d")
    
    current_date = start_date
    date_list = []
    
    while current_date <= end_date:
        date_list.append(current_date.strftime("%Y.%m.%d"))
        current_date += timedelta(days=1)
    
    print(f"=" * 60)
    print(f"네이버 뉴스 날짜별 스크래핑 시작")
    print(f"검색어: {keyword}")
    print(f"기간: {start_date_str} ~ {end_date_str}")
    print(f"총 {len(date_list)}일 수집 예정")
    print(f"=" * 60)
    print()
    
    total_articles = 0
    
    for idx, target_date in enumerate(date_list):
        print(f"[{idx + 1}/{len(date_list)}] {target_date} 수집 시작...")
        
        # 해당 날짜의 기사만 스크래핑
        articles = scraper.scrape_by_date(
            query=keyword,
            target_date=target_date,
            max_pages=50,  # 최대 50페이지 (500개 기사)
            delay=1.0
        )
        
        # 날짜별 엑셀 저장
        if articles:
            scraper.save_to_excel(articles, target_date, keyword)
            total_articles += len(articles)
            print(f"  → {target_date}: {len(articles)}건 수집 완료")
        else:
            print(f"  → {target_date}: 수집된 기사 없음")
        
        # 날짜 변경 시 1분 대기 (마지막 날짜가 아니면)
        if idx < len(date_list) - 1:
            print(f"  → 다음 날짜 조회 전 60초 대기...")
            time.sleep(60)
        print()
    
    print(f"=" * 60)
    print(f"수집 완료: 총 {total_articles}건의 기사가 저장되었습니다.")
    print(f"저장 경로: /app/ksubscribe_share/test/news_scarppings/")
    print(f"=" * 60)


if __name__ == "__main__":
    # 명령줄 인자로부터 날짜 받기
    if len(sys.argv) < 4:
        print("사용법: python collect_naver_news_by_date_excel.py <keyword> <start_date> <end_date>")
        print("예시: python collect_naver_news_by_date_excel.py 한국전력 2025.11.01 2025.11.30")
        sys.exit(1)
    
    keyword = sys.argv[1]
    start_date = sys.argv[2]
    end_date = sys.argv[3]
    
    scrape_date_range(keyword, start_date, end_date)




