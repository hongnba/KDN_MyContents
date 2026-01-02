# main_collect_and_scrapping2.py 코드 분석 보고서

## 1. Import 모듈 상세 분석

### 1.1 DockerCollectMain (docker_collect.collect_v2)
**역할**: 정부기관/공공기관 웹사이트에서 공고/뉴스/입찰정보 등을 수집하는 크롤러

**입력 인자**:
- 없음 (생성자에서 DB에서 기관 정보를 자동으로 조회)

**중간 처리 과정**:
1. `ContentsOrgService`에서 모든 기관(organization) 및 카테고리 정보 조회
2. 각 기관별, 카테고리별로 수집 방법(COL_METHOD) 확인:
   - `C0003` (SELENIUM): 동적 웹페이지 크롤링
   - `C0001` (RSS): RSS 피드 파싱
   - 기타 (OPEN API): 나라장터 API, 네이버 뉴스 API 등
3. 수집된 URL/제목/날짜 정보를 `ContentsQueueVO` 객체로 변환
4. `ContentsQueueService.insertQueue()`로 `contents_queue` 컬렉션에 저장

**결과물**:
- MongoDB `contents_queue` 컬렉션에 수집된 기사/공고 목록 저장
- 수집 성공/실패 건수 로깅
- 실패 시 `contents_collect_error` 컬렉션에 오류 정보 저장

---

### 1.2 ContentsScrapingOllamaTrafilaura (docker_scraping.contents_scraping_ollama_trafilaura)
**역할**: `contents_queue`에서 URL을 가져와 본문을 스크래핑하고, Ollama LLM으로 요약/키워드/감성분석 수행

**입력 인자**:
- 없음 (생성자에서 기관/카테고리/키워드 리스트를 DB에서 조회)

**중간 처리 과정**:

#### A. `crawl_and_analyze_ollama()` 메서드
1. `ContentsQueueService.find_all()`로 대기 중인 URL 목록 조회
2. 각 URL에 대해:
   - **웹 스크래핑**:
     - `WebLoaderV3` 또는 `TrafilauraScraper`로 본문 추출
     - PDF/HTML 등 다양한 포맷 지원
   - **LLM 분석** (`AnalysisOllamaGenerateCall.analysis_main()`):
     - 요약(shortSummary, longSummary)
     - 키워드 추출(keywords)
     - 감성 분석(긍정/부정/중립 비율)
     - 관련 기관별 평판 분석
   - **저장**:
     - `ContentsVO` 객체 생성
     - `contents` 컬렉션에 저장 (`BaseQueryService.insert_one()`)
     - 큐에서 삭제 (`ContentsQueueService.deleteQueue()`)

#### B. `process_articles_from_today_json()` 메서드
1. `today.json` 파일에서 기사 목록 읽기
2. 각 기사를 `contents_backup` 컬렉션에 저장 (별도 백업용)
3. 본문 스크래핑 및 LLM 분석 수행

**결과물**:
- MongoDB `contents` 컬렉션에 최종 분석 결과 저장:
  ```json
  {
    "title": "기사 제목",
    "url": "원본 URL",
    "contentsRaw": {
      "title": "제목",
      "contents": "본문 전체 텍스트"
    },
    "contentsMeta": {
      "keywords": ["키워드1", "키워드2"],
      "shortSummary": "한 줄 요약",
      "longSummary": "상세 요약",
      "sentiments": [
        {
          "orgId": "A0001",
          "positiveRatio": 70,
          "negativeRatio": 10,
          "neutralRatio": 20
        }
      ]
    },
    "metaSucYN": "Y",  // 분석 성공 여부
    "rawCollectSucYN": "Y"  // 스크래핑 성공 여부
  }
  ```

---

### 1.3 OllamaAlive (ksubscribe_server.analysis.ollama_alive)
**역할**: Ollama 서비스의 헬스체크 및 장애 시 알림

**입력 인자**:
- `op_mode`: "docker_server" 또는 "ollama_server"
- `keep_alive`: True면 백그라운드 스레드 유지, False면 작업 완료 시 종료

**중간 처리 과정**:
1. 별도 스레드에서 1초마다 Ollama API (`/api/ps`) 헬스체크
2. 5회 연속 실패 시:
   - 로그 기록
   - 관리자에게 텔레그램 알림 전송 (`TelegramSendModel`)
   - (설정에 따라) Ollama 서비스 재시작 시도

**결과물**:
- Ollama 서비스 장애 모니터링
- 관리자 알림 (Telegram)

---

### 1.4 ContentsQueueService (ksubscribe_share.db.service.contentsQueueService)
**역할**: `contents_queue` 컬렉션 관리 (대기열 관리)

**주요 메서드**:
- `insertQueue()`: 수집한 URL을 큐에 추가
- `find_all()`: 모든 대기 중인 항목 조회
- `deleteQueue()`: 처리 완료된 항목 삭제
- `removeDuplicateUrl()`: 중복 URL 제거 (같은 URL이 여러 번 들어간 경우)

**입력/출력**:
- 입력: `orgId`, `cateId`, `url`, `title`, `pubDt` 등
- 출력: `List[ContentsQueueVO]`

---

### 1.5 StatsService (ksubscribe_share.db.service.statsService)
**역할**: 기관별 통계 집계 (일별/주별/월별)

**입력 인자**:
- `orgId`: 기관 ID (예: "A0001")
- `period`: "day", "week", "month"
- `start_date`, `end_date`: 집계 기간

**중간 처리 과정**:
1. 해당 기간의 `contents` 문서들을 조회
2. 집계 계산:
   - 총 기사 수
   - 긍정/부정/중립 기사 수
   - 평균 감성 비율
   - 키워드 빈도 통계
3. 기존 통계가 있으면 업데이트, 없으면 신규 생성

**결과물**:
- `daily_stats`, `weekly_stats`, `monthly_stats` 컬렉션에 저장
- 통계 객체 반환 (`DailyStatsVO`, `WeeklyStatsVO`, `MonthlyStatsVO`)

---

### 1.6 ContentsOrgService, CalendarService
**역할**:
- `ContentsOrgService`: 기관 정보 관리 (`contents_org` 컬렉션)
- `CalendarService`: 일별 평판 달력 정보 생성

---

### 1.7 Logger (ksubscribe_share.logger)
**역할**: 로깅 유틸리티

**주요 로거**:
- `docker_collect_logger_name`: 수집(collect) 로그
- `docker_scraping_logger_name`: 스크래핑 상세 로그
- `docker_scraping_result_logger_name`: 스크래핑 결과 요약 로그

---

## 2. main_collect_and_scrapping2.py 실행 흐름

### 2.1 명령줄 인자에 따른 분기

#### A. `--today-json` 플래그가 있는 경우
```
실행: python main_collect_and_scrapping2.py --today-json
```

**흐름**:
1. `OllamaAlive` 헬스체크 스레드 시작
2. `process_articles_from_today_json()` 실행
   - `today.json` 파일에서 기사 목록 읽기
   - 각 기사를 `contents_backup` 컬렉션에 저장
3. `OllamaAlive` 스레드 종료

**용도**: 특정 JSON 파일에 있는 기사만 처리 (테스트/복구용)

---

#### B. 플래그가 없는 경우 (기본 전체 파이프라인)
```
실행: python main_collect_and_scrapping2.py
```

**전체 흐름**:

```
[1단계: 수집] (주석 처리됨 - 현재 비활성)
├─ DockerCollectMain.distribute()
│  ├─ 정부기관 웹사이트 크롤링
│  └─ contents_queue에 URL 저장
└─ ContentsQueueService.removeDuplicateUrl()
   └─ 중복 URL 제거

[2단계: 스크래핑 및 분석] (활성화)
├─ OllamaAlive 시작 (백그라운드 헬스체크)
├─ ContentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama()
│  ├─ contents_queue에서 URL 목록 조회
│  ├─ 각 URL에 대해:
│  │  ├─ 웹 본문 스크래핑 (WebLoaderV3 / TrafilauraScraper)
│  │  ├─ Ollama LLM 분석 (요약/키워드/감성)
│  │  ├─ contents 컬렉션에 저장
│  │  └─ 큐에서 삭제
│  └─ 성공/실패 건수 로깅
└─ (주석 처리됨) ContentsService.removeDuplicateUrl()

[3단계: 재시도 분석] (활성화)
└─ 7시간 전~현재 중 분석 실패 건 재시도
   └─ crawl_and_analyze_ollama() 재실행

[4단계: 통계 계산] (활성화)
├─ ContentsOrgService.get_all()로 전체 기관 조회
└─ 각 기관별로:
   ├─ StatsService.count_for_period(orgId, 'day')
   ├─ StatsService.count_for_period(orgId, 'week')
   ├─ StatsService.count_for_period(orgId, 'month')
   └─ CalendarService.get_calendar_results(orgId)
      └─ 일별 긍정/부정 달력 데이터 생성

[종료]
└─ OllamaAlive 스레드 종료
```

---

## 3. 데이터 흐름 요약

```
[외부 웹사이트]
     ↓ (1) 크롤링
[contents_queue] ← DockerCollectMain
     ↓ (2) URL 목록
ContentsScrapingOllamaTrafilaura
     ↓ (3) 본문 스크래핑
[원문 텍스트]
     ↓ (4) LLM 분석
[AnalysisOllamaGenerateCall]
     ↓ (5) 요약/키워드/감성
[contents] ← MongoDB 저장
     ↓ (6) 통계 집계
[daily_stats, weekly_stats, monthly_stats]
```

---

## 4. 주요 MongoDB 컬렉션

| 컬렉션 이름 | 역할 | 생성 시점 |
|------------|------|----------|
| `contents_queue` | 수집 대기 URL 목록 | DockerCollectMain |
| `contents` | 최종 분석 결과 (본문+요약+감성) | ContentsScrapingOllamaTrafilaura |
| `contents_backup` | today.json 백업용 | process_articles_from_today_json() |
| `contents_org` | 기관 정보 (orgId, 카테고리 등) | 사전 설정 |
| `contents_collect_error` | 수집 실패 로그 | DockerCollectMain (실패 시) |
| `daily_stats` | 일별 통계 | StatsService |
| `weekly_stats` | 주별 통계 | StatsService |
| `monthly_stats` | 월별 통계 | StatsService |

---

## 5. 핵심 설정 및 주의사항

### 현재 주석 처리된 부분 (비활성화)
- **1단계 수집** (`DockerCollectMain.distribute()`)
  - 이유: 테스트 중이거나 별도 스케줄러로 실행 중일 가능성
- **중복 제거** (`ContentsService.removeDuplicateUrl()`)
  - 이유: 성능 이슈 또는 별도 처리

### 활성화된 주요 기능
- **스크래핑 및 분석** (2단계): `crawl_and_analyze_ollama()`
- **재시도 로직** (3단계): 7시간 내 실패 건 재분석
- **통계 집계** (4단계): 일/주/월별 통계 자동 계산

### 환경 의존성
- **Ollama API**: `CONF.OLLAMA_URL` (예: http://10.99.2.71:11434)
- **MongoDB**: `MongoManager`로 연결
- **Selenium WebDriver**: Chrome/Chromium 드라이버 필요
- **Telegram**: 관리자 알림용 (CONF.TELEGRAM_SEND_TOKEN)

---

## 6. 오류 처리 및 복구

### 스크래핑 실패 시
- `rawCollectSucYN = "N"` 설정
- `contentsRaw.errorInfo`에 오류 정보 저장
- `contents` 컬렉션에도 실패 정보 기록 (분석 없이)

### LLM 분석 실패 시
- `metaSucYN = "N"` 설정
- `contentsMeta.errorInfo`에 오류 이유 저장
- 7시간 후 재시도 로직에 의해 재분석 시도

### Ollama 서비스 장애 시
- `OllamaAlive` 스레드가 5회 연속 실패 감지
- 관리자에게 텔레그램 알림
- (옵션) 자동 서비스 재시작

---

## 7. 성능 및 확장성

### 병렬 처리
- 현재는 순차 처리 (`for` 루프)
- 개선 가능: `asyncio` 또는 멀티프로세싱으로 병렬화

### 큐 관리
- `contents_queue` 크기가 클 경우 배치 처리 권장
- 중복 URL은 `removeDuplicateUrl()`로 주기적 정리

### 통계 계산
- 전체 기관 순회 방식 (O(N))
- 기관 수가 많을 경우 비동기 또는 백그라운드 작업 권장

---

## 8. 개선 제안

1. **1단계 수집 활성화 여부 확인**: 주석된 `DockerCollectMain.distribute()` 코드의 활성화 필요성 검토
2. **재시도 로직 개선**: 현재 `crawl_and_analyze_ollama()` 전체 재실행 → 실패 건만 필터링하도록 개선
3. **통계 계산 최적화**: 변경된 데이터만 집계하도록 증분 업데이트
4. **모니터링 강화**: 각 단계별 소요 시간, 큐 크기, 성공률 등을 메트릭으로 수집
5. **에러 핸들링**: 예외 발생 시 상세 스택트레이스 로깅 및 복구 전략

---

이상으로 `main_collect_and_scrapping2.py` 코드 분석을 마칩니다.
