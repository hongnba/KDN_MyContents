# 네이버 뉴스 Selenium 수집 실현 가능성 분석

> 작성일: 2025-12-24  
> 분석 대상: Selenium을 사용한 네이버 뉴스 날짜 범위 수집의 실현 가능성

---

## 📋 목차

1. [요구사항 정리](#1-요구사항-정리)
2. [실현 가능성 분석](#2-실현-가능성-분석)
3. [주요 고려사항](#3-주요-고려사항)
4. [구현 전략 제안](#4-구현-전략-제안)
5. [위험 요소 및 대응 방안](#5-위험-요소-및-대응-방안)
6. [대안 검토](#6-대안-검토)

---

## 1. 요구사항 정리

### 1.1 목표
- **수집 대상**: 네이버 뉴스에서 한국전력 관련 기사
- **수집 방식**: Selenium (웹 브라우저 자동화)
- **수집 기간**: 사용자가 설정한 날짜 범위 (예: 1달)
- **제약사항**: 
  - 1달 기간을 한 번에 수집하면 봇 차단 위험
  - 하루 단위로 끊어서 수집 필요
  - 각 수집 후 10-20초 대기 (봇이 아닌 것처럼)

### 1.2 현재 상황
- **현재 방식**: 네이버 뉴스 검색 API (Open API)
- **문제점**: API는 과거 기사 수집이 어려움 (최신 기사 위주)
- **해결책**: Selenium으로 네이버 뉴스 검색 페이지 직접 크롤링

---

## 2. 실현 가능성 분석

### 2.1 ✅ 실현 가능한 부분

#### A. 네이버 뉴스 검색 페이지 접근
- **가능성**: ✅ **가능**
- **이유**: 
  - 네이버 뉴스 검색 페이지는 공개적으로 접근 가능
  - URL: `https://search.naver.com/search.naver?where=news&query=한국전력`
  - Selenium으로 접근 가능

#### B. 검색어 입력
- **가능성**: ✅ **가능**
- **이유**:
  - 검색어 입력 필드에 키워드 입력 가능
  - 검색 버튼 클릭 가능

#### C. 날짜 필터링
- **가능성**: ⚠️ **확인 필요**
- **이유**:
  - 네이버 뉴스 검색 페이지에 날짜 필터 기능이 있는지 확인 필요
  - 옵션 메뉴에서 날짜 범위 선택 가능 여부 확인 필요
  - **실제 확인 필요**: 네이버 뉴스 검색 페이지에서 날짜 필터 기능 존재 여부

#### D. 하루 단위 수집
- **가능성**: ✅ **가능**
- **이유**:
  - 날짜 범위를 하루씩 나누어 반복 수집 가능
  - 예: 2025-11-01 ~ 2025-11-30 → 각 날짜별로 개별 수집

#### E. 요청 간 대기
- **가능성**: ✅ **가능**
- **이유**:
  - Python의 `time.sleep()` 함수로 대기 시간 설정 가능
  - 10-20초 랜덤 대기 시간 설정 가능

---

### 2.2 ⚠️ 확인이 필요한 부분

#### A. 네이버 뉴스 검색 페이지의 날짜 필터 기능
**확인 필요 사항**:
1. 네이버 뉴스 검색 페이지에 날짜 범위 선택 기능이 있는가?
2. 날짜 필터는 어떤 형태인가? (드롭다운, 캘린더, 입력 필드 등)
3. 날짜 필터를 Selenium으로 조작할 수 있는가?

**확인 방법**:
- 실제 네이버 뉴스 검색 페이지 접속하여 확인
- 개발자 도구로 HTML 구조 분석
- 날짜 필터 요소의 ID, 클래스명, XPath 확인

#### B. 페이지네이션 처리
**확인 필요 사항**:
1. 네이버 뉴스 검색 결과의 페이지네이션 방식은?
2. "다음" 버튼이 있는가? 페이지 번호가 있는가?
3. 한 페이지에 몇 개의 기사가 표시되는가?

#### C. 봇 차단 메커니즘
**확인 필요 사항**:
1. 네이버는 어떤 방식으로 봇을 감지하는가?
2. 요청 빈도 제한이 있는가?
3. IP 차단 기준은 무엇인가?
4. User-Agent 체크를 하는가?

---

## 3. 주요 고려사항

### 3.1 날짜 필터 기능 확인

#### 시나리오 A: 날짜 필터 기능이 있는 경우
**구현 방법**:
```python
# 1. 검색어 입력
search_input = driver.find_element(By.ID, "query")
search_input.send_keys("한국전력")
search_button.click()

# 2. 옵션 메뉴 열기
option_button = driver.find_element(By.CLASS_NAME, "option_btn")
option_button.click()

# 3. 날짜 필터 선택
date_filter = driver.find_element(By.ID, "date_filter")
date_filter.click()

# 4. 시작 날짜 입력
start_date_input = driver.find_element(By.ID, "start_date")
start_date_input.clear()
start_date_input.send_keys("2025.11.01")

# 5. 종료 날짜 입력
end_date_input = driver.find_element(By.ID, "end_date")
end_date_input.clear()
end_date_input.send_keys("2025.11.01")  # 하루 단위

# 6. 적용 버튼 클릭
apply_button.click()
```

**장점**:
- ✅ 정확한 날짜 범위로 필터링 가능
- ✅ 불필요한 기사 수집 방지

**단점**:
- ⚠️ 날짜 필터 UI가 복잡할 수 있음
- ⚠️ 날짜 필터 요소를 찾기 어려울 수 있음

#### 시나리오 B: 날짜 필터 기능이 없는 경우
**구현 방법**:
```python
# 1. 검색어에 날짜 포함 (예: "한국전력 2025-11-01")
search_query = f"한국전력 {date.strftime('%Y-%m-%d')}"
search_input.send_keys(search_query)
search_button.click()

# 2. 검색 결과에서 날짜 확인하여 필터링
for article in articles:
    article_date = extract_date(article)
    if article_date == target_date:
        # 수집
    else:
        # 스킵
```

**장점**:
- ✅ 날짜 필터 UI가 없어도 구현 가능

**단점**:
- ⚠️ 검색 결과에 다른 날짜의 기사도 포함될 수 있음
- ⚠️ 수동으로 날짜 필터링 필요
- ⚠️ 정확도가 낮을 수 있음

---

### 3.2 하루 단위 수집 전략

#### 전략 1: 날짜별 개별 검색
```python
# 날짜 범위를 하루씩 나누기
start_date = datetime(2025, 11, 1)
end_date = datetime(2025, 11, 30)

current_date = start_date
while current_date <= end_date:
    # 하루 단위로 검색
    search_for_date(current_date)
    
    # 10-20초 랜덤 대기
    wait_time = random.randint(10, 20)
    time.sleep(wait_time)
    
    current_date += timedelta(days=1)
```

**장점**:
- ✅ 봇 차단 위험 감소
- ✅ 각 날짜별로 독립적으로 수집 가능
- ✅ 실패 시 특정 날짜만 재시도 가능

**단점**:
- ⚠️ 수집 시간이 오래 걸림 (30일 × 15초 = 7.5분 이상)
- ⚠️ 네트워크 오류 시 재시도 로직 필요

#### 전략 2: 배치 단위 수집 (3-5일씩)
```python
# 3-5일씩 묶어서 수집
batch_size = 3
current_date = start_date

while current_date <= end_date:
    batch_end = min(current_date + timedelta(days=batch_size-1), end_date)
    
    # 배치 단위로 검색
    search_for_date_range(current_date, batch_end)
    
    # 20-30초 대기
    wait_time = random.randint(20, 30)
    time.sleep(wait_time)
    
    current_date += timedelta(days=batch_size)
```

**장점**:
- ✅ 하루 단위보다 빠름
- ✅ 봇 차단 위험은 여전히 낮음

**단점**:
- ⚠️ 하루 단위보다는 위험도가 높음
- ⚠️ 배치 내에서 날짜 필터링 필요

---

### 3.3 봇 차단 우회 전략

#### A. User-Agent 설정
```python
chrome_options = Options()
chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
```

**효과**: ✅ 일반 브라우저처럼 보이게 함

#### B. 요청 간 랜덤 대기
```python
import random
import time

# 10-20초 랜덤 대기
wait_time = random.randint(10, 20)
time.sleep(wait_time)
```

**효과**: ✅ 봇처럼 보이지 않게 함

#### C. 페이지 로딩 대기
```python
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 요소가 로드될 때까지 대기
WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CLASS_NAME, "news_wrap"))
)
```

**효과**: ✅ 페이지가 완전히 로드된 후 처리

#### D. 마우스 이동 시뮬레이션 (선택사항)
```python
from selenium.webdriver.common.action_chains import ActionChains

# 마우스 이동 시뮬레이션
actions = ActionChains(driver)
actions.move_to_element(element).perform()
```

**효과**: ⚠️ 효과가 제한적일 수 있음

---

## 4. 구현 전략 제안

### 4.1 추천 전략: 하루 단위 + 랜덤 대기

#### 구현 흐름
```
1. 날짜 범위를 하루씩 나누기
   ↓
2. 각 날짜별로:
   a. 네이버 뉴스 검색 페이지 접속
   b. 검색어 입력 ("한국전력")
   c. 날짜 필터 설정 (해당 날짜)
   d. 검색 실행
   e. 검색 결과에서 기사 목록 추출
   f. 각 기사의 제목, URL, 발행일 추출
   g. 날짜 확인 (정확히 해당 날짜인지)
   h. contents_queue에 저장
   ↓
3. 10-20초 랜덤 대기
   ↓
4. 다음 날짜로 이동
```

#### 코드 구조 (의사코드)
```python
def get_naver_news_by_selenium_date_range(
    driver, 
    contentsOrg, 
    category, 
    start_date, 
    end_date,
    logger
):
    """
    Selenium을 사용하여 네이버 뉴스에서 날짜 범위별로 기사 수집
    """
    current_date = start_date
    
    while current_date <= end_date:
        logger.info(f"날짜별 수집 시작: {current_date.strftime('%Y-%m-%d')}")
        
        try:
            # 1. 네이버 뉴스 검색 페이지 접속
            base_url = "https://search.naver.com/search.naver?where=news"
            driver.get(base_url)
            time.sleep(2)  # 페이지 로딩 대기
            
            # 2. 검색어 입력
            search_input = driver.find_element(By.ID, "query")  # 실제 ID 확인 필요
            search_input.clear()
            search_input.send_keys("한국전력")
            search_button = driver.find_element(By.CLASS_NAME, "search_btn")  # 실제 클래스 확인 필요
            search_button.click()
            time.sleep(2)
            
            # 3. 날짜 필터 설정 (날짜 필터 기능이 있는 경우)
            if has_date_filter:
                set_date_filter(driver, current_date, current_date)
            
            # 4. 검색 결과에서 기사 목록 추출
            articles = extract_articles(driver)
            
            # 5. 각 기사 처리
            for article in articles:
                article_date = extract_date(article)
                
                # 정확히 해당 날짜인지 확인
                if article_date.date() == current_date.date():
                    # ContentsCollectDetail 생성 및 저장
                    collectDetail = create_collect_detail(article)
                    save_to_queue(collectDetail)
            
            # 6. 페이지네이션 처리 (필요한 경우)
            while has_next_page(driver):
                next_page_button.click()
                time.sleep(2)
                articles = extract_articles(driver)
                # ... 동일한 처리
            
        except Exception as e:
            logger.error(f"날짜별 수집 실패: {current_date.strftime('%Y-%m-%d')} - {e}")
        
        # 7. 랜덤 대기 (10-20초)
        wait_time = random.randint(10, 20)
        logger.info(f"대기 중: {wait_time}초")
        time.sleep(wait_time)
        
        # 8. 다음 날짜로 이동
        current_date += timedelta(days=1)
```

---

### 4.2 날짜 필터 설정 함수 (가상)

```python
def set_date_filter(driver, start_date, end_date):
    """
    네이버 뉴스 검색 페이지에서 날짜 필터 설정
    (실제 HTML 구조 확인 후 구현 필요)
    """
    try:
        # 옵션 메뉴 열기
        option_button = driver.find_element(By.CLASS_NAME, "option_btn")
        option_button.click()
        time.sleep(1)
        
        # 날짜 필터 선택
        date_filter = driver.find_element(By.ID, "date_filter")
        date_filter.click()
        time.sleep(1)
        
        # 시작 날짜 입력
        start_input = driver.find_element(By.ID, "start_date")
        start_input.clear()
        start_input.send_keys(start_date.strftime("%Y.%m.%d"))
        
        # 종료 날짜 입력
        end_input = driver.find_element(By.ID, "end_date")
        end_input.clear()
        end_input.send_keys(end_date.strftime("%Y.%m.%d"))
        
        # 적용 버튼 클릭
        apply_button = driver.find_element(By.CLASS_NAME, "apply_btn")
        apply_button.click()
        time.sleep(2)  # 필터 적용 대기
        
    except Exception as e:
        logger.warning(f"날짜 필터 설정 실패: {e}")
        # 날짜 필터가 없으면 검색 결과에서 수동 필터링
```

---

### 4.3 기사 추출 함수 (가상)

```python
def extract_articles(driver):
    """
    검색 결과 페이지에서 기사 목록 추출
    (실제 HTML 구조 확인 후 구현 필요)
    """
    articles = []
    
    try:
        # 기사 목록 컨테이너 찾기
        news_list = driver.find_element(By.CLASS_NAME, "news_wrap")  # 실제 클래스 확인 필요
        
        # 각 기사 항목 추출
        news_items = news_list.find_elements(By.CLASS_NAME, "news_tit")  # 실제 클래스 확인 필요
        
        for item in news_items:
            # 제목 추출
            title = item.find_element(By.TAG_NAME, "a").text
            
            # URL 추출
            url = item.find_element(By.TAG_NAME, "a").get_attribute("href")
            
            # 날짜 추출
            date_element = item.find_element(By.CLASS_NAME, "info_group")  # 실제 클래스 확인 필요
            date_text = date_element.text  # "2025.11.01."
            date = parse_date(date_text)
            
            articles.append({
                "title": title,
                "url": url,
                "date": date
            })
    
    except Exception as e:
        logger.error(f"기사 추출 실패: {e}")
    
    return articles
```

---

## 5. 위험 요소 및 대응 방안

### 5.1 봇 차단 위험

#### 위험도: ⚠️ **높음**

**이유**:
- 네이버는 봇 차단에 적극적
- Selenium 사용은 봇으로 감지되기 쉬움
- 과도한 요청 시 IP 차단 가능

#### 대응 방안

1. **요청 빈도 제한**
   - 하루 단위로 수집하여 요청 빈도 감소
   - 각 요청 후 10-20초 랜덤 대기
   - 30일 수집 시 최소 5분 이상 소요 (안전)

2. **User-Agent 설정**
   - 실제 브라우저 User-Agent 사용
   - 최신 Chrome User-Agent 사용

3. **페이지 로딩 대기**
   - `WebDriverWait` 사용하여 자연스러운 로딩 시뮬레이션
   - 즉시 클릭하지 않고 요소가 로드될 때까지 대기

4. **에러 처리**
   - 봇 차단 감지 시 즉시 중단
   - 재시도 로직 구현 (최대 3회)
   - 실패 시 해당 날짜 건너뛰고 다음 날짜로

---

### 5.2 HTML 구조 변경 위험

#### 위험도: ⚠️ **중간**

**이유**:
- 네이버는 웹사이트 구조를 자주 변경할 수 있음
- XPath, 클래스명이 변경되면 크롤링 실패

#### 대응 방안

1. **유연한 요소 찾기**
   - 여러 방법으로 요소 찾기 시도
   - XPath, 클래스명, ID 등 다양한 방법 사용

2. **에러 처리 및 로깅**
   - 요소를 찾지 못할 경우 상세 로그 기록
   - 실패 시 스크린샷 저장 (디버깅용)

3. **정기적인 모니터링**
   - 수집 실패 시 즉시 알림
   - HTML 구조 변경 감지

---

### 5.3 성능 문제

#### 위험도: ⚠️ **낮음**

**이유**:
- 하루 단위 수집은 시간이 오래 걸림
- 30일 수집 시 최소 5-10분 소요

#### 대응 방안

1. **병렬 처리 고려** (선택사항)
   - 여러 날짜를 동시에 수집 (위험도 증가)
   - 권장하지 않음 (봇 차단 위험)

2. **진행 상황 로깅**
   - 각 날짜별 수집 진행 상황 로그
   - 예상 완료 시간 표시

---

## 6. 대안 검토

### 6.1 현재 방식 (네이버 API) 유지

**장점**:
- ✅ 안정적 (API는 공식 지원)
- ✅ 빠름 (API 호출)
- ✅ 봇 차단 위험 낮음

**단점**:
- ❌ 과거 기사 수집 어려움
- ❌ 날짜 범위 필터링 불가능

**결론**: 과거 기사 수집이 목적이면 Selenium이 필요

---

### 6.2 하이브리드 방식

**전략**:
- 최근 기사 (예: 최근 7일): 네이버 API 사용
- 과거 기사 (예: 7일 이전): Selenium 사용

**장점**:
- ✅ 최근 기사는 빠르게 수집
- ✅ 과거 기사도 수집 가능

**단점**:
- ⚠️ 두 가지 방식을 모두 유지해야 함
- ⚠️ 복잡도 증가

---

## 7. 실현 가능성 종합 평가

### 7.1 기술적 실현 가능성: ⚠️ **중간**

**이유**:
- ✅ Selenium으로 네이버 뉴스 접근 가능
- ⚠️ 날짜 필터 기능 존재 여부 확인 필요
- ⚠️ HTML 구조 분석 필요
- ✅ 하루 단위 수집 및 대기 시간 설정 가능

### 7.2 봇 차단 위험: ⚠️ **높음**

**이유**:
- ⚠️ 네이버는 봇 차단에 적극적
- ⚠️ Selenium 사용은 봇으로 감지되기 쉬움
- ⚠️ 과도한 요청 시 IP 차단 가능

**완화 방안**:
- ✅ 하루 단위 수집으로 요청 빈도 감소
- ✅ 10-20초 랜덤 대기로 자연스러운 패턴 시뮬레이션
- ✅ User-Agent 설정
- ✅ 페이지 로딩 대기

### 7.3 유지보수성: ⚠️ **중간**

**이유**:
- ⚠️ HTML 구조 변경 시 코드 수정 필요
- ⚠️ 네이버 정책 변경 시 대응 필요
- ✅ 하루 단위 수집으로 실패 시 특정 날짜만 재시도 가능

---

## 8. 최종 의견

### 8.1 실현 가능성: ✅ **가능하지만 주의 필요**

**조건**:
1. ✅ 네이버 뉴스 검색 페이지의 날짜 필터 기능 확인 필요
2. ✅ HTML 구조 분석 필요
3. ✅ 봇 차단 우회 전략 필수
4. ✅ 하루 단위 수집 및 랜덤 대기 시간 설정

### 8.2 추천 접근 방법

#### Phase 1: 탐색 및 분석
1. 네이버 뉴스 검색 페이지 실제 접속
2. 날짜 필터 기능 존재 여부 확인
3. HTML 구조 분석 (개발자 도구 사용)
4. 요소 선택자 (ID, 클래스명, XPath) 확인

#### Phase 2: 프로토타입 개발
1. 단일 날짜 수집 테스트
2. 날짜 필터 설정 테스트
3. 기사 추출 테스트
4. 봇 차단 여부 확인

#### Phase 3: 전체 구현
1. 날짜 범위 수집 로직 구현
2. 하루 단위 반복 로직 구현
3. 랜덤 대기 시간 설정
4. 에러 처리 및 재시도 로직

#### Phase 4: 테스트 및 모니터링
1. 소규모 테스트 (3-5일)
2. 봇 차단 여부 확인
3. 수집 정확도 확인
4. 대규모 테스트 (1달)

### 8.3 주의사항

1. **봇 차단 위험**
   - 처음에는 소규모 테스트 (1-3일)
   - 봇 차단 감지 시 즉시 중단
   - IP 차단 시 복구 어려움

2. **HTML 구조 변경**
   - 정기적인 모니터링 필요
   - 수집 실패 시 즉시 확인

3. **성능**
   - 30일 수집 시 최소 5-10분 소요
   - 대기 시간을 줄이면 봇 차단 위험 증가

4. **법적/윤리적 고려**
   - 네이버 이용약관 확인
   - robots.txt 확인
   - 과도한 요청 자제

---

## 9. 결론

### 9.1 실현 가능성: ✅ **가능**

**전제 조건**:
- 네이버 뉴스 검색 페이지에 날짜 필터 기능이 있어야 함
- HTML 구조를 정확히 파악해야 함
- 봇 차단 우회 전략이 필수

### 9.2 추천 사항

1. **먼저 확인할 것**:
   - 네이버 뉴스 검색 페이지의 날짜 필터 기능 존재 여부
   - HTML 구조 분석

2. **구현 전략**:
   - 하루 단위 수집
   - 10-20초 랜덤 대기
   - User-Agent 설정
   - 페이지 로딩 대기

3. **테스트 순서**:
   - 단일 날짜 테스트
   - 소규모 테스트 (3-5일)
   - 대규모 테스트 (1달)

4. **리스크 관리**:
   - 봇 차단 감지 시 즉시 중단
   - 실패한 날짜는 별도로 기록
   - 재시도 로직 구현

### 9.3 최종 권고사항

**✅ 진행 가능하지만, 다음 단계를 먼저 수행하는 것을 권장합니다:**

1. **네이버 뉴스 검색 페이지 실제 접속 및 분석**
   - 날짜 필터 기능 확인
   - HTML 구조 분석
   - 요소 선택자 확인

2. **프로토타입 개발**
   - 단일 날짜 수집 테스트
   - 봇 차단 여부 확인

3. **전체 구현**
   - 위의 결과를 바탕으로 전체 로직 구현

**⚠️ 주의**: 봇 차단 위험이 높으므로, 처음에는 소규모 테스트를 통해 안전성을 확인한 후 확장하는 것을 권장합니다.


