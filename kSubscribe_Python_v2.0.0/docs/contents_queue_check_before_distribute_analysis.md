# contents_queue 체크 로직 확인 보고서

> 작성일: 2025-12-23  
> 확인 요청: `contents_queue` 컬렉션이 비어있지 않으면 `DockerCollectMain.distribute()`가 작동하지 않도록 구현되어 있는지 확인

---

## 📋 확인 결과

### ❌ **구현되어 있지 않습니다**

현재 코드에는 `contents_queue` 컬렉션이 비어있지 않으면 `DockerCollectMain.distribute()`가 작동하지 않도록 하는 로직이 **구현되어 있지 않습니다**.

---

## 🔍 상세 분석

### 1. DockerCollectMain.distribute() 메서드 확인

**파일**: `collect_v2.py` (Line 61-145)

**코드 내용**:
```python
def distribute(self):
    self.docker_collect_logger.info("--------------Docker_Collect 시작--------------")
    
    # dailycollecthistory가 없으면 생성
    self.dailyHistoryService.isExist()
    
    # 기관 카테고리 정보를 가져옴
    g2b_keywords = self.contentsOrgService.findOrgKeywords("A0004")
    contentsOrgList = ContentsOrgService().find_all()
    
    driver = get_driver()
    test_cnt = 0
    for contentsOrg in contentsOrgList:
        for category in contentsOrg.categoryList:
            # 수집 로직 실행
            # ...
```

**확인 사항**:
- ❌ `contents_queue` 컬렉션 체크 로직 없음
- ❌ `ContentsQueueService().find_all()` 호출 없음
- ❌ 큐가 비어있는지 확인하는 조건문 없음
- ✅ 바로 수집 로직 실행

**결론**: `distribute()` 메서드는 `contents_queue` 상태와 관계없이 항상 실행됩니다.

---

### 2. main_collect_and_scrapping.py 확인

**파일**: `main_collect_and_scrapping.py` (Line 48-56)

**코드 내용**:
```python
try:
    # 1. docker collect
    dockerCollectMain = DockerCollectMain()
    logger.info("dockerCollectMain.distribute()")
    dockerCollectMain.distribute()
    
except Exception as e:
    pass
```

**확인 사항**:
- ❌ `distribute()` 호출 전에 `contents_queue` 체크 없음
- ❌ `ContentsQueueService().find_all()` 호출 없음
- ❌ 큐가 비어있는지 확인하는 조건문 없음
- ✅ 바로 `distribute()` 호출

**결론**: `main_collect_and_scrapping.py`에서도 `contents_queue` 상태를 확인하지 않고 바로 `distribute()`를 호출합니다.

---

### 3. ContentsQueueService 메서드 확인

**파일**: `contentsQueueService.py`

**사용 가능한 메서드**:
- ✅ `find_all()`: 모든 큐 항목 조회
- ✅ `findByURL(url)`: URL로 항목 찾기
- ✅ `isExistQueue(url)`: URL 존재 여부 확인
- ❌ `count()`: 큐 항목 개수 조회 메서드 없음
- ❌ `isEmpty()`: 큐가 비어있는지 확인하는 메서드 없음

**확인 사항**:
- `find_all()`을 사용하면 큐가 비어있는지 확인할 수 있음
- 하지만 현재 코드에서는 `distribute()` 호출 전에 사용되지 않음

---

## 📊 코드 흐름 분석

### 현재 실행 흐름

```
main_collect_and_scrapping.py
    ↓
dockerCollectMain.distribute() 호출
    ↓
[contents_queue 체크 없음] ❌
    ↓
바로 수집 로직 실행
    ↓
웹사이트/RSS/API에서 기사 크롤링
    ↓
contents_queue에 저장
```

### 만약 구현되어 있다면 예상되는 흐름

```
main_collect_and_scrapping.py
    ↓
ContentsQueueService().find_all() 호출
    ↓
if len(queue_items) > 0:
    logger.info("contents_queue가 비어있지 않습니다. 수집을 건너뜁니다.")
    return  # 또는 continue
    ↓
dockerCollectMain.distribute() 호출 (스킵됨)
```

---

## 🔎 관련 코드 검색 결과

### 1. collect_v2.py 검색

```bash
grep -i "contents_queue\|queue\|isEmpty\|count" collect_v2.py
```

**결과**: 
- `ContentsQueueService` import만 있음 (Line 35)
- 실제 사용하는 코드 없음

### 2. main_collect_and_scrapping.py 검색

```bash
grep -i "contents_queue\|queue\|isEmpty\|count" main_collect_and_scrapping.py
```

**결과**:
- `ContentsQueueService` import 있음 (Line 9)
- `ContentsQueueService().removeDuplicateUrl()` 호출 있음 (Line 60)
- 하지만 `distribute()` 호출 전에 큐 체크 없음

---

## 💡 결론

### 현재 상태

1. **`DockerCollectMain.distribute()` 메서드**:
   - `contents_queue` 상태를 확인하지 않음
   - 항상 실행됨

2. **`main_collect_and_scrapping.py`**:
   - `distribute()` 호출 전에 `contents_queue` 체크 없음
   - 항상 `distribute()` 호출

3. **`ContentsQueueService`**:
   - `find_all()` 메서드로 큐 상태 확인 가능
   - 하지만 현재 코드에서 사용되지 않음

### 구현되어 있지 않은 기능

❌ `contents_queue`가 비어있지 않으면 `DockerCollectMain.distribute()`가 작동하지 않도록 하는 로직

### 현재 동작

✅ `contents_queue` 상태와 관계없이 `DockerCollectMain.distribute()`는 항상 실행됩니다.

---

## 📝 참고 사항

### 다른 부분에서의 큐 체크

`ContentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama()`에서는 큐 체크가 있습니다:

```python
# docker_scraping/contents_scraping_ollama_trafilaura.py
def crawl_and_analyze_ollama(self):
    queueContents = self.contentsQueueService.find_all()
    
    if len(queueContents) == 0:
        self.docker_scraping_logger.info("Queue is empty")
        return  # 큐가 비어있으면 스킵
    
    # 큐가 비어있지 않으면 처리
    for contentsQueueVO in queueContents:
        # ...
```

**차이점**:
- `crawl_and_analyze_ollama()`: 큐가 비어있으면 스킵 ✅
- `DockerCollectMain.distribute()`: 큐 상태와 관계없이 실행 ❌

---

## 🎯 요약

| 항목 | 상태 |
|------|------|
| `DockerCollectMain.distribute()` 내부 체크 | ❌ 없음 |
| `main_collect_and_scrapping.py`에서 체크 | ❌ 없음 |
| `ContentsQueueService`에 체크 메서드 | ⚠️ `find_all()`로 가능하나 사용 안함 |
| **결론** | ❌ **구현되어 있지 않음** |

**현재 동작**: `contents_queue` 상태와 관계없이 `DockerCollectMain.distribute()`는 항상 실행됩니다.



