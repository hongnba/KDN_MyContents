"""
네이버 뉴스 수집 (crawl4ai 버전)
crawl4ai를 사용하여 JavaScript로 동적 로딩되는 콘텐츠도 수집 가능
"""
import asyncio
import json
import os
import pandas as pd
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False
    print("⚠️  crawl4ai가 설치되어 있지 않습니다.")
    print("   설치 방법: pip install crawl4ai && crawl4ai-setup")


async def get_naver_news_data_crawl4ai(keyword, start_date_str, end_date_str):
    """
    crawl4ai를 사용하여 네이버 뉴스 기사를 날짜별로 개별 조회하여 수집함.
    
    :param keyword: 검색어 (예: '한국전력')
    :param start_date_str: 시작일 (YYYYMMDD 형식, 예: '20251129')
    :param end_date_str: 종료일 (YYYYMMDD 형식, 예: '20251130')
    :return: 수집된 기사 데이터 리스트
    """
    if not CRAWL4AI_AVAILABLE:
        print("❌ crawl4ai가 설치되어 있지 않아 실행할 수 없습니다.")
        return []
    
    # 날짜 범위 생성
    start_date = datetime.strptime(start_date_str, "%Y%m%d")
    end_date = datetime.strptime(end_date_str, "%Y%m%d")
    
    # 수집 결과 저장용 리스트
    all_news_data = []
    
    # 브라우저 설정 - 봇 감지 회피 및 최적화
    browser_config = BrowserConfig(
        headless=True,
        stealth_mode=True,  # 봇 감지 회피 (중요!)
        timeout=60,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        verbose=False
    )
    
    async with AsyncWebCrawler(browser_config=browser_config) as crawler:
        current_date = start_date
        
        while current_date <= end_date:
            # 날짜 포맷 변환 (YYYY.MM.DD)
            ds_de = current_date.strftime("%Y.%m.%d")
            nso_date = current_date.strftime("%Y%m%d")
            
            # 네이버 뉴스 검색 URL 구성 (일 단위 검색용 파라미터 적용)
            url = (
                f"https://search.naver.com/search.naver?where=news&query={keyword}"
                f"&pd=3&ds={ds_de}&de={ds_de}"
                f"&nso=so:dd,p:from{nso_date}to{nso_date},a:all"
            )
            
            print(f"[{ds_de}] 크롤링 중...")
            
            try:
                # crawl4ai로 페이지 크롤링 (가이드 권장 설정 적용)
                result = await crawler.arun(
                    url=url,
                    scroll_to_bottom=True,  # 페이지 하단까지 스크롤 (동적 콘텐츠 로딩)
                    wait_for_selector="ul.list_news, li.bx, a.news_tit",  # 뉴스 목록 요소 대기
                    extract_images=False,  # 이미지는 추출하지 않음
                    bypass_cache=True  # 캐시 우회하여 최신 데이터 수집
                )
                
                if result.success and result.html:
                    # BeautifulSoup으로 HTML 파싱
                    soup = BeautifulSoup(result.html, 'lxml')
                    
                    # 기사 아이템 추출 (여러 선택자 시도)
                    # 네이버 뉴스 검색 결과의 주요 선택자들
                    articles = soup.select("ul.list_news > li.bx")
                    
                    if not articles:
                        articles = soup.select("div.news_wrap > div.news_area")
                    if not articles:
                        articles = soup.select("li.bx")
                    if not articles:
                        # 추가 선택자 시도
                        articles = soup.select("div.info_group")
                    if not articles:
                        articles = soup.select("div.news_info")
                    
                    day_article_count = 0
                    for item in articles:
                        # 제목과 링크 추출 (여러 선택자 시도)
                        title_tag = item.select_one("a.news_tit")
                        if not title_tag:
                            title_tag = item.select_one("a._sp_each_title")
                        if not title_tag:
                            title_tag = item.find("a", class_="news_tit")
                        
                        if title_tag:
                            title = title_tag.get_text(strip=True)
                            link = title_tag.get('href')
                            
                            # 상대 경로인 경우 절대 경로로 변환
                            if link and link.startswith('/'):
                                link = f"https://search.naver.com{link}"
                            
                            # 중복 제거 (같은 URL이 이미 있는지 확인)
                            if not any(existing.get('URL') == link for existing in all_news_data):
                                all_news_data.append({
                                    "수집일": ds_de,
                                    "제목": title,
                                    "URL": link
                                })
                                day_article_count += 1
                    
                    print(f"  [{ds_de}] {day_article_count}건 수집 완료")
                    
                    # 페이지네이션 처리 (추가 페이지가 있는 경우)
                    page = 2
                    max_pages = 400  # 최대 페이지 수 제한
                    
                    while page <= max_pages:
                        start_val = (page - 1) * 10 + 1
                        page_url = f"{url}&start={start_val}"
                        
                        # 페이지네이션 크롤링 (동일한 설정 적용)
                        page_result = await crawler.arun(
                            url=page_url,
                            scroll_to_bottom=True,
                            wait_for_selector="ul.list_news, li.bx, a.news_tit",
                            extract_images=False,
                            bypass_cache=True
                        )
                        
                        if not page_result.success or not page_result.html:
                            break
                        
                        page_soup = BeautifulSoup(page_result.html, 'lxml')
                        page_articles = page_soup.select("ul.list_news > li.bx")
                        
                        if not page_articles:
                            break
                        
                        page_article_count = 0
                        for item in page_articles:
                            # 제목과 링크 추출 (여러 선택자 시도)
                            title_tag = item.select_one("a.news_tit")
                            if not title_tag:
                                title_tag = item.select_one("a._sp_each_title")
                            if not title_tag:
                                title_tag = item.find("a", class_="news_tit")
                            
                            if title_tag:
                                title = title_tag.get_text(strip=True)
                                link = title_tag.get('href')
                                
                                # 상대 경로인 경우 절대 경로로 변환
                                if link and link.startswith('/'):
                                    link = f"https://search.naver.com{link}"
                                
                                # 중복 제거
                                if not any(existing.get('URL') == link for existing in all_news_data):
                                    all_news_data.append({
                                        "수집일": ds_de,
                                        "제목": title,
                                        "URL": link
                                    })
                                    page_article_count += 1
                        
                        if page_article_count == 0:
                            break
                        
                        print(f"  [{ds_de}] 페이지 {page}: {page_article_count}건 수집 (누적: {len([x for x in all_news_data if x['수집일'] == ds_de])}건)")
                        
                        page += 1
                        # 페이지 간 지연 (봇 차단 방지) - 가이드 권장: 2-3초
                        await asyncio.sleep(2.0)
                    
                else:
                    print(f"  [{ds_de}] 수집 실패 또는 데이터 없음")
                    
            except Exception as e:
                print(f"  [{ds_de}] 오류 발생: {e}")
            
            # 다음 날짜로 이동
            current_date += timedelta(days=1)
            
            # 날짜 간 지연 (봇 차단 방지) - 가이드 권장: 2-3초
            if current_date <= end_date:
                delay = 2.5
                print(f"  다음 날짜 조회 전 {delay}초 대기...")
                await asyncio.sleep(delay)
    
    return all_news_data


async def main():
    """메인 실행 함수"""
    keyword = "한국전력"
    start_date = "20251129"
    end_date = "20251130"
    
    print(f"=" * 60)
    print(f"네이버 뉴스 수집 시작 (crawl4ai 버전)")
    print(f"검색어: {keyword}")
    print(f"기간: {start_date} ~ {end_date}")
    print(f"수집 방식: crawl4ai + 날짜별 개별 조회 (봇 차단 방지)")
    print(f"=" * 60)
    print()
    
    results = await get_naver_news_data_crawl4ai(keyword, start_date, end_date)
    
    # 데이터프레임 변환 및 CSV 저장
    df = pd.DataFrame(results)
    
    # 출력 디렉토리 설정 (도커 컨테이너 내부 경로)
    output_dir = "/app/ksubscribe_share/test/news_scarppings"
    os.makedirs(output_dir, exist_ok=True)
    
    # 출력 파일명 생성
    output_filename = f"한전_뉴스_crawl4ai_{start_date}_{end_date}.csv"
    output_path = os.path.join(output_dir, output_filename)
    
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    
    print()
    print(f"=" * 60)
    print(f"수집 완료: 총 {len(df)}건의 기사가 저장되었습니다.")
    print(f"저장 경로: {output_path}")
    print(f"=" * 60)
    
    # 날짜별 통계 출력
    if len(df) > 0:
        print()
        print("날짜별 수집 통계:")
        date_stats = df.groupby("수집일").size().sort_index()
        for date, count in date_stats.items():
            print(f"  {date}: {count}건")


if __name__ == "__main__":
    # 코랩 환경이 아닌 경우 nest_asyncio 불필요
    # 도커 환경에서는 일반 asyncio.run() 사용
    asyncio.run(main())

