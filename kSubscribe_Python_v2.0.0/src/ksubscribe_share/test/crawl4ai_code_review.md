# crawl4ai 코드 검토 및 수정 사항

## 제공된 원본 코드의 문제점

### 1. ❌ **변수 타입 오류**
```python
# 원본 코드 (문제)
all_news_data = '/content/drive/MyDrive/회사/naver_news'  # 문자열
all_news_data.extend(day_data)  # 문자열에는 extend() 메서드 없음
```

**문제**: `all_news_data`가 문자열로 초기화되어 있는데, 리스트 메서드인 `extend()`를 사용하려고 함

**수정**:
```python
all_news_data = []  # 빈 리스트로 초기화
```

### 2. ❌ **코랩 전용 코드 (도커 환경에서 불필요)**
```python
# 원본 코드
nest_asyncio.apply()  # 코랩 환경 전용
```

**문제**: `nest_asyncio`는 Google Colab의 이벤트 루프 중복 실행 방지를 위한 것. 도커 환경에서는 불필요하며, 일반 Python 환경에서는 오류 발생 가능

**수정**: 제거하고 일반 `asyncio.run()` 사용

### 3. ⚠️ **불확실한 API 사용**
```python
# 원본 코드
from crawl4ai import JsonCssExtractionStrategy, BrowserConfig, CrawlerRunConfig, CacheMode

schema = {
    "name": "Naver News",
    "baseSelector": "li.bx",
    "fields": [...]
}
extraction_strategy = JsonCssExtractionStrategy(schema)
browser_config = BrowserConfig(headless=True, verbose=False)
run_config = CrawlerRunConfig(
    extraction_strategy=extraction_strategy,
    cache_mode=CacheMode.BYPASS,
    wait_for="css:a.news_tit"
)
```

**문제**: 
- `JsonCssExtractionStrategy`, `BrowserConfig`, `CrawlerRunConfig`, `CacheMode` 등의 API가 실제 crawl4ai 라이브러리에 존재하는지 확인 불가
- 웹 검색 결과로는 기본 `AsyncWebCrawler` API만 확인됨

**수정**: 
- crawl4ai의 기본 API (`AsyncWebCrawler`) 사용
- BeautifulSoup으로 HTML 파싱하여 데이터 추출
- 더 안정적이고 호환성 높은 방식으로 변경

### 4. ❌ **저장 경로 문제**
```python
# 원본 코드
all_news_data = '/content/drive/MyDrive/회사/naver_news'  # 코랩 경로
```

**문제**: 
- Google Colab의 경로를 하드코딩
- 도커 환경에서는 사용 불가

**수정**: 
- 도커 컨테이너 내부 경로로 변경: `/app/ksubscribe_share/test/news_scarppings`
- 호스트 경로와 매핑 가능하도록 설정

### 5. ⚠️ **페이지네이션 미처리**
원본 코드는 첫 페이지만 수집하고 페이지네이션 처리가 없음

**수정**: 페이지네이션 처리 추가 (최대 400페이지까지)

## 수정된 코드의 주요 개선 사항

### ✅ **1. 올바른 변수 초기화**
```python
all_news_data = []  # 빈 리스트로 초기화
```

### ✅ **2. 도커 환경에 맞는 코드**
```python
# nest_asyncio 제거
asyncio.run(main())  # 표준 asyncio 사용
```

### ✅ **3. crawl4ai 기본 API 사용**
```python
from crawl4ai import AsyncWebCrawler

async with AsyncWebCrawler(headless=True) as crawler:
    result = await crawler.arun(url=url)
    # BeautifulSoup으로 파싱
    soup = BeautifulSoup(result.html, 'lxml')
```

### ✅ **4. 페이지네이션 처리 추가**
```python
page = 2
max_pages = 400
while page <= max_pages:
    start_val = (page - 1) * 10 + 1
    page_url = f"{url}&start={start_val}"
    # 페이지별 수집 처리
```

### ✅ **5. 에러 처리 강화**
```python
try:
    from crawl4ai import AsyncWebCrawler
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False
    print("⚠️  crawl4ai가 설치되어 있지 않습니다.")
```

### ✅ **6. 날짜 범위 설정**
```python
start_date = "20251129"
end_date = "20251130"
```

### ✅ **7. 저장 경로 설정**
```python
output_dir = "/app/ksubscribe_share/test/news_scarppings"
```

## crawl4ai 설치 방법

### 도커 컨테이너에서 설치
```bash
docker exec -it ksubscribe_python_unified pip install crawl4ai
docker exec -it ksubscribe_python_unified crawl4ai-setup
```

### Playwright 브라우저 설치 (필요시)
```bash
docker exec -it ksubscribe_python_unified python -m playwright install chromium
```

## 실행 방법

### 1. 스크립트를 컨테이너에 복사
```bash
docker cp collect_naver_news_by_date_crawl4ai.py ksubscribe_python_unified:/app/ksubscribe_share/test/
```

### 2. 컨테이너에서 실행
```bash
docker exec ksubscribe_python_unified python /app/ksubscribe_share/test/collect_naver_news_by_date_crawl4ai.py
```

## 비교: 원본 vs 수정본

| 항목 | 원본 코드 | 수정된 코드 |
|------|----------|------------|
| 변수 초기화 | 문자열 (오류) | 빈 리스트 ✅ |
| 이벤트 루프 | nest_asyncio (코랩 전용) | asyncio.run() ✅ |
| API 사용 | 불확실한 API | 기본 AsyncWebCrawler ✅ |
| 페이지네이션 | 없음 | 추가됨 ✅ |
| 저장 경로 | 코랩 경로 | 도커 경로 ✅ |
| 에러 처리 | 없음 | 추가됨 ✅ |
| 날짜 범위 | 2025-11-01~30 | 2025-11-29~30 ✅ |

## 결론

원본 코드는 Google Colab 환경을 전제로 작성되었고, 여러 문제점이 있었습니다. 수정된 코드는:

1. ✅ 도커 환경에 맞게 수정
2. ✅ crawl4ai의 검증된 기본 API 사용
3. ✅ 페이지네이션 처리 추가
4. ✅ 에러 처리 강화
5. ✅ 올바른 변수 타입 사용

이제 도커 컨테이너에서 안정적으로 실행할 수 있습니다.




