"""
네이버 뉴스 검색 스크래핑 코드
- 키워드, 날짜 범위, 정렬 옵션 등을 설정하여 기사 수집
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode, quote
import time
import pandas as pd
import os
from datetime import datetime


class NaverNewsScraper:
    def __init__(self):
        self.base_url = "https://search.naver.com/search.naver"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        }
    
    def build_search_url(self, query, start_date=None, end_date=None, sort=0, start=1):
        """
        검색 URL 생성
        
        Args:
            query: 검색 키워드
            start_date: 시작 날짜 (YYYY.MM.DD 형식)
            end_date: 종료 날짜 (YYYY.MM.DD 형식)
            sort: 정렬 옵션 (0: 관련도순, 1: 최신순, 2: 오래된순)
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
            "start": start,
        }
        
        if start_date and end_date:
            params["ds"] = start_date
            params["de"] = end_date
        
        return f"{self.base_url}?{urlencode(params)}"
    
    def parse_news_list(self, html, debug=False):
        """검색 결과 페이지에서 뉴스 목록 파싱"""
        soup = BeautifulSoup(html, "html.parser")
        articles = []
        
        # 디버깅: HTML 샘플 저장
        if debug:
            debug_dir = "/app/ksubscribe_share/test/news_scarppings"
            os.makedirs(debug_dir, exist_ok=True)
            debug_file = os.path.join(debug_dir, "debug_html_sample.html")
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"  [디버그] HTML 샘플 저장: {debug_file}")
            print(f"  [디버그] HTML 길이: {len(html)} bytes")
        
        # 새로운 네이버 뉴스 구조: data-heatmap-target=".tit" 속성을 가진 링크 찾기
        # 제목 링크들 찾기
        title_links = soup.select('a[data-heatmap-target=".tit"]')
        
        if debug:
            print(f"  [디버그] 제목 링크 개수: {len(title_links)}개")
        
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
                
                # 부모 요소 찾기 (언론사, 날짜 등이 같은 부모에 있음)
                parent = title_link.find_parent(["div", "section", "article"])
                if not parent:
                    parent = title_link
                
                # 언론사 추출
                press = ""
                press_elem = parent.select_one(".sds-comps-profile-info-title-text span, .sds-comps-profile-info-title-text a")
                if press_elem:
                    press = press_elem.get_text(strip=True)
                
                # 날짜 추출
                date_text = ""
                date_spans = parent.select(".sds-comps-profile-info-subtext span.sds-comps-text")
                for span in date_spans:
                    text = span.get_text(strip=True)
                    # 날짜 형식 확인 (YYYY.MM.DD 또는 "N주 전", "N일 전" 등)
                    if "." in text and len(text) >= 8:  # YYYY.MM.DD 형식
                        date_text = text
                        break
                    elif "전" in text or "분" in text or "시간" in text:
                        date_text = text
                        break
                
                # 요약 추출
                description = ""
                desc_link = parent.select_one('a[data-heatmap-target=".body"]')
                if desc_link:
                    desc_span = desc_link.select_one("span.sds-comps-text")
                    if desc_span:
                        description = desc_span.get_text(strip=True)
                
                # 네이버 뉴스 링크 추출
                naver_link = ""
                naver_elem = parent.select_one('a[data-heatmap-target=".nav"]')
                if naver_elem:
                    naver_link = naver_elem.get("href", "")
                
                # 중복 제거 (같은 링크가 이미 있는지 확인)
                if link and not any(art.get('link') == link for art in articles):
                    articles.append({
                        "title": title,
                        "link": link,
                        "naver_link": naver_link,
                        "press": press,
                        "date": date_text,
                        "description": description,
                    })
                
            except Exception as e:
                if debug:
                    print(f"  [디버그] 파싱 오류: {e}")
                continue
        
        if debug:
            print(f"  [디버그] 최종 수집된 기사 수: {len(articles)}개")
        
        return articles
    
    def get_total_count(self, html):
        """총 검색 결과 수 추출"""
        soup = BeautifulSoup(html, "html.parser")
        count_elem = soup.select_one("div.title_desc span.title_num")
        if count_elem:
            text = count_elem.get_text(strip=True)
            # "1-10 / 1,234건" 형식에서 숫자 추출
            import re
            match = re.search(r"[\d,]+건", text)
            if match:
                return int(match.group().replace(",", "").replace("건", ""))
        return 0
    
    def scrape(self, query, start_date=None, end_date=None, sort=0, max_pages=5, delay=1.0, debug=False):
        """
        뉴스 검색 스크래핑 실행
        
        Args:
            query: 검색 키워드
            start_date: 시작 날짜 (YYYY.MM.DD)
            end_date: 종료 날짜 (YYYY.MM.DD)
            sort: 정렬 (0: 관련도, 1: 최신, 2: 오래된순)
            max_pages: 최대 페이지 수
            delay: 요청 간 딜레이 (초)
            debug: 디버깅 모드 (기본값: False)
        
        Returns:
            list: 수집된 기사 목록
        """
        all_articles = []
        
        for page in range(max_pages):
            start = page * 10 + 1
            url = self.build_search_url(query, start_date, end_date, sort, start)
            
            print(f"[페이지 {page + 1}] 수집 중... (start={start})")
            if debug:
                print(f"  [디버그] URL: {url}")
            
            try:
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
                
                if debug:
                    print(f"  [디버그] 응답 상태 코드: {response.status_code}")
                    print(f"  [디버그] 응답 헤더 Content-Type: {response.headers.get('Content-Type', 'N/A')}")
                    print(f"  [디버그] 응답 본문 길이: {len(response.text)} bytes")
                    # HTML에서 특정 키워드 확인
                    if "한국전력" in response.text:
                        print(f"  [디버그] ✅ '한국전력' 키워드가 HTML에 포함됨")
                    else:
                        print(f"  [디버그] ⚠️  '한국전력' 키워드가 HTML에 없음")
                    # 뉴스 관련 클래스 확인
                    if "news_area" in response.text or "list_news" in response.text:
                        print(f"  [디버그] ✅ 뉴스 관련 클래스가 HTML에 포함됨")
                    else:
                        print(f"  [디버그] ⚠️  뉴스 관련 클래스가 HTML에 없음")
                
                articles = self.parse_news_list(response.text, debug=debug)
                
                if not articles:
                    print("더 이상 기사가 없습니다.")
                    break
                
                all_articles.extend(articles)
                print(f"  → {len(articles)}개 기사 수집")
                
                # 첫 페이지에서 총 개수 확인
                if page == 0:
                    total = self.get_total_count(response.text)
                    print(f"  → 총 검색 결과: {total}건")
                
                time.sleep(delay)
                
            except requests.RequestException as e:
                print(f"요청 오류: {e}")
                break
        
        return all_articles
    
    def scrape_article_content(self, url, delay=0.5):
        """
        개별 기사 본문 스크래핑 (네이버 뉴스 링크인 경우)
        """
        if "news.naver.com" not in url:
            return None
        
        try:
            time.sleep(delay)
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 네이버 뉴스 본문 선택자들
            content_elem = (
                soup.select_one("article#dic_area") or
                soup.select_one("div#articleBodyContents") or
                soup.select_one("div._article_body_contents")
            )
            
            if content_elem:
                # 스크립트, 스타일 태그 제거
                for tag in content_elem.select("script, style"):
                    tag.decompose()
                return content_elem.get_text(strip=True, separator="\n")
            
        except Exception as e:
            print(f"본문 스크래핑 오류: {e}")
        
        return None
    
    def to_dataframe(self, articles):
        """결과를 DataFrame으로 변환"""
        return pd.DataFrame(articles)
    
    def to_csv(self, articles, filename):
        """
        결과를 CSV로 저장
        도커 컨테이너 환경: /app/ksubscribe_share/test/news_scarppings
        """
        df = self.to_dataframe(articles)
        
        # 도커 컨테이너 내부 경로 설정
        output_dir = "/app/ksubscribe_share/test/news_scarppings"
        os.makedirs(output_dir, exist_ok=True)
        
        # 절대 경로로 파일 저장
        if not os.path.isabs(filename):
            filepath = os.path.join(output_dir, filename)
        else:
            filepath = filename
        
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        print(f"저장 완료: {filepath}")
        return df


# 사용 예시
if __name__ == "__main__":
    scraper = NaverNewsScraper()
    
    # 검색 설정
    keyword = "한국전력"
    start_date = "2025.11.29"
    end_date = "2025.11.30"
    sort_option = 0  # 0: 관련도순, 1: 최신순
    
    print(f"=== 네이버 뉴스 검색 ===")
    print(f"키워드: {keyword}")
    print(f"기간: {start_date} ~ {end_date}")
    print(f"정렬: {'관련도순' if sort_option == 0 else '최신순'}")
    print("=" * 30)
    
    # 스크래핑 실행
    articles = scraper.scrape(
        query=keyword,
        start_date=start_date,
        end_date=end_date,
        sort=sort_option,
        max_pages=10,  # 최대 10페이지 (100개 기사)
        delay=1.0,
        debug=False  # 디버깅 모드 비활성화 (필요시 True로 변경)
    )
    
    # 결과 출력
    print(f"\n=== 수집 완료: 총 {len(articles)}개 기사 ===\n")
    
    for i, article in enumerate(articles[:5], 1):  # 상위 5개만 출력
        print(f"[{i}] {article['title']}")
        print(f"    언론사: {article['press']}")
        print(f"    날짜: {article['date']}")
        print(f"    링크: {article['link']}")
        if article['naver_link']:
            print(f"    네이버뉴스: {article['naver_link']}")
        print()
    
    # CSV 저장
    if articles:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"naver_news_{keyword}_{timestamp}.csv"
        scraper.to_csv(articles, filename)