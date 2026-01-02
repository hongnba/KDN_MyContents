# Selenium 기사 스크래핑 코드 분석

## 개요
`selenium_collector.py`는 Selenium WebDriver를 사용하여 웹사이트에서 기사를 크롤링하는 모듈입니다. 주로 정부 기관 및 공공기관의 공지사항/보도자료를 수집하는 데 사용됩니다.

## 주요 함수 구조

### 1. `get_contents_by_selenium_main(driver, contentsOrg, category)`
**역할**: 메인 진입점 함수. 전체 크롤링 프로세스를 관리합니다.

**실행 흐름**:
```
1. 날짜 리스트 생성 (lastSucYMD ~ 오늘)
   └─ date_list = [(next_day + timedelta(days=x)).strftime("%Y%m%d") for x in range(...)]

2. 웹페이지 초기 접속
   └─ driver.get(category.collectUrlInfo)
   └─ 특정 기관(A0029)의 경우 쿠키 처리

3. 첫 페이지 크롤링
   └─ get_contents_by_selenium() 호출

4. 페이지 네비게이션 (while loop)
   └─ result["next_page"].click()
   └─ get_contents_by_selenium() 반복 호출
   └─ next_page가 None이 될 때까지 반복

5. 수집 결과 처리
   └─ collect_cnt > 0: lastSucYMD 갱신 (성공)
   └─ collect_cnt == 0: lastSucYMD 미갱신 (실패)
```

**주요 특징**:
- `lastSucYMD`부터 오늘까지의 날짜 리스트를 생성
- 페이지 네비게이션을 자동으로 처리
- 수집 건수에 따라 `lastSucYMD` 갱신 여부 결정

---

### 2. `get_contents_by_selenium(driver, contentsOrg, category, date_list, today)`
**역할**: 단일 페이지에서 기사 정보를 추출하는 핵심 함수.

**데이터 추출 프로세스**:

#### 2.1 HTML 구조 파싱
```python
# tbody 또는 ul 요소 찾기
tbody = driver.find_element(By.XPATH, category.COL_HTML_TBODY_TAG)
# 또는
tbody = driver.find_element(By.TAG_NAME, 'tbody')

# tr 또는 li 요소들 찾기
trs = tbody.find_elements(By.TAG_NAME, category.COL_HTML_TR_TAG)
```

#### 2.2 각 행(tr) 처리
```python
for idx, tr in enumerate(trs):
    # 1. 공지사항 필터링
    if tr.get_attribute('class') == 'notice_alert':
        continue
    
    # 2. 제목 추출 (기관별로 다른 방식)
    if contentsOrg.orgId == 'A0001':
        title = td[1].find_element(By.TAG_NAME, 'a').text
    elif contentsOrg.orgId == 'A0023':
        title = tr.find_element(By.CLASS_NAME, category.COL_HTML_TITLE_TAG).text
    else:
        # BeautifulSoup로 span, em 태그 제거
        title = tr.find_element(By.CLASS_NAME, category.COL_HTML_TITLE_TAG)
        soup = BeautifulSoup(html_content, "html.parser")
        for tag in soup.find_all(["span", "em"]):
            tag.decompose()
        title = soup.text.strip()
    
    # 3. 날짜 추출
    date_element = td[category.COL_HTML_DATE_N].text  # '등록일자 2023.05.08'
    date_idx = date_element.find('202')
    date = date_element[date_idx:date_idx+10]
    date = re.sub(r'[^0-9]', '', date)  # 숫자만 추출 → '20230508'
    
    # 4. URL 추출
    if category.COL_HTML_URL_TYPE == 'link':
        url = tr.find_element(By.TAG_NAME, 'a').get_attribute(category.COL_HTML_URL_ATTR)
    elif category.COL_HTML_URL_TYPE == 'param':
        js_func = tr.get_attribute(category.COL_HTML_URL_ATTR)
        param_list = re.findall(r"'([^']*)'", js_func)
        url = category.COL_HTML_DETAIL_PAGE_URL + param_list[category.COL_HTML_URL_PARAM_N]
    
    # 5. 날짜 필터링
    if date in date_list:
        # ContentsCollectDetail 생성 및 DB 저장
        collectDetail = ContentsCollectDetail()
        collectDetail.url = url
        collectDetail.title = title
        collectDetail.pubDt = date
        collectDetail.shortUrl = generate_random_string(5)
        collectDetail.sucYN = bool(title and title.strip() and url and url.strip())
        
        if collectDetail.sucYN:
            if contentsCollectHistoryService.insertCategoryCollectHistory(...):
                collect_cnt += 1
```

#### 2.3 페이지 네비게이션 처리
```python
# 마지막 행이고 오늘 날짜인 경우
if idx == len(trs) - 1:
    # 페이지네이션 바 찾기
    page_bar = driver.find_element(By.CLASS_NAME, category.COL_HTML_PAGEBAR_TAG)
    
    # 현재 페이지 번호 추출
    now_page = page_bar.find_element(By.CLASS_NAME, category.COL_HTML_NOW_PAGE_INFO2).text
    
    # 다음 페이지 버튼 찾기 (기관별로 다른 방식)
    if contentsOrg.orgId == 'A0016':
        next_page = page_bar.find_element(By.XPATH, f'//*[@id="..."]/li[{int(now_page)+1}]/a')
    else:
        next_page = page_bar.find_element(By.XPATH, f'//*[text() = {int(now_page) + 1}]')
```

**반환값**:
```python
{
    "success": True/False,
    "datetime": today,
    "next_page": next_page_element or None
}
```

---

### 3. 특수 기관별 함수들

#### 3.1 `get_kepco_news(driver, contentsOrg, category)`
**대상**: 한국전력공사 (A0010, B0001)

**특징**:
- 페이지 인덱스를 직접 계산하여 URL 구성
- 각 기사 상세 페이지로 이동하여 제목 추출
- 날짜가 `date_list`에 없으면 즉시 종료 (내림차순 정렬 가정)

```python
while True:
    i += 1
    tr_idx = i % 10
    page_sum += 1
    page_idx = page_sum // 10
    col_url = category.collectUrlInfo + str(page_idx)
    driver.get(col_url)
    
    # 날짜 추출
    date = td[2].text
    date = year+month+day  # '20231101'
    
    if date in date_list:
        # 상세 페이지로 이동
        detail_page.click()
        detail_title = driver.find_element(By.CLASS_NAME, 'view').find_element(By.TAG_NAME, 'dt').text
        url = driver.current_url
        # DB 저장
    else:
        break  # 날짜 범위 밖이면 종료
```

#### 3.2 `get_koen_news(driver, contentsOrg, category)`
**대상**: 남동발전 (A0018)

**특징**:
- 재시도 로직 포함 (최대 5회)
- `onclick` 속성에서 파라미터 추출

#### 3.3 `get_kps_news(driver, contentsOrg, category)`
**대상**: 한국석유공사 (A0028)

**특징**:
- URL에 `pageIndex` 파라미터 추가
- `onclick` 속성에서 `selectedId` 추출

---

## 날짜 필터링 로직

### 현재 방식
```python
# 1. 날짜 리스트 생성
last_suc = category.lastSucYMD
next_day = last_suc
today = datetime.now(pytz.timezone('Asia/Seoul'))
date_list = [(next_day + timedelta(days=x)).strftime("%Y%m%d") 
             for x in range((today - next_day).days + 1)]

# 2. 각 기사의 날짜 추출
date = re.sub(r'[^0-9]', '', date_element)  # '20231101'

# 3. 필터링
if date in date_list:
    # 수집 처리
```

### 날짜 범위 지정 방식 (제안)
```python
# 날짜 범위가 지정된 경우
if start_date is not None and end_date is not None:
    date_list = [(start_date + timedelta(days=x)).strftime("%Y%m%d") 
                 for x in range((end_date - start_date).days + 1)]
else:
    # 기존 로직 (lastSucYMD ~ 오늘)
    date_list = [(next_day + timedelta(days=x)).strftime("%Y%m%d") 
                 for x in range((today - next_day).days + 1)]
```

---

## 네이버 뉴스 검색에 적용 가능한 방법

### 1. 네이버 뉴스 검색 페이지 구조
- URL: `https://search.naver.com/search.naver?where=news&query=한국전력`
- 날짜 필터: 검색 옵션에서 날짜 범위 지정 가능
- 페이지네이션: 하단에 페이지 번호 또는 "다음" 버튼

### 2. 구현 전략

#### 2.1 검색어 입력 및 날짜 필터 설정
```python
def get_naver_news_by_selenium(driver, contentsOrg, category, start_date, end_date):
    # 1. 네이버 뉴스 검색 페이지 접속
    base_url = "https://search.naver.com/search.naver?where=news"
    query = urllib.parse.quote(contentsOrg.orgKeywordList[0])  # 첫 번째 키워드
    url = f"{base_url}&query={query}"
    driver.get(url)
    time.sleep(2)
    
    # 2. 날짜 필터 설정 (검색 옵션 열기)
    try:
        # "옵션" 또는 "필터" 버튼 클릭
        option_button = driver.find_element(By.CLASS_NAME, "option_btn")  # 실제 클래스명 확인 필요
        option_button.click()
        time.sleep(1)
        
        # 날짜 범위 선택
        date_filter = driver.find_element(By.ID, "date_filter")  # 실제 ID 확인 필요
        date_filter.click()
        
        # 시작 날짜 입력
        start_date_input = driver.find_element(By.ID, "start_date")
        start_date_input.clear()
        start_date_input.send_keys(start_date.strftime("%Y.%m.%d"))
        
        # 종료 날짜 입력
        end_date_input = driver.find_element(By.ID, "end_date")
        end_date_input.clear()
        end_date_input.send_keys(end_date.strftime("%Y.%m.%d"))
        
        # 적용 버튼 클릭
        apply_button = driver.find_element(By.CLASS_NAME, "apply_btn")
        apply_button.click()
        time.sleep(2)
    except Exception as e:
        logger.warning(f"날짜 필터 설정 실패: {e}")
        # 필터 설정 실패 시에도 계속 진행 (수동 필터링)
    
    # 3. 기사 목록 크롤링
    date_list = [(start_date + timedelta(days=x)).strftime("%Y%m%d") 
                 for x in range((end_date - start_date).days + 1)]
    
    collect_cnt = 0
    page = 1
    
    while True:
        # 현재 페이지의 기사 목록 추출
        news_items = driver.find_elements(By.CLASS_NAME, "news_wrap")  # 실제 클래스명 확인 필요
        
        for item in news_items:
            # 제목 추출
            title_element = item.find_element(By.CLASS_NAME, "news_tit")
            title = title_element.text
            
            # 날짜 추출
            date_element = item.find_element(By.CLASS_NAME, "info_group")
            date_text = date_element.text  # "2023.11.01."
            date = re.sub(r'[^0-9]', '', date_text)  # '20231101'
            
            # URL 추출
            url = title_element.get_attribute('href')
            
            # 날짜 필터링
            if date in date_list:
                collectDetail = ContentsCollectDetail()
                collectDetail.url = url
                collectDetail.title = title
                collectDetail.pubDt = date
                collectDetail.shortUrl = generate_random_string(5)
                collectDetail.sucYN = bool(title and title.strip() and url and url.strip())
                
                if collectDetail.sucYN:
                    if contentsCollectHistoryService.insertCategoryCollectHistory(...):
                        collect_cnt += 1
        
        # 다음 페이지로 이동
        try:
            next_button = driver.find_element(By.CLASS_NAME, "btn_next")  # 실제 클래스명 확인 필요
            if "disabled" in next_button.get_attribute("class"):
                break  # 마지막 페이지
            next_button.click()
            time.sleep(2)
            page += 1
        except Exception as e:
            logger.info(f"페이지 네비게이션 종료: {e}")
            break
    
    return {"success": True, "count": collect_cnt, "datetime": datetime.utcnow()}
```

#### 2.2 주의사항
1. **실제 HTML 구조 확인 필요**: 네이버 뉴스 검색 페이지의 실제 클래스명, ID, XPath를 확인해야 합니다.
2. **봇 차단 우회**: User-Agent 설정, 쿠키 처리, 요청 간 딜레이 추가
3. **동적 로딩 대기**: `WebDriverWait`와 `expected_conditions` 사용
4. **에러 처리**: 요소를 찾지 못할 경우 대체 방법 제공

---

## 공통 패턴 및 베스트 프랙티스

### 1. 날짜 추출 패턴
```python
# 다양한 날짜 형식 처리
date_element = td[category.COL_HTML_DATE_N].text
# 예: "등록일자 2023.05.08", "2023-05-08", "2023/05/08"

date_idx = date_element.find('202')  # '202'로 시작하는 위치 찾기
date = date_element[date_idx:date_idx+10]  # 10자리 추출
date = re.sub(r'[^0-9]', '', date)  # 숫자만 남기기
```

### 2. URL 추출 패턴
```python
# 링크 타입
if category.COL_HTML_URL_TYPE == 'link':
    url = element.get_attribute('href')

# 파라미터 타입 (onclick 등)
elif category.COL_HTML_URL_TYPE == 'param':
    js_func = element.get_attribute('onclick')
    param_list = re.findall(r"'([^']*)'", js_func)
    url = base_url + param_list[index]
```

### 3. 페이지 네비게이션 패턴
```python
# 현재 페이지 번호 추출
now_page = page_bar.find_element(By.CLASS_NAME, 'now_page').text

# 다음 페이지 버튼 찾기
next_page = page_bar.find_element(By.XPATH, f'//*[text() = {int(now_page) + 1}]')

# 클릭 및 대기
next_page.click()
time.sleep(2)  # 또는 WebDriverWait 사용
```

---

## 결론

현재 `selenium_collector.py`의 구조는:
1. **날짜 리스트 기반 필터링**: `date_list`에 포함된 날짜만 수집
2. **페이지 네비게이션 자동화**: `next_page`를 찾아 자동으로 다음 페이지로 이동
3. **기관별 커스터마이징**: 각 기관의 HTML 구조에 맞춰 데이터 추출 로직 분기

네이버 뉴스 검색에 적용하려면:
1. 네이버 뉴스 검색 페이지의 실제 HTML 구조를 먼저 분석
2. 날짜 필터 설정 방법 확인 (옵션 메뉴 또는 URL 파라미터)
3. 기사 목록의 클래스명/구조 확인
4. 페이지네이션 방식 확인
5. 위의 패턴을 참고하여 새로운 함수 작성


