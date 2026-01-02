# main_collect_and_scrapping2.py 실행 흐름도

## 전체 파이프라인 구조

```mermaid
flowchart TD
    Start([프로그램 시작]) --> CheckArgs{명령줄 인자<br/>--today-json?}
    
    %% today-json 모드
    CheckArgs -->|Yes| TodayMode[Today JSON 모드]
    TodayMode --> StartOllama1[OllamaAlive 스레드 시작]
    StartOllama1 --> ProcessToday[process_articles_from_today_json]
    ProcessToday --> LoadJSON[today.json 파일 읽기]
    LoadJSON --> ForEachArticle[각 기사 처리]
    ForEachArticle --> ScrapeToday[본문 스크래핑]
    ScrapeToday --> AnalyzeToday[LLM 분석]
    AnalyzeToday --> SaveBackup[contents_backup에 저장]
    SaveBackup --> StopOllama1[OllamaAlive 스레드 종료]
    StopOllama1 --> End1([종료])
    
    %% 전체 파이프라인 모드
    CheckArgs -->|No| FullMode[전체 파이프라인 모드]
    
    %% 1단계: 수집 (주석처리)
    FullMode --> Stage1Comment[1단계: 수집<br/>현재 비활성화]
    Stage1Comment -.->|주석 처리됨| Collect[DockerCollectMain.distribute]
    Collect -.-> CrawlWebsites[정부기관 웹사이트 크롤링]
    CrawlWebsites -.-> SaveQueue[contents_queue에 저장]
    SaveQueue -.-> RemoveDup1[중복 URL 제거]
    
    %% 2단계: 스크래핑 및 분석
    Stage1Comment --> Stage2[2단계: 스크래핑 및 분석<br/>활성화]
    Stage2 --> StartOllama2[OllamaAlive 헬스체크 시작]
    
    StartOllama2 --> GetQueue[contents_queue 조회]
    GetQueue --> CheckEmpty{큐가<br/>비었는가?}
    CheckEmpty -->|Yes| SkipScrape[스크래핑 스킵]
    CheckEmpty -->|No| ForEachQueue[각 URL 순회]
    
    ForEachQueue --> CheckExist{이미<br/>존재?}
    CheckExist -->|Yes| NextURL1[다음 URL]
    CheckExist -->|No| ValidateOrg{기관/카테고리<br/>유효?}
    
    ValidateOrg -->|No| NextURL2[다음 URL]
    ValidateOrg -->|Yes| ScrapeWeb[웹 스크래핑]
    
    ScrapeWeb --> ChooseMethod{수집 방법}
    ChooseMethod -->|PDF| WebLoaderPDF[WebLoaderV3<br/>PDF 처리]
    ChooseMethod -->|HTML/Body| TrafilauraHTML[TrafilauraScraper<br/>본문 추출]
    ChooseMethod -->|Tag| TrafilauraTag[Trafilaura<br/>태그 기반]
    
    WebLoaderPDF --> CheckSuccess{스크래핑<br/>성공?}
    TrafilauraHTML --> CheckSuccess
    TrafilauraTag --> CheckSuccess
    
    CheckSuccess -->|No| SaveFail[실패 정보 저장<br/>rawCollectSucYN=N]
    SaveFail --> DeleteQ1[큐에서 삭제]
    DeleteQ1 --> NextURL3[다음 URL]
    
    CheckSuccess -->|Yes| LLMAnalysis[Ollama LLM 분석]
    LLMAnalysis --> ExtractKeywords[키워드 추출]
    ExtractKeywords --> GenerateSummary[요약 생성]
    GenerateSummary --> SentimentAnalysis[감성 분석]
    SentimentAnalysis --> CheckAnalysis{분석<br/>성공?}
    
    CheckAnalysis -->|Yes| SaveSuccess[contents 저장<br/>metaSucYN=Y]
    CheckAnalysis -->|No| SaveAnalysisFail[contents 저장<br/>metaSucYN=N]
    
    SaveSuccess --> DeleteQ2[큐에서 삭제]
    SaveAnalysisFail --> DeleteQ2
    DeleteQ2 --> IncCounter[성공 카운터 증가]
    IncCounter --> NextURL3
    
    NextURL1 --> CheckMoreURLs{더 많은<br/>URL?}
    NextURL2 --> CheckMoreURLs
    NextURL3 --> CheckMoreURLs
    SkipScrape --> Stage3
    
    CheckMoreURLs -->|Yes| ForEachQueue
    CheckMoreURLs -->|No| LogResults[결과 로깅]
    
    %% 3단계: 재시도
    LogResults --> Stage3[3단계: 재시도 분석<br/>활성화]
    Stage3 --> CalcTimeRange[7시간 전~현재 계산]
    CalcTimeRange --> RetryAnalysis[실패 건 재분석]
    RetryAnalysis --> RerunScrape[crawl_and_analyze_ollama<br/>재실행]
    
    %% 4단계: 통계
    RerunScrape --> Stage4[4단계: 통계 계산<br/>활성화]
    Stage4 --> GetAllOrgs[전체 기관 목록 조회]
    GetAllOrgs --> ForEachOrg[각 기관 순회]
    
    ForEachOrg --> CalcDaily[일별 통계 계산]
    CalcDaily --> CalcWeekly[주별 통계 계산]
    CalcWeekly --> CalcMonthly[월별 통계 계산]
    CalcMonthly --> CalcCalendar[달력 데이터 생성]
    
    CalcCalendar --> SaveStats[daily_stats,<br/>weekly_stats,<br/>monthly_stats 저장]
    SaveStats --> NextOrg{더 많은<br/>기관?}
    
    NextOrg -->|Yes| ForEachOrg
    NextOrg -->|No| StopOllama2[OllamaAlive 스레드 종료]
    
    StopOllama2 --> End2([종료])
    
    %% 스타일링
    classDef activeStage fill:#90EE90,stroke:#228B22,stroke-width:2px
    classDef inactiveStage fill:#FFE4B5,stroke:#FF8C00,stroke-width:2px,stroke-dasharray: 5 5
    classDef decision fill:#87CEEB,stroke:#4682B4,stroke-width:2px
    classDef process fill:#FFB6C1,stroke:#DC143C,stroke-width:2px
    classDef database fill:#DDA0DD,stroke:#8B008B,stroke-width:2px
    
    class Stage2,Stage3,Stage4,StartOllama1,StartOllama2 activeStage
    class Stage1Comment,Collect,CrawlWebsites,SaveQueue,RemoveDup1 inactiveStage
    class CheckArgs,CheckEmpty,CheckExist,ValidateOrg,ChooseMethod,CheckSuccess,CheckAnalysis,CheckMoreURLs,NextOrg decision
    class ScrapeWeb,LLMAnalysis,ExtractKeywords,GenerateSummary,SentimentAnalysis process
    class SaveQueue,SaveSuccess,SaveFail,SaveBackup,SaveStats database
```

---

## 데이터 흐름도 (MongoDB 컬렉션 중심)

```mermaid
flowchart LR
    subgraph External[외부 소스]
        Web[정부기관 웹사이트]
        JSON[today.json]
    end
    
    subgraph Stage1[1단계: 수집]
        Crawler[DockerCollectMain<br/>크롤러]
    end
    
    subgraph Queue[대기열]
        QueueDB[(contents_queue)]
    end
    
    subgraph Stage2[2단계: 스크래핑]
        Scraper[WebLoaderV3 /<br/>TrafilauraScraper]
        RawText[원문 텍스트]
    end
    
    subgraph Stage3[3단계: LLM 분석]
        Ollama[AnalysisOllamaGenerateCall<br/>Ollama LLM]
        MetaData[요약/키워드/감성]
    end
    
    subgraph MainDB[주요 데이터베이스]
        ContentsDB[(contents)]
        BackupDB[(contents_backup)]
        OrgDB[(contents_org)]
    end
    
    subgraph Stage4[4단계: 통계]
        StatsCalc[StatsService]
        StatsDB[(daily_stats<br/>weekly_stats<br/>monthly_stats)]
    end
    
    subgraph Monitoring[모니터링]
        Health[OllamaAlive<br/>헬스체크]
        Telegram[Telegram 알림]
    end
    
    %% 데이터 흐름
    Web -->|크롤링| Crawler
    Crawler -->|URL 저장| QueueDB
    JSON -->|직접 처리| Scraper
    
    QueueDB -->|URL 조회| Scraper
    Scraper -->|본문 추출| RawText
    RawText -->|분석 요청| Ollama
    Ollama -->|분석 결과| MetaData
    
    MetaData -->|저장| ContentsDB
    MetaData -.->|백업| BackupDB
    OrgDB -->|기관 정보 참조| Scraper
    OrgDB -->|기관 정보 참조| Ollama
    
    ContentsDB -->|집계| StatsCalc
    StatsCalc -->|통계 저장| StatsDB
    
    Ollama -.->|상태 체크| Health
    Health -.->|장애 시| Telegram
    
    %% 스타일
    classDef dbStyle fill:#DDA0DD,stroke:#8B008B,stroke-width:3px
    classDef processStyle fill:#90EE90,stroke:#228B22,stroke-width:2px
    classDef externalStyle fill:#FFE4B5,stroke:#FF8C00,stroke-width:2px
    
    class QueueDB,ContentsDB,BackupDB,OrgDB,StatsDB dbStyle
    class Crawler,Scraper,Ollama,StatsCalc processStyle
    class Web,JSON externalStyle
```

---

## 모듈 간 의존성 다이어그램

```mermaid
graph TB
    subgraph Main[main_collect_and_scrapping2.py]
        MainScript[메인 스크립트]
    end
    
    subgraph Collect[수집 모듈]
        DockerCollect[DockerCollectMain]
        RSS[RSSCollector]
        Selenium[SeleniumCollector]
        OpenAPI[OpenAPICollector]
    end
    
    subgraph Scraping[스크래핑 모듈]
        ContentsScraping[ContentsScrapingOllamaTrafilaura]
        WebLoader[WebLoaderV3]
        Trafilaura[TrafilauraScraper]
    end
    
    subgraph Analysis[분석 모듈]
        OllamaAnalysis[AnalysisOllamaGenerateCall]
        OllamaAlive[OllamaAlive]
        ChatOllama[ChatOllama<br/>langchain_ollama]
    end
    
    subgraph Services[DB 서비스]
        QueueService[ContentsQueueService]
        ContentsService[ContentsService]
        StatsService[StatsService]
        OrgService[ContentsOrgService]
        CalendarService[CalendarService]
    end
    
    subgraph Database[MongoDB]
        MongoDB[(MongoDB<br/>mycontents DB)]
    end
    
    subgraph External[외부 서비스]
        OllamaServer[Ollama Server<br/>:11434]
        TelegramAPI[Telegram API]
    end
    
    subgraph Utils[유틸리티]
        Logger[Logger]
        Config[Config]
    end
    
    %% 의존성 관계
    MainScript --> DockerCollect
    MainScript --> ContentsScraping
    MainScript --> OllamaAlive
    MainScript --> StatsService
    MainScript --> CalendarService
    MainScript --> OrgService
    MainScript --> Logger
    
    DockerCollect --> RSS
    DockerCollect --> Selenium
    DockerCollect --> OpenAPI
    DockerCollect --> QueueService
    DockerCollect --> OrgService
    
    ContentsScraping --> WebLoader
    ContentsScraping --> Trafilaura
    ContentsScraping --> OllamaAnalysis
    ContentsScraping --> QueueService
    ContentsScraping --> ContentsService
    ContentsScraping --> OrgService
    
    OllamaAnalysis --> ChatOllama
    OllamaAlive --> TelegramAPI
    
    QueueService --> MongoDB
    ContentsService --> MongoDB
    StatsService --> MongoDB
    OrgService --> MongoDB
    CalendarService --> MongoDB
    
    ChatOllama --> OllamaServer
    OllamaAlive --> OllamaServer
    
    DockerCollect --> Logger
    ContentsScraping --> Logger
    OllamaAlive --> Logger
    
    DockerCollect --> Config
    ContentsScraping --> Config
    OllamaAnalysis --> Config
    OllamaAlive --> Config
    
    %% 스타일
    classDef mainClass fill:#FF6B6B,stroke:#C92A2A,stroke-width:3px,color:#fff
    classDef moduleClass fill:#4ECDC4,stroke:#0B7285,stroke-width:2px
    classDef serviceClass fill:#95E1D3,stroke:#087F5B,stroke-width:2px
    classDef dbClass fill:#DDA0DD,stroke:#8B008B,stroke-width:3px
    classDef externalClass fill:#FFD93D,stroke:#F59F00,stroke-width:2px
    
    class MainScript mainClass
    class DockerCollect,ContentsScraping,OllamaAnalysis,OllamaAlive moduleClass
    class QueueService,ContentsService,StatsService,OrgService,CalendarService serviceClass
    class MongoDB dbClass
    class OllamaServer,TelegramAPI externalClass
```

---

## 단계별 상세 시퀀스 다이어그램

### 2단계: 스크래핑 및 분석 상세 흐름

```mermaid
sequenceDiagram
    participant Main as main_collect_and_scrapping2.py
    participant Alive as OllamaAlive
    participant Scraping as ContentsScrapingOllamaTrafilaura
    participant Queue as ContentsQueueService
    participant Loader as WebLoaderV3/Trafilaura
    participant Ollama as AnalysisOllamaGenerateCall
    participant LLM as Ollama Server
    participant DB as MongoDB (contents)
    
    Main->>Alive: start_thread()
    activate Alive
    Note over Alive: 백그라운드 헬스체크 시작
    
    Main->>Scraping: crawl_and_analyze_ollama()
    activate Scraping
    
    Scraping->>Queue: find_all()
    activate Queue
    Queue-->>Scraping: List[ContentsQueueVO]
    deactivate Queue
    
    loop 각 URL 처리
        Scraping->>Scraping: 중복/유효성 검사
        
        Scraping->>Loader: 본문 스크래핑
        activate Loader
        Loader->>Loader: HTML 파싱 / PDF 추출
        Loader-->>Scraping: (success, text)
        deactivate Loader
        
        alt 스크래핑 성공
            Scraping->>Ollama: analysis_main(text, keywords, orgs)
            activate Ollama
            
            Ollama->>LLM: 요약 프롬프트
            LLM-->>Ollama: shortSummary, longSummary
            
            Ollama->>LLM: 키워드 프롬프트
            LLM-->>Ollama: keywords[]
            
            Ollama->>LLM: 감성 분석 프롬프트
            LLM-->>Ollama: sentiments[]
            
            Ollama-->>Scraping: ContentsMetaResult
            deactivate Ollama
            
            Scraping->>DB: insert_one(ContentsVO)
            DB-->>Scraping: OK
            
            Scraping->>Queue: deleteQueue(_id)
            Queue-->>Scraping: OK
            
            Note over Scraping: 성공 카운터 증가
        else 스크래핑 실패
            Scraping->>DB: insert_one (실패 정보)
            Scraping->>Queue: deleteQueue(_id)
        end
    end
    
    Scraping-->>Main: 완료 (성공/실패 건수)
    deactivate Scraping
    
    Main->>Alive: stop_thread()
    deactivate Alive
```

---

## 통계 계산 흐름

```mermaid
flowchart TD
    Start([통계 계산 시작]) --> GetOrgs[ContentsOrgService.get_all]
    GetOrgs --> LoopOrgs{각 기관 순회}
    
    LoopOrgs --> CalcDay[일별 통계]
    CalcDay --> GetDayData[오늘 00:00~23:59<br/>contents 조회]
    GetDayData --> AggDay[집계 계산]
    AggDay --> SaveDay[daily_stats 저장]
    
    SaveDay --> CalcWeek[주별 통계]
    CalcWeek --> GetWeekData[이번 주 월~일<br/>contents 조회]
    GetWeekData --> AggWeek[집계 계산]
    AggWeek --> SaveWeek[weekly_stats 저장]
    
    SaveWeek --> CalcMonth[월별 통계]
    CalcMonth --> GetMonthData[이번 달 1일~말일<br/>contents 조회]
    GetMonthData --> AggMonth[집계 계산]
    AggMonth --> SaveMonth[monthly_stats 저장]
    
    SaveMonth --> CalcCal[달력 데이터]
    CalcCal --> GenCalendar[일별 긍정/부정 비율]
    GenCalendar --> NextOrg{다음 기관?}
    
    NextOrg -->|Yes| LoopOrgs
    NextOrg -->|No| End([통계 계산 완료])
    
    subgraph 집계 내용
        AggContent[총 기사 수<br/>긍정/부정/중립 수<br/>평균 감성 비율<br/>키워드 빈도]
    end
    
    AggDay -.-> AggContent
    AggWeek -.-> AggContent
    AggMonth -.-> AggContent
    
    classDef processStyle fill:#90EE90,stroke:#228B22,stroke-width:2px
    classDef dbStyle fill:#DDA0DD,stroke:#8B008B,stroke-width:2px
    class CalcDay,CalcWeek,CalcMonth,CalcCal processStyle
    class SaveDay,SaveWeek,SaveMonth dbStyle
```

---

## 범례 (Legend)

- 🟢 **활성화된 단계**: 현재 코드에서 실행되는 부분
- 🟠 **비활성화된 단계**: 주석 처리되어 실행되지 않는 부분
- 🔵 **조건 분기**: if/else 등 조건에 따라 달라지는 흐름
- 🔴 **외부 의존성**: MongoDB, Ollama Server 등 외부 서비스
- 🟣 **데이터베이스**: MongoDB 컬렉션

---

이상으로 `main_collect_and_scrapping2.py`의 전체 흐름을 시각화했습니다.
