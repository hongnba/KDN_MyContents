# collect_v2.py 날짜 필터링 분석 보고서

> 작성일: 2025-12-23  
> 분석 대상: `src/docker_collect/collect_v2.py`  
> 문제: 오늘 날짜 기사를 수집하지 않고 MongoDB의 `contents_queue` 컬렉션에 저장된 기존 데이터만 분석하고 있음

---

## 📋 목차

1. [문제 상황](#1-문제-상황)
2. [날짜 필터링 로직 분석](#2-날짜-필터링-로직-분석)
3. [수집 메서드별 날짜 처리](#3-수집-메서드별-날짜-처리)
4. [lastSucYMD 업데이트 메커니즘](#4-lastsucymd-업데이트-메커니즘)
5. [문제 원인 분석](#5-문제-원인-분석)
6. [결론](#6-결론)

---

## 1. 문제 상황

### 1.1 사용자 보고

- `main_collect_and_scrapping.py`에서 주석을 해제하고 실행
- **오늘 날짜 기사를 수집하지 않음**
- MongoDB의 `contents_queue` 컬렉션에 저장된 기존 데이터만 분석

### 1.2 실행 흐름

```
main_collect_and_scrapping.py
    ↓
DockerCollectMain.distribute() (주석 해제됨)
    ↓
각 기관/카테고리별 수집 함수 호출
    ↓
날짜 필터링 (lastSucYMD 기반)
    ↓
contents_queue에 저장
```

---

## 2. 날짜 필터링 로직 분석

### 2.1 핵심 로직

모든 수집 메서드(`get_contents_by_selenium_main`, `get_contents_by_rss`, `get_g2b_nara`, `get_naver_news`)에서 공통으로 사용하는 날짜 필터링 로직:

```python
# selenium_collector.py, rss_collector.py, openapi_collector.py 공통
last_suc = category.lastSucYMD  # 마지막 성공 수집 날짜
next_day = last_suc  # 주석처리: + timedelta(days=1)
today = datetime.now(pytz.timezone('Asia/Seoul'))
date_list = [(next_day + timedelta(days=x)).strftime("%Y%m%d") 
             for x in range((today - next_day).days + 1)]
```

### 2.2 날짜 리스트 생성 시나리오

#### 시나리오 1: lastSucYMD가 어제 날짜인 경우

```
lastSucYMD = 2025-12-22 (어제)
today = 2025-12-23 (오늘)

next_day = 2025-12-22
(today - next_day).days = 1
range(1 + 1) = range(2) = [0, 1]

date_list = [
    (2025-12-22 + 0일).strftime("%Y%m%d") = "20251222",
    (2025-12-22 + 1일).strftime("%Y%m%d") = "20251223"
]

결과: 어제와 오늘 날짜 모두 포함 ✅
```

#### 시나리오 2: lastSucYMD가 오늘 날짜인 경우

```
lastSucYMD = 2025-12-23 (오늘)
today = 2025-12-23 (오늘)

next_day = 2025-12-23
(today - next_day).days = 0
range(0 + 1) = range(1) = [0]

date_list = [
    (2025-12-23 + 0일).strftime("%Y%m%d") = "20251223"
]

결과: 오늘 날짜만 포함 ✅
```

#### 시나리오 3: lastSucYMD가 오늘보다 미래인 경우

```
lastSucYMD = 2025-12-24 (내일)
today = 2025-12-23 (오늘)

next_day = 2025-12-24
(today - next_day).days = -1
range(-1 + 1) = range(0) = []

date_list = []

결과: 빈 리스트 ❌ (오늘 날짜 미포함)
```

#### 시나리오 4: lastSucYMD가 며칠 전인 경우

```
lastSucYMD = 2025-12-20 (3일 전)
today = 2025-12-23 (오늘)

next_day = 2025-12-20
(today - next_day).days = 3
range(3 + 1) = range(4) = [0, 1, 2, 3]

date_list = [
    "20251220",  # 3일 전
    "20251221",  # 2일 전
    "20251222",  # 어제
    "20251223"   # 오늘
]

결과: 3일 전부터 오늘까지 모두 포함 ✅
```

### 2.3 주석처리된 코드의 영향

```python
# 원래 의도 (주석처리됨)
next_day = last_suc + timedelta(days=1)  # 마지막 성공 날짜의 다음 날부터

# 현재 코드
next_day = last_suc  # 마지막 성공 날짜부터 (중복 수집 가능)
```

**영향**:
- 원래 의도: `lastSucYMD` 다음 날부터 수집 (중복 방지)
- 현재 동작: `lastSucYMD`부터 수집 (중복 가능하지만, `insertCategoryCollectHistory`에서 중복 체크)

---

## 3. 수집 메서드별 날짜 처리

### 3.1 SELENIUM 수집 (`get_contents_by_selenium_main`)

**파일**: `selenium_collector.py`

**날짜 필터링**:
```python
# Line 40-45
last_suc = category.lastSucYMD
next_day = last_suc  # + timedelta(days=1) 주석처리
today = datetime.now(pytz.timezone('Asia/Seoul'))
date_list = [(next_day + timedelta(days=x)).strftime("%Y%m%d") 
             for x in range((today - next_day).days + 1)]
```

**기사 필터링**:
```python
# Line 264 (get_contents_by_selenium 함수 내부)
if date in date_list:  # date_list에 포함된 날짜만 수집
    # contents_queue에 저장
    contentsCollectHistoryService.insertCategoryCollectHistory(...)
```

**lastSucYMD 업데이트**:
```python
# Line 48, 115, 119, 130
lastSucYMD = today  # 항상 오늘 날짜로 설정

# 수집 성공 시
if collect_cnt > 0:
    contentsOrgService.updateCategorySucYMD(orgId, cateId, True, lastSucYMD, ...)
    # lastSucYMD를 오늘 날짜로 업데이트

# 수집 실패 시 (0건)
else:
    contentsOrgService.updateCategorySucYMD(orgId, cateId, False, lastSucYMD, ...)
    # lastSucYMD는 업데이트되지 않음 (기존 값 유지)
```

### 3.2 RSS 수집 (`get_contents_by_rss`)

**파일**: `rss_collector.py`

**날짜 필터링**:
```python
# Line 24-31
last_suc = category.lastSucYMD
next_day = last_suc  # + timedelta(days=1) 주석처리
today = datetime.now(pytz.timezone('Asia/Seoul'))
date_list = [(next_day + timedelta(days=x)).strftime("%Y%m%d") 
             for x in range((today - next_day).days + 1)]
```

**기사 필터링**:
```python
# Line 68
if colDt in date_list:  # RSS 피드의 published 날짜가 date_list에 포함된 경우만
    # contents_queue에 저장
    contentsCollectHistoryService.insertCategoryCollectHistory(...)
```

**lastSucYMD 업데이트**:
```python
# Line 34, 94, 98, 103
lastSucYMD = today  # 항상 오늘 날짜로 설정

# 수집 성공 시
if collect_cnt > 0:
    contentsOrgService.updateCategorySucYMD(orgId, cateId, True, lastSucYMD, ...)

# 수집 실패 시 (0건)
else:
    contentsOrgService.updateCategorySucYMD(orgId, cateId, False, lastSucYMD, ...)
```

### 3.3 OPEN API 수집 (`get_g2b_nara`, `get_naver_news`)

**파일**: `openapi_collector.py`

**날짜 필터링**:
```python
# get_g2b_nara (Line 33-41)
last_suc = category.lastSucYMD
next_day = last_suc  # + timedelta(days=1) 주석처리
today = datetime.now(pytz.timezone('Asia/Seoul'))
date_list = [(next_day + timedelta(days=x)).strftime("%Y%m%d") 
             for x in range((today - next_day).days + 1)]

# get_naver_news (Line 156-173)
last_suc = category.lastSucYMD
next_day = last_suc + timedelta(days=1)  # ⚠️ 여기만 주석처리 안됨!
today = datetime.now(pytz.timezone('Asia/Seoul'))
date_list = [(next_day + timedelta(days=x)).strftime("%Y%m%d") 
             for x in range((today - next_day).days + 1)]
```

**차이점**:
- `get_g2b_nara`: `next_day = last_suc` (lastSucYMD부터 포함)
- `get_naver_news`: `next_day = last_suc + timedelta(days=1)` (lastSucYMD 다음 날부터)

---

## 4. lastSucYMD 업데이트 메커니즘

### 4.1 업데이트 조건

**성공 시 업데이트** (`updateCategorySucYMD` 호출):
```python
if collect_cnt > 0:  # 수집 건수가 1건 이상
    contentsOrgService.updateCategorySucYMD(orgId, cateId, True, lastSucYMD, ...)
    # lastSucYMD를 오늘 날짜로 업데이트
```

**실패 시 업데이트 안함**:
```python
else:  # 수집 건수가 0건
    contentsOrgService.updateCategorySucYMD(orgId, cateId, False, lastSucYMD, ...)
    # lastSucYMD는 업데이트되지 않음 (기존 값 유지)
```

### 4.2 업데이트 로직 (`updateCategorySucYMD`)

**파일**: `contentsOrgService.py` (Line 298-327)

```python
def updateCategorySucYMD(self, org_id, category_id, sucYN, lastSucYMD, ...):
    update_fields = {
        "categoryList.$.sucYN": "Y" if sucYN else "N"
    }
    
    if sucYN:  # 성공 시에만 lastSucYMD 업데이트
        update_fields["categoryList.$.lastSucYMD"] = lastSucYMD
    
    collection.update_one(
        {"orgId": org_id, "categoryList.cateId": category_id},
        {"$set": update_fields}
    )
```

**중요**:
- `sucYN=True`일 때만 `lastSucYMD`가 업데이트됨
- `sucYN=False`일 때는 `lastSucYMD`가 업데이트되지 않음 (기존 값 유지)

---

## 5. 문제 원인 분석

### 5.1 가능한 원인들

#### 원인 1: lastSucYMD가 이미 오늘 날짜로 업데이트됨

**시나리오**:
1. 오늘 아침에 수집이 실행되어 오늘 날짜 기사를 수집함
2. 수집 성공 → `lastSucYMD`가 오늘 날짜로 업데이트됨
3. 오후에 다시 실행 → `lastSucYMD = 오늘 날짜`
4. `date_list = [오늘 날짜]` (1개만 포함)
5. 하지만 웹사이트/RSS 피드에 오늘 날짜 기사가 없거나 이미 수집됨
6. 결과: 0건 수집

**확인 방법**:
```python
# MongoDB에서 확인
db.contents_org.find(
    {"orgId": "A0010", "categoryList.cateId": "B0001"},
    {"categoryList.$": 1}
)
# categoryList[0].lastSucYMD 값 확인
```

#### 원인 2: lastSucYMD가 오늘보다 미래 날짜

**시나리오**:
1. 어제 수집이 실패하여 `lastSucYMD`가 업데이트되지 않음
2. 하지만 수동으로 `lastSucYMD`를 미래 날짜로 설정했거나
3. 타임존 문제로 `lastSucYMD`가 오늘보다 미래로 설정됨
4. `date_list = []` (빈 리스트)
5. 결과: 아무것도 수집하지 않음

**확인 방법**:
```python
# MongoDB에서 확인
# lastSucYMD가 오늘보다 미래인지 확인
```

#### 원인 3: 날짜 형식 불일치

**시나리오**:
1. `lastSucYMD`는 `datetime` 객체
2. `date_list`는 `["20251223"]` 형식 (문자열)
3. 웹사이트에서 추출한 날짜가 다른 형식 (예: `"2025-12-23"`, `"23.12.2025"`)
4. `if date in date_list` 조건이 False
5. 결과: 오늘 날짜 기사가 필터링됨

**확인 방법**:
- 로그에서 `date_list`와 실제 추출된 `date` 값 비교

#### 원인 4: 수집 시간대 문제

**시나리오**:
1. `today = datetime.now(pytz.timezone('Asia/Seoul'))` (한국 시간)
2. 웹사이트/RSS 피드의 날짜가 UTC 기준
3. 시간대 차이로 인해 날짜가 다름
4. 결과: 오늘 날짜 기사가 필터링됨

#### 원인 5: 중복 체크로 인한 스킵

**시나리오**:
1. 오늘 날짜 기사가 이미 `contents_queue`에 존재
2. `insertCategoryCollectHistory`에서 중복 체크:
   ```python
   if ContentsQueueService().isExistQueue(collectDetail.url):
       return None  # 스킵
   ```
3. 결과: 오늘 날짜 기사가 수집되지 않음 (이미 큐에 있음)

---

## 6. 결론

### 6.1 핵심 발견 사항

1. **날짜 필터링 로직은 정상 작동**:
   - `lastSucYMD`가 어제 날짜면 오늘 날짜가 포함됨
   - `lastSucYMD`가 오늘 날짜면 오늘 날짜가 포함됨

2. **문제는 `lastSucYMD` 값에 있음**:
   - `lastSucYMD`가 오늘보다 미래면 `date_list`가 비어있음
   - `lastSucYMD`가 오늘 날짜인데 웹사이트에 오늘 날짜 기사가 없으면 0건 수집

3. **중복 체크로 인한 스킵 가능성**:
   - 오늘 날짜 기사가 이미 `contents_queue`에 있으면 수집하지 않음

### 6.2 디버깅 권장 사항

1. **MongoDB에서 `lastSucYMD` 확인**:
   ```javascript
   db.contents_org.find(
       {},
       {
           "orgId": 1,
           "categoryList.cateId": 1,
           "categoryList.cateName": 1,
           "categoryList.lastSucYMD": 1
       }
   )
   ```

2. **로그에서 `date_list` 확인**:
   - `docker_collect_logger.info(f'date_list: {date_list}')` 추가

3. **수집된 기사 날짜 확인**:
   - `contents_queue` 컬렉션에서 오늘 날짜 기사가 있는지 확인
   - `collectDt` 또는 `pubDt` 필드 확인

4. **중복 체크 로그 확인**:
   - `"이미 Queue에 존재하는 contents입니다"` 로그 확인

### 6.3 예상되는 실제 문제

**가장 가능성 높은 원인**:
- `lastSucYMD`가 이미 오늘 날짜로 업데이트되어 있음
- 하지만 웹사이트/RSS 피드에 오늘 날짜 기사가 아직 게시되지 않았거나
- 이미 수집되어 `contents_queue`에 존재함
- 결과: 0건 수집 → `lastSucYMD`는 업데이트되지 않음 (기존 값 유지)
- 다음 실행 시에도 같은 상황 반복

**해결 방안**:
- `lastSucYMD`를 어제 날짜로 수동 조정하거나
- 수집 시간을 웹사이트 업데이트 시간 이후로 조정

---

## 7. 참고 코드 위치

- **날짜 필터링 로직**:
  - `selenium_collector.py`: Line 40-45
  - `rss_collector.py`: Line 24-31
  - `openapi_collector.py`: Line 33-41, 156-173

- **lastSucYMD 업데이트**:
  - `selenium_collector.py`: Line 115, 119, 130
  - `rss_collector.py`: Line 94, 98, 103
  - `contentsOrgService.py`: Line 298-327

- **중복 체크**:
  - `contentsCollectHistoryService.py`: Line 159-164



