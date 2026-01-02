import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from datetime import datetime, timedelta
import urllib.parse
import os

def get_naver_news_data(keyword, start_date_str, end_date_str):
    """
    지정된 기간 동안 네이버 뉴스 기사의 제목과 URL을 날짜별로 개별 조회하여 수집함.
    각 날짜마다 개별적으로 조회하여 봇 차단을 방지함.
    
    :param keyword: 검색어 (예: '한국전력')
    :param start_date_str: 시작일 (YYYYMMDD 형식, 예: '20251101')
    :param end_date_str: 종료일 (YYYYMMDD 형식, 예: '20251130')
    :return: 수집된 기사 데이터 리스트
    """
    # 1. 날짜 범위 생성
    start_date = datetime.strptime(start_date_str, "%Y%m%d")
    end_date = datetime.strptime(end_date_str, "%Y%m%d")
    delta = end_date - start_date
    
    # 각 날짜를 개별적으로 조회하기 위한 날짜 리스트 생성
    date_list = []
    current_date = start_date
    while current_date <= end_date:
        date_list.append(current_date.strftime("%Y%m%d"))
        current_date += timedelta(days=1)
    
    # 결과 저장 리스트
    collected_data = []
    
    # 2025년 보안 대응을 위한 표준 브라우저 헤더 설정 
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.naver.com/"
    }
    
    session = requests.Session()
    session.headers.update(headers)
    
    # 2. 각 날짜를 개별적으로 조회하여 수집
    for target_date in date_list:
        # 네이버 URL 파라미터용 형식으로 변환 (YYYY.MM.DD) 
        formatted_date = f"{target_date[:4]}.{target_date[4:6]}.{target_date[6:]}"
        print(f"[{formatted_date}] 수집 시작... (날짜별 개별 조회)")
        
        page = 1
        date_article_count = 0
        
        while True:
            # start 파라미터 계산: 1, 11, 21,... 
            start_val = (page - 1) * 10 + 1
            
            # 검색 URL 생성 - 각 날짜를 개별적으로 조회 (ds와 de를 같은 날짜로 설정)
            query_encoded = urllib.parse.quote(keyword)
            search_url = (
                f"https://search.naver.com/search.naver?where=news&query={query_encoded}"
                f"&pd=3&ds={formatted_date}&de={formatted_date}"
                f"&nso=so:dd,p:from{target_date}to{target_date},a:all"
                f"&start={start_val}"
            )
            
            try:
                response = session.get(search_url, timeout=10)
                # 인코딩 자동 감지 및 설정 
                response.encoding = response.apparent_encoding or 'utf-8'
                
                if response.status_code != 200:
                    print(f"  Error: HTTP {response.status_code}")
                    break
                
                soup = BeautifulSoup(response.text, 'lxml')
                
                # 기사 아이템 추출 (여러 선택자 시도)
                articles = soup.select("ul.list_news > li.bx")
                
                # 선택자 1이 실패하면 다른 선택자 시도
                if not articles:
                    articles = soup.select("div.news_wrap > div.news_area")
                if not articles:
                    articles = soup.select("li.bx")
                
                # 결과가 없으면 해당 날짜 수집 종료
                if not articles:
                    print(f"  [{formatted_date}] 더 이상 기사가 없습니다. (총 {date_article_count}건 수집)")
                    # 디버깅: HTML 일부 출력 (선택사항)
                    if page == 1:
                        print(f"  [디버그] HTML 샘플 (처음 500자): {response.text[:500]}")
                    break
                
                page_article_count = 0
                for item in articles:
                    title_tag = item.select_one("a.news_tit")
                    if title_tag:
                        title = title_tag.get_text(strip=True)
                        link = title_tag.get('href')
                        
                        collected_data.append({
                            "수집일": formatted_date,
                            "제목": title,
                            "URL": link
                        })
                        page_article_count += 1
                        date_article_count += 1
                
                print(f"  [{formatted_date}] 페이지 {page}: {page_article_count}건 수집 (누적: {date_article_count}건)")
                
                # 페이지 안전 종료 조건: 최대 페이지 수 제한 (보통 400페이지가 한계) 
                if page >= 400:
                    print(f"  [{formatted_date}] 최대 페이지 수(400)에 도달했습니다.")
                    break
                
                # 3. 비정상적 차단 방지를 위한 지연 시간 삽입 
                time.sleep(random.uniform(1.0, 2.0))
                page += 1
                
            except Exception as e:
                print(f"  [{formatted_date}] Error occurred: {e}")
                break
        
        # 날짜별 수집 완료 후 약간의 지연 (봇 차단 방지)
        if target_date != date_list[-1]:  # 마지막 날짜가 아니면
            delay = random.uniform(2.0, 3.0)
            print(f"  [{formatted_date}] 수집 완료. 다음 날짜 조회 전 {delay:.1f}초 대기...")
            time.sleep(delay)
                
    return collected_data

# 실행 및 데이터 저장
if __name__ == "__main__":
    keyword = "한국전력"
    start_date = "20251129"
    end_date = "20251130"
    
    print(f"=" * 60)
    print(f"네이버 뉴스 수집 시작")
    print(f"검색어: {keyword}")
    print(f"기간: {start_date} ~ {end_date}")
    print(f"수집 방식: 날짜별 개별 조회 (봇 차단 방지)")
    print(f"=" * 60)
    print()
    
    results = get_naver_news_data(keyword, start_date, end_date)
    
    # 데이터프레임 변환 및 CSV 저장 (한글 깨짐 방지를 위해 utf-8-sig 사용) 
    df = pd.DataFrame(results)
    
    # 출력 디렉토리 설정 (도커 컨테이너 내부 경로)
    output_dir = "/app/ksubscribe_share/test/news_scarppings"
    os.makedirs(output_dir, exist_ok=True)
    
    # 출력 파일명 생성
    output_filename = f"한전_뉴스_{start_date}_{end_date}.csv"
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

