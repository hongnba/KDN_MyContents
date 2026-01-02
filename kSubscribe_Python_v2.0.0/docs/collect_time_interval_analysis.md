# 수집 시간 간격 분석 문서

> 작성일: 2025-01-XX  
> 분석 목적: 기사 및 나라장터 공고 수집 시 6시간 간격 설정 여부 확인

---

## 📋 분석 결과 요약

**결론: 현재 코드에는 6시간 간격으로 데이터를 수집하는 설정이 없습니다.**

모든 수집 함수는 `lastSucYMD`(마지막 성공 수집일)부터 오늘까지의 **모든 날짜**를 수집하도록 되어 있습니다.

---

## 1. 나라장터 공고 수집 (`get_g2b_nara`)

**파일**: `docker_collect/openapi_collector.py`  
**함수**: `get_g2b_nara()`

### 현재 로직

```python
# Line 33-43
last_suc = category.lastSucYMD
if isinstance(last_suc_str, str): 
    last_suc = datetime.strptime(category.lastSucYMD, "%Y%m%d")

# last_suc부터 오늘까지의 날짜 리스트 생성
next_day = last_suc  # + timedelta(days=1) 주석 처리됨
today = datetime.now(pytz.timezone('Asia/Seoul'))
date_list = [(next_day + timedelta(days=x)).strftime("%Y%m%d") 
             for x in range((today - next_day).days + 1)]
```

### 분석 결과

- ✅ `lastSucYMD`부터 오늘까지의 **모든 날짜**를 수집
- ❌ **6시간 간격 설정 없음**
- ❌ 시간 단위 필터링 없음 (날짜 단위만)

### 수집 범위 예시

- `lastSucYMD = 2025-01-20`, `today = 2025-01-23`인 경우:
  - 수집 날짜: `2025-01-20`, `2025-01-21`, `2025-01-22`, `2025-01-23` (4일치)

---

## 2. 네이버 뉴스 수집 (`get_naver_news`)

**파일**: `docker_collect/openapi_collector.py`  
**함수**: `get_naver_news()`

### 현재 로직

```python
# Line 154-173
last_suc = category.lastSucYMD
next_day = last_suc + timedelta(days=1)  # 다음 날부터

today = datetime.utcnow().replace(tzinfo=pytz.utc)
lastSucYMD = today 

date_list = [(next_day + timedelta(days=x)).strftime("%Y%m%d") 
             for x in range((today - next_day).days + 1)]

# Line 231-239: 날짜 비교
date = parse(date).replace(tzinfo=pytz.timezone('Asia/Seoul'))
last_suc_ymd = datetime(last_suc.year, last_suc.month, last_suc.day)
pubDt_ymd = datetime(date.year, date.month, date.day)

# 하루에 여러번 돌리므로 비교연산자 (<=)사용
if last_suc_ymd <= pubDt_ymd:
    # 수집 처리
```

### 분석 결과

- ✅ `lastSucYMD + 1일`부터 오늘까지의 **모든 날짜**를 수집
- ❌ **6시간 간격 설정 없음**
- ⚠️ 주석에 "하루에 여러번 돌리므로 비교연산자 (<=)사용"이라고 되어 있으나, 실제로는 날짜 단위 비교만 수행
- ❌ 시간 단위 필터링 없음

### 수집 범위 예시

- `lastSucYMD = 2025-01-20`, `today = 2025-01-23`인 경우:
  - 수집 날짜: `2025-01-21`, `2025-01-22`, `2025-01-23` (3일치)

---

## 3. RSS 수집 (`get_contents_by_rss`)

**파일**: `docker_collect/rss_collector.py`  
**함수**: `get_contents_by_rss()`

### 현재 로직

```python
# Line 24-31
last_suc = category.lastSucYMD

# last_suc부터 오늘까지의 날짜 리스트 생성
next_day = last_suc  # + timedelta(days=1) 주석 처리됨
today = datetime.now(pytz.timezone('Asia/Seoul'))
date_list = [(next_day + timedelta(days=x)).strftime("%Y%m%d") 
             for x in range((today - next_day).days + 1)]

# Line 68: 날짜 필터링
if colDt in date_list:
    # 수집 처리
```

### 분석 결과

- ✅ `lastSucYMD`부터 오늘까지의 **모든 날짜**를 수집
- ❌ **6시간 간격 설정 없음**
- ❌ 시간 단위 필터링 없음

---

## 4. Selenium 수집 (`get_contents_by_selenium_main`)

**파일**: `docker_collect/selenium_collector.py`  
**함수**: `get_contents_by_selenium_main()`

### 현재 로직

```python
# Line 40-45
last_suc = category.lastSucYMD
next_day = last_suc  # + timedelta(days=1) 주석 처리됨
today = datetime.now(pytz.timezone('Asia/Seoul'))
date_list = [(next_day + timedelta(days=x)).strftime("%Y%m%d") 
             for x in range((today - next_day).days + 1)]

# Line 264: 날짜 필터링
if date in date_list:
    # 수집 처리
```

### 분석 결과

- ✅ `lastSucYMD`부터 오늘까지의 **모든 날짜**를 수집
- ❌ **6시간 간격 설정 없음**
- ❌ 시간 단위 필터링 없음

---

## 5. main_collect_and_scrapping.py의 7시간 설정

**파일**: `docker_shell/main_collect_and_scrapping.py`  
**Line 85-92**

```python
#7시간전 ~ 지금 까지의 contents 중 ollama 요약 안된 데이터 다시 요약(collectDT 기준)
end_date = datetime.utcnow()
start_date = end_date - timedelta(hours=7)

#코드 재개발 필요함 
contentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama()
```

### 분석 결과

- ⚠️ 이 설정은 **스크래핑 단계**에서만 사용됨 (주석 처리됨)
- ❌ **수집 단계와는 무관**
- ❌ 실제로는 사용되지 않음 (함수 호출 시 파라미터 전달 안 함)

---

## 6. 종합 분석

### 현재 동작 방식

1. **수집 단계 (Collect)**:
   - `lastSucYMD`부터 오늘까지의 **모든 날짜**를 수집
   - 시간 단위 필터링 없음
   - 날짜 단위로만 비교

2. **스크래핑 단계 (Scraping)**:
   - `contents_queue`의 모든 항목을 처리
   - 시간 간격 제한 없음

### 6시간 간격 수집을 위한 필요 사항

현재 코드로는 6시간 간격 수집이 불가능합니다. 구현하려면:

1. **시간 단위 비교 로직 추가**:
   ```python
   # 예시
   last_suc_datetime = category.lastSucYMD  # datetime 객체
   six_hours_ago = datetime.now() - timedelta(hours=6)
   
   if last_suc_datetime < six_hours_ago:
       # 수집 수행
   ```

2. **네이버 뉴스 API 시간 필터링**:
   - 네이버 뉴스 API는 시간 단위 필터링을 지원하지 않음
   - 수집 후 시간 필터링 필요

3. **나라장터 API 시간 필터링**:
   - 나라장터 API는 날짜 단위만 지원 (`inqryBgnDt`, `inqryEndDt`)
   - 시간 단위 필터링 불가능

---

## 7. 권장 사항

### 옵션 1: Cron Job으로 6시간마다 실행

현재 코드는 그대로 두고, cron job으로 6시간마다 실행:

```bash
# crontab 예시
0 */6 * * * /path/to/python /path/to/main_collect_and_scrapping.py
```

- 장점: 코드 수정 불필요
- 단점: `lastSucYMD`가 업데이트되지 않으면 중복 수집 가능

### 옵션 2: 시간 단위 필터링 추가

수집 함수에 시간 단위 필터링 로직 추가:

```python
# 예시: 6시간 이내 데이터만 수집
last_suc_datetime = category.lastSucYMD
six_hours_ago = datetime.now() - timedelta(hours=6)

if last_suc_datetime < six_hours_ago:
    # 수집 수행
else:
    # 스킵
```

- 장점: 중복 수집 방지
- 단점: 코드 수정 필요

### 옵션 3: lastSucYMD를 시간 단위로 저장

`lastSucYMD`를 날짜가 아닌 datetime으로 저장하고 시간 단위 비교:

- 장점: 정확한 시간 단위 제어 가능
- 단점: DB 스키마 변경 필요

---

## 8. 결론

| 항목 | 현재 상태 | 6시간 간격 설정 |
|------|----------|----------------|
| 나라장터 | 날짜 단위 수집 | ❌ 없음 |
| 네이버 뉴스 | 날짜 단위 수집 | ❌ 없음 |
| RSS | 날짜 단위 수집 | ❌ 없음 |
| Selenium | 날짜 단위 수집 | ❌ 없음 |

**현재 코드는 6시간 간격으로 데이터를 수집하도록 설정되어 있지 않습니다.**

6시간 간격 수집을 원한다면:
1. Cron job으로 6시간마다 실행 (코드 수정 불필요)
2. 또는 시간 단위 필터링 로직 추가 (코드 수정 필요)

---

**문서 작성자**: AI Assistant  
**최종 수정일**: 2025-01-XX

