# 한국전력(A0010) 수집 방식 및 API KEY 분석

## 개요
한국전력공사(A0010)는 `contents_org` collection에서 2개의 카테고리를 가지고 있으며, 각각 다른 수집 방식을 사용합니다.

---

## 수집 방식 분류

### 1. Selenium 방식 (COL_METHOD: "C0003")
**카테고리**: 보도자료 (B0001)

#### 수집 대상 플랫폼
- **플랫폼**: 한국전력공사 공식 홈페이지
- **URL**: `https://home.kepco.co.kr/kepco/PR/ntcob/list.do?boardSeq=0&boardCd=BRD_000117&menuCd=FN060306&parnScrpSeq=0&searchCondition=total&searchKeyword&pageIndex=`
- **사용 함수**: `get_kepco_news(driver, contentsOrg, category)`

#### API KEY 사용 여부
- **APIKEY1**: `null` (사용 안 함)
- **APIKEY2**: `null` (사용 안 함)
- **설명**: Selenium은 웹 브라우저를 자동화하여 직접 웹페이지를 크롤링하므로 API KEY가 필요 없습니다.

#### 수집 방식 상세
```python
# selenium_collector.py의 get_kepco_news() 함수 사용
# - Selenium WebDriver로 한국전력 홈페이지 접속
# - 페이지네이션을 통해 기사 목록 순회
# - 각 기사의 제목, 날짜, URL 추출
# - 날짜 필터링 (lastSucYMD ~ 오늘)
```

#### MongoDB 저장 정보
```json
{
  "cateId": "B0001",
  "cateName": "보도자료",
  "COL_METHOD": "C0003",
  "collectUrlInfo": "https://home.kepco.co.kr/kepco/PR/ntcob/list.do?...",
  "APIKEY1": null,
  "APIKEY2": null,
  "collectMethod": "onlyPDF"
}
```

---

### 2. 네이버 뉴스 API 방식 (COL_METHOD: "C0002")
**카테고리**: 네이버 뉴스 (B0010)

#### 수집 대상 플랫폼
- **플랫폼**: 네이버 뉴스 검색 API
- **API URL**: `https://openapi.naver.com/v1/search/news.json?display=100&start=1&sort=sim&query=`
- **사용 함수**: `get_naver_news("A0026", contentsOrg, category)`

#### API KEY 정보
- **APIKEY1**: `p531jpkl0a9i_B7IuHFg` (X-Naver-Client-Id)
- **APIKEY2**: `Ppihi8s7Br` (X-Naver-Client-Secret)
- **설명**: 네이버 개발자 센터에서 발급받은 API KEY를 사용합니다.

#### API 호출 방식
```python
# openapi_collector.py의 get_naver_news() 함수 사용
request = urllib.request.Request(url)
request.add_header('X-Naver-Client-Id', category.APIKEY1)      # APIKEY1 사용
request.add_header('X-Naver-Client-Secret', category.APIKEY2)  # APIKEY2 사용
response = urllib.request.urlopen(request)
```

#### 검색 키워드
- **orgKeywordList**: `["한국전력공사", "한국전력"]`
- **category.keywords**: `[]` (빈 배열)
- **실제 검색어**: `orgKeywordList + category.keywords` 조합

#### MongoDB 저장 정보
```json
{
  "cateId": "B0010",
  "cateName": "네이버 뉴스",
  "COL_METHOD": "C0002",
  "collectUrlInfo": "https://openapi.naver.com/v1/search/news.json?display=100&start=1&sort=sim&query=",
  "APIKEY1": "p531jpkl0a9i_B7IuHFg",
  "APIKEY2": "Ppihi8s7Br",
  "collectMethod": "textInBody"
}
```

---

### 3. 나라장터 API 방식 (참고 정보)
**카테고리**: 한국전력(A0010)에는 나라장터 카테고리가 없음

#### 참고 정보
- **나라장터는 A0004 기관**에서 사용됩니다.
- **카테고리 ID**: B0005 (입찰정보)
- **사용 함수**: `get_g2b_nara(contentsOrg, category, g2b_keywords)`

#### API KEY 사용 여부
- 나라장터(G2B) API는 `collectUrlInfo`에 API KEY가 포함된 URL을 사용합니다.
- URL 예시: `https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch?serviceKey=...&numOfRows=100&pageNo=1&inqryDiv=1&type=json`
- `serviceKey` 파라미터에 API KEY가 포함됩니다.
- 한국전력(A0010)은 나라장터 카테고리를 가지고 있지 않으므로 이 방식을 사용하지 않습니다.

---

## 수집 방식 결정 로직

코드에서 수집 방식을 결정하는 로직:

```python
# collect_v2.py 또는 collect_and_analyze_integrated.py

for category in target_org.categoryList:
    # SELENIUM (COL_METHOD == "C0003")
    if category.COL_METHOD == "C0003":
        if contentsOrg.orgId == "A0010" and category.cateId == "B0001":
            result = get_kepco_news(driver, contentsOrg, category)  # 한국전력 보도자료
        else:
            result = get_contents_by_selenium_main(driver, contentsOrg, category)
    
    # RSS (COL_METHOD == "C0001")
    elif category.COL_METHOD == "C0001":
        result = get_contents_by_rss(contentsOrg, category)
    
    # OPEN API (COL_METHOD == "C0002" 등)
    else:
        if contentsOrg.orgId == "A0004" and category.cateId == "B0005":
            result = get_g2b_nara(contentsOrg, category, g2b_keywords)  # 나라장터
        else:
            result = get_naver_news("A0026", contentsOrg, category)  # 네이버 뉴스
```

---

## 한국전력(A0010) 카테고리 요약

| 카테고리 ID | 카테고리명 | 수집 방식 | COL_METHOD | API KEY 필요 | 플랫폼/서비스 |
|------------|-----------|----------|------------|-------------|--------------|
| B0001 | 보도자료 | Selenium | C0003 | ❌ 없음 | 한국전력공사 홈페이지 |
| B0010 | 네이버 뉴스 | Open API | C0002 | ✅ 필요 | 네이버 뉴스 검색 API |

---

## API KEY 저장 위치

### MongoDB Collection
- **Collection**: `contents_org`
- **Document**: `{"orgId": "A0010"}`
- **필드 경로**: `categoryList[].APIKEY1`, `categoryList[].APIKEY2`

### API KEY 사용 위치
1. **네이버 뉴스 API** (`openapi_collector.py`):
   ```python
   request.add_header('X-Naver-Client-Id', category.APIKEY1)
   request.add_header('X-Naver-Client-Secret', category.APIKEY2)
   ```

2. **나라장터 API** (`openapi_collector.py`의 `get_g2b_nara`):
   - 나라장터는 별도의 API KEY를 사용하지만, 한국전력(A0010)에는 해당 카테고리가 없습니다.

---

## 주의사항

1. **Selenium 방식 (보도자료)**:
   - API KEY가 필요 없습니다.
   - 웹사이트 구조 변경 시 크롤링 실패 가능성이 있습니다.
   - 봇 차단 위험이 있습니다.

2. **네이버 뉴스 API 방식**:
   - API KEY가 필수입니다.
   - API KEY는 네이버 개발자 센터에서 발급받아야 합니다.
   - API KEY 만료 시 수집이 중단됩니다.
   - API 호출 제한이 있습니다 (일일 호출량 제한).

3. **나라장터 API 방식**:
   - 한국전력(A0010)에는 해당 카테고리가 없습니다.
   - A0004 기관에서 사용됩니다.

---

## 결론

한국전력(A0010)은 **2가지 수집 방식**을 사용합니다:

1. **Selenium (보도자료)**: API KEY 불필요, 한국전력 홈페이지 직접 크롤링
2. **네이버 뉴스 API**: API KEY 필요 (`p531jpkl0a9i_B7IuHFg` / `Ppihi8s7Br`)

나라장터는 한국전력(A0010)의 카테고리에 포함되어 있지 않으므로, 한국전력은 나라장터 API를 사용하지 않습니다.

