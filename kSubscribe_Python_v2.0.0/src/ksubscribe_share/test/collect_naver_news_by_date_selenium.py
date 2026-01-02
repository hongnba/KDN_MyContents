"""
네이버 뉴스 수집 (Selenium 버전)
JavaScript로 동적 로딩되는 콘텐츠를 수집하기 위한 Selenium 기반 버전
BeautifulSoup 버전으로 수집이 안 될 경우 사용
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import time
import random
from datetime import datetime, timedelta
import urllib.parse
import os

def scroll_and_collect_articles(driver, formatted_date, max_scrolls=50, scroll_pause=2):
    """
    무한 스크롤을 처리하여 모든 기사를 수집
    
    :param driver: Selenium WebDriver
    :param formatted_date: 날짜 (YYYY.MM.DD 형식)
    :param max_scrolls: 최대 스크롤 횟수
    :param scroll_pause: 스크롤 간 대기 시간 (초)
    :return: 수집된 기사 데이터 리스트
    """
    collected_articles = []
    seen_urls = set()  # 중복 제거용
    
    last_count = 0
    no_new_count = 0  # 새로운 기사가 없는 연속 횟수
    
    for scroll_iteration in range(max_scrolls):
        # 현재 페이지의 모든 기사 추출
        articles = []
        try:
            # 여러 선택자 시도
            articles = driver.find_elements(By.CSS_SELECTOR, "ul.list_news > li.bx")
            if not articles:
                articles = driver.find_elements(By.CSS_SELECTOR, "li.bx")
            if not articles:
                articles = driver.find_elements(By.CSS_SELECTOR, "div.news_wrap")
        except:
            pass
        
        current_count = 0
        for item in articles:
            try:
                # 제목과 링크 추출
                title_tag = None
                try:
                    title_tag = item.find_element(By.CSS_SELECTOR, "a.news_tit")
                except:
                    try:
                        title_tag = item.find_element(By.CSS_SELECTOR, "a._sp_each_title")
                    except:
                        pass
                
                if title_tag:
                    title = title_tag.text.strip()
                    link = title_tag.get_attribute('href')
                    
                    # 상대 경로를 절대 경로로 변환
                    if link and link.startswith('/'):
                        link = f"https://search.naver.com{link}"
                    
                    # 중복 제거
                    if link and link not in seen_urls:
                        seen_urls.add(link)
                        collected_articles.append({
                            "수집일": formatted_date,
                            "제목": title,
                            "URL": link
                        })
                        current_count += 1
            except NoSuchElementException:
                continue
        
        # 새로운 기사 수집 여부 확인
        if current_count > 0:
            no_new_count = 0
            print(f"  [{formatted_date}] 스크롤 {scroll_iteration + 1}: {current_count}건 추가 (총 {len(collected_articles)}건)")
        else:
            no_new_count += 1
            if no_new_count >= 3:  # 3번 연속 새로운 기사가 없으면 종료
                print(f"  [{formatted_date}] 더 이상 새로운 기사가 없습니다. (총 {len(collected_articles)}건 수집)")
                break
        
        # 페이지 하단으로 스크롤
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause)
        
        # 추가 로딩 대기 (동적 콘텐츠 로딩 시간)
        time.sleep(1)
    
    return collected_articles


def get_naver_news_data_selenium(keyword, start_date_str, end_date_str, headless=True):
    """
    Selenium을 사용하여 네이버 뉴스 기사를 날짜별로 개별 조회하여 수집함.
    무한 스크롤 방식으로 모든 기사를 수집.
    
    :param keyword: 검색어 (예: '한국전력')
    :param start_date_str: 시작일 (YYYYMMDD 형식, 예: '20251129')
    :param end_date_str: 종료일 (YYYYMMDD 형식, 예: '20251130')
    :param headless: 헤드리스 모드 사용 여부 (기본값: True)
    :return: 수집된 기사 데이터 리스트
    """
    # 1. 날짜 범위 생성
    start_date = datetime.strptime(start_date_str, "%Y%m%d")
    end_date = datetime.strptime(end_date_str, "%Y%m%d")
    
    # 각 날짜를 개별적으로 조회하기 위한 날짜 리스트 생성
    date_list = []
    current_date = start_date
    while current_date <= end_date:
        date_list.append(current_date.strftime("%Y%m%d"))
        current_date += timedelta(days=1)
    
    # 결과 저장 리스트
    collected_data = []
    
    # 2. Selenium WebDriver 설정
    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(5)
        
        # 3. 각 날짜를 개별적으로 조회하여 수집
        for target_date in date_list:
            # 네이버 URL 파라미터용 형식으로 변환 (YYYY.MM.DD) 
            formatted_date = f"{target_date[:4]}.{target_date[4:6]}.{target_date[6:]}"
            print(f"[{formatted_date}] 수집 시작... (Selenium, 무한 스크롤 방식)")
            
            # 제공된 URL 형식 사용
            query_encoded = urllib.parse.quote(keyword)
            search_url = (
                f"https://search.naver.com/search.naver?"
                f"ssc=tab.news.all&"
                f"query={query_encoded}&"
                f"sm=tab_opt&"
                f"sort=0&"
                f"photo=0&"
                f"field=0&"
                f"pd=3&"
                f"ds={formatted_date}&"
                f"de={formatted_date}&"
                f"nso=so%3Ar%2Cp%3Afrom{target_date}to{target_date}"
            )
            
            try:
                driver.get(search_url)
                # 초기 페이지 로딩 대기
                time.sleep(random.uniform(2.0, 3.0))
                
                # 무한 스크롤 처리하여 모든 기사 수집
                day_articles = scroll_and_collect_articles(driver, formatted_date, max_scrolls=50, scroll_pause=2)
                collected_data.extend(day_articles)
                
                print(f"  [{formatted_date}] 수집 완료: 총 {len(day_articles)}건")
                
            except Exception as e:
                print(f"  [{formatted_date}] 오류 발생: {e}")
            
            # 날짜별 수집 완료 후 약간의 지연 (봇 차단 방지)
            if target_date != date_list[-1]:  # 마지막 날짜가 아니면
                delay = random.uniform(3.0, 5.0)
                print(f"  [{formatted_date}] 다음 날짜 조회 전 {delay:.1f}초 대기...")
                time.sleep(delay)
        
    except Exception as e:
        print(f"❌ Selenium WebDriver 오류: {e}")
        print("   ChromeDriver가 설치되어 있는지 확인하세요.")
        print("   또는 BeautifulSoup 버전(collect_naver_news_by_date.py)을 사용해보세요.")
    finally:
        if driver:
            driver.quit()
                
    return collected_data

# 실행 및 데이터 저장
if __name__ == "__main__":
    keyword = "한국전력"
    start_date = "20251101"
    end_date = "20251130"
    
    print(f"=" * 60)
    print(f"네이버 뉴스 수집 시작 (Selenium 버전)")
    print(f"검색어: {keyword}")
    print(f"기간: {start_date} ~ {end_date}")
    print(f"수집 방식: Selenium + 날짜별 개별 조회 (봇 차단 방지)")
    print(f"=" * 60)
    print()
    
    # 헤드리스 모드로 실행 (브라우저 창을 띄우지 않음)
    # headless=False로 변경하면 브라우저 창이 보임 (디버깅용)
    results = get_naver_news_data_selenium(keyword, start_date, end_date, headless=True)
    
    # 데이터프레임 변환 및 CSV 저장 (한글 깨짐 방지를 위해 utf-8-sig 사용) 
    df = pd.DataFrame(results)
    
    # 출력 디렉토리 설정 (도커 컨테이너 내부 경로)
    output_dir = "/app/ksubscribe_share/test/news_scarppings"
    os.makedirs(output_dir, exist_ok=True)
    
    # 출력 파일명 생성
    output_filename = f"한전_뉴스_selenium_{start_date}_{end_date}.csv"
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

