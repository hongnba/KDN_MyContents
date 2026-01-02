# 단일 URL Ollama 5개 프롬프트 분석 및 MongoDB 저장 가이드

## 📋 개요

**`main_collect_and_scrapping2.py`만 수정**하여 다음 작업을 한 번에 수행합니다:

1. ✅ URL을 `contents_queue`에 삽입
2. ✅ Ollama 서버 연결 확인
3. ✅ Trafilaura로 본문 스크래핑
4. ✅ Ollama 5개 프롬프트 실행
5. ✅ MongoDB `contents` 컬렉션에 저장

**나머지 파일은 수정하지 않고 기존 기능을 그대로 활용합니다.**

---

## 🚀 사용 방법

### 방법 1: 완전 자동 (가장 간단) ⭐

URL만 입력하면 기관/카테고리를 자동으로 추론합니다.

```bash
cd /home/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src/docker_shell

python3 main_collect_and_scrapping2.py \
  --single-url "https://www.motie.go.kr/kor/article/ATCL2826a2625/69968/view"
```

**실행 결과:**
```
✅ URL에서 기관 자동 추론: A0001
✅ URL에서 카테고리 자동 추론: B0001
=== 단일 URL 처리 모드 시작 ===
Step 1: URL을 contents_queue에 삽입
Step 2: Ollama 서버 연결 확인
Step 3: 스크래핑 및 Ollama 5개 프롬프트 분석 시작
  - Trafilaura로 본문 스크래핑
  - Prompt 1: 키워드 관련성 검증 (question_verify)
  - Prompt 2: 요약 생성 (question_summary)
  - Prompt 3: 감성 비율 분석 (question_sentiment_ratio)
  - Prompt 4: 감성 이유 설명 (sentiment_reason)
  - Prompt 5: 긍정/부정 키워드 추출 (sentiment_keywords)
Step 4: 처리 결과 확인
✅ 스크래핑 성공: 1건
✅ Ollama 분석 성공: 1건
=== 단일 URL 처리 완료 ===
```

---

### 방법 2: 기관/카테고리 직접 지정

자동 추론이 실패하거나 정확한 값을 지정하고 싶을 때:

```bash
python3 main_collect_and_scrapping2.py \
  --single-url "https://example.com/article" \
  --org "A0001" \
  --category "B0002"
```

---

## 🔄 전체 처리 과정 상세

### Step 1: URL을 contents_queue에 삽입

```python
# ContentsQueueVO 생성
queue_vo = ContentsQueueVO(
    _id=ObjectId(),
    url="https://www.motie.go.kr/...",
    contentOrgId="A0001",  # 산업통상자원부
    cateId="B0001",        # 보도자료
    title="수동 입력 기사",  # 스크래핑 시 자동 추출됨
    collectDt=datetime.utcnow()
)

# MongoDB에 삽입
queue_service.insert_queue(queue_vo)
```

**MongoDB 확인:**
```bash
docker exec -i ksubscribe_mongodb mongo mycontents --quiet --eval \
  'db.contents_queue.findOne({url: "https://www.motie.go.kr/..."})'
```

---

### Step 2: Ollama 서버 연결 확인

```python
# OllamaAlive 스레드 시작
checker = OllamaAlive(op_mode="docker_server", keep_alive=False)
checker.start_thread()
```

**확인 내용:**
- Ollama 서버 상태 체크 (http://10.99.2.71:11434)
- 모델 로드 확인 (llama-3-Korean-Bllossom-8B-Q4_K_M:latest)

---

### Step 3: 스크래핑 및 Ollama 5개 프롬프트 분석

```python
# ContentsScrapingOllamaTrafilaura 실행
scraper = ContentsScrapingOllamaTrafilaura()
scraper.crawl_and_analyze_ollama()
```

#### 3-1. Trafilaura로 본문 스크래핑

```python
# TrafilauraScraper 사용
isSuccess, title, text = trafilauraScraper.get_newbody(url)
```

**추출 정보:**
- 기사 제목 (title)
- 본문 텍스트 (text)
- 메타데이터 (작성일, 저자 등)

---

#### 3-2. Ollama 5개 프롬프트 순차 실행

```python
# AnalysisOllamaGenerateCall 실행
ollamaAnalysis = AnalysisOllamaGenerateCall()
isSuccess, contentsMetaResult, summary, sentiment, error = \
    ollamaAnalysis.analysis_main(
        queueContent=queueContent,
        title=title,
        content=text,
        pred_keyword_list=keyword_list,
        org_name_list=org_list,
        mycontents_logger=logger
    )
```

##### Prompt 1: 키워드 관련성 검증 (question_verify)

```
역할: 당신은 기사 분석 전문가입니다.

사용자 지시:
다음 기사가 주어진 키워드 목록과 관련이 있는지 판단하세요.
키워드: {pred_keyword_list}
기사 내용: {content}

출력 형식 (JSON):
{
  "ai_keyword": "가장 관련 있는 키워드",
  "related": true/false,
  "reason": "판단 이유"
}
```

**출력 예시:**
```json
{
  "ai_keyword": "인공지능",
  "related": true,
  "reason": "기사가 AI 기술 개발에 대한 내용을 포함하고 있습니다."
}
```

---

##### Prompt 2: 요약 생성 (question_summary)

```
역할: 당신은 기사 요약 전문가입니다.

사용자 지시:
다음 기사를 짧은 요약과 긴 요약으로 작성하세요.
제목: {title}
내용: {content}

출력 형식 (JSON):
{
  "short_summary": "한 문장 요약 (100자 이내)",
  "long_summary": "상세 요약 (300자 이내)"
}
```

**출력 예시:**
```json
{
  "short_summary": "산업부, AI 기술 개발에 500억 투자 발표",
  "long_summary": "산업통상자원부는 인공지능 기술 개발을 위해 500억원 규모의 지원 사업을 시작한다고 발표했다. 이번 사업은 중소기업과 스타트업을 중심으로 AI 핵심 기술 개발을 지원하며, 2025년까지 100개 기업을 선정할 계획이다."
}
```

---

##### Prompt 3: 감성 비율 분석 (question_sentiment_ratio)

```
역할: 당신은 감성 분석 전문가입니다.

사용자 지시:
다음 기관들에 대해 기사의 감성을 분석하세요.
기관: {org_name_list}
기사: {content}

출력 형식 (JSON):
{
  "sentiments": [
    {
      "orgName": "산업통상자원부",
      "positiveRatio": 80,
      "negativeRatio": 10,
      "neutralRatio": 10
    }
  ]
}
```

**출력 예시:**
```json
{
  "sentiments": [
    {
      "orgName": "산업통상자원부",
      "positiveRatio": 75,
      "negativeRatio": 5,
      "neutralRatio": 20
    },
    {
      "orgName": "과학기술정보통신부",
      "positiveRatio": 60,
      "negativeRatio": 10,
      "neutralRatio": 30
    }
  ]
}
```

---

##### Prompt 4: 감성 판단 이유 (sentiment_reason)

```
역할: 당신은 감성 분석 설명 전문가입니다.

사용자 지시:
왜 그렇게 감성 비율을 판단했는지 설명하세요.
기관: {org_name}
기사: {content}

출력 형식 (JSON):
{
  "reason": "전체 판단 이유",
  "positiveReason": "긍정 판단 근거",
  "negativeReason": "부정 판단 근거"
}
```

**출력 예시:**
```json
{
  "reason": "기사는 정부의 AI 투자 확대를 긍정적으로 다루고 있으나, 일부 기업의 우려도 언급됨",
  "positiveReason": "500억원 규모 투자, 중소기업 지원 확대, 일자리 창출 기대",
  "negativeReason": "선정 기준 불명확, 대기업 참여 제한에 대한 비판"
}
```

---

##### Prompt 5: 긍정/부정 키워드 추출 (sentiment_keywords)

```
역할: 당신은 키워드 추출 전문가입니다.

사용자 지시:
기사에서 긍정/부정 키워드를 추출하세요.
기사: {content}

출력 형식 (JSON):
{
  "positiveKeywords": ["투자", "지원", "성장"],
  "negativeKeywords": ["우려", "비판", "제한"]
}
```

**출력 예시:**
```json
{
  "positiveKeywords": ["투자 확대", "중소기업 지원", "기술 혁신", "일자리 창출"],
  "negativeKeywords": ["선정 기준 불명확", "대기업 배제", "실효성 의문"]
}
```

---

### Step 4: MongoDB contents 컬렉션에 저장

```python
# ContentsVO 생성 및 저장
contentsVO = ContentsVO(
    _id=ObjectId(),
    url=url,
    orgId=org_id,
    cateId=cate_id,
    title=title,
    collectDt=datetime.utcnow(),
    rawCollectSucYN="Y",
    metaSucYN="Y",
    contentsRaw=ContentsRaw(
        title=title,
        contents=text,
        collectDt=datetime.utcnow()
    ),
    contentsMeta=ContentsMeta(
        ai_keyword=result["ai_keyword"],
        related=result["related"],
        short_summary=result["short_summary"],
        long_summary=result["long_summary"],
        sentimentInfoList=[
            SentimentInfo(
                orgName="산업통상자원부",
                positiveRatio=75,
                negativeRatio=5,
                neutralRatio=20,
                reason="...",
                positiveKeywords=["투자", "지원"],
                negativeKeywords=["우려"]
            )
        ]
    )
)

BaseQueryService.insert_one(contentsVO)
```

---

## 📊 결과 확인 방법

### 방법 1: 로그 확인

```bash
# 처리 중 실시간 로그
tail -f /app/logs/docker_scraping_result.log
```

### 방법 2: MongoDB 직접 조회

```bash
# 저장된 데이터 확인
docker exec -i ksubscribe_mongodb mongo mycontents --quiet --eval \
  'db.contents.findOne({url: "https://www.motie.go.kr/..."})'
```

**조회 결과 예시:**
```json
{
  "_id": ObjectId("..."),
  "url": "https://www.motie.go.kr/...",
  "orgId": "A0001",
  "cateId": "B0001",
  "title": "산업부, AI 기술 개발에 500억 투자",
  "collectDt": ISODate("2025-11-11T..."),
  "rawCollectSucYN": "Y",
  "metaSucYN": "Y",
  "contentsRaw": {
    "title": "...",
    "contents": "전체 본문...",
    "collectDt": ISODate("...")
  },
  "contentsMeta": {
    "ai_keyword": "인공지능",
    "related": true,
    "short_summary": "산업부, AI 기술 개발에 500억 투자 발표",
    "long_summary": "산업통상자원부는...",
    "sentimentInfoList": [
      {
        "orgName": "산업통상자원부",
        "positiveRatio": 75,
        "negativeRatio": 5,
        "neutralRatio": 20,
        "reason": "...",
        "positiveReason": "...",
        "negativeReason": "...",
        "positiveKeywords": ["투자 확대", "지원"],
        "negativeKeywords": ["우려"]
      }
    ]
  }
}
```

### 방법 3: Python으로 조회

```python
from ksubscribe_share.db.service.contentsService import ContentsService

# URL로 검색
service = ContentsService()
content = service.findByUrl("https://www.motie.go.kr/...")

# 결과 출력
print(f"제목: {content.title}")
print(f"요약: {content.contentsMeta.short_summary}")
print(f"감성 비율: {content.contentsMeta.sentimentInfoList[0].positiveRatio}%")
```

---

## 🤖 자동 추론 규칙

### 기관 자동 추론 (URL 도메인 기반)

| URL 도메인 | 기관 ID | 기관명 |
|-----------|--------|--------|
| `motie.go.kr` | A0001 | 산업통상자원부 |
| `msit.go.kr` | A0003 | 과학기술정보통신부 |
| `pipc.go.kr` | A0002 | 개인정보보호위원회 |
| `g2b.go.kr` | A0004 | 나라장터 |
| `ketep.re.kr` | A0005 | 한국에너지기술평가원 |

### 카테고리 자동 추론 (URL 키워드 기반)

| URL 키워드 | 카테고리 ID | 카테고리명 |
|-----------|-----------|-----------|
| `news`, `press`, `보도`, `release` | B0001 | 보도자료 |
| `notice`, `announce`, `공고`, `bid` | B0002 | 사업공고 |
| `policy`, `정책` | B0003 | 정책자료 |
| (없음) | B0001 | 보도자료 (기본값) |

---

## ⚠️ 주의사항

### 1. 중복 URL 체크

이미 존재하는 URL은 자동으로 스킵됩니다:

```
⚠️  이미 contents에 존재하는 URL입니다: https://...
기존 데이터를 확인하려면 MongoDB에서 조회하세요:
  db.contents.findOne({url: "https://..."})
```

### 2. Ollama 서버 상태 확인

Ollama 서버가 실행 중이어야 합니다:

```bash
# Ollama 컨테이너 확인
docker ps | grep ollama

# Ollama 서버 상태 체크
curl http://10.99.2.71:11434/api/tags
```

### 3. 스크래핑 실패 시

일부 사이트는 스크래핑이 실패할 수 있습니다:
- 로그인 필요 페이지
- JavaScript 렌더링 필수 페이지
- 차단된 IP/User-Agent

**해결 방법:**
```bash
# 원문을 직접 복사하여 test_single_article.py 사용
python3 test_single_article.py \
  --text "기사 원문..." \
  --org "A0001" \
  --category "B0001"
```

---

## 📝 수정된 파일

### `main_collect_and_scrapping2.py` (유일하게 수정된 파일)

**추가된 기능:**
1. `process_single_url_mode()` 함수 - 단일 URL 처리
2. `auto_infer_org_from_url()` 함수 - 기관 자동 추론
3. `auto_infer_category_from_url()` 함수 - 카테고리 자동 추론
4. `argparse` 인자 파싱 추가
5. `--single-url` 모드 추가

**기존 기능 유지:**
- `--today-json` 모드
- 전체 파이프라인 모드 (기본)

---

## 🎯 활용되는 기존 코드 (수정 없음)

| 파일 | 역할 | 활용 방법 |
|------|------|----------|
| `ContentsScrapingOllamaTrafilaura` | 스크래핑 및 분석 | `crawl_and_analyze_ollama()` 호출 |
| `AnalysisOllamaGenerateCall` | Ollama 5개 프롬프트 실행 | `analysis_main()` 호출 |
| `TrafilauraScraper` | 본문 추출 | `get_newbody(url)` 호출 |
| `OllamaAlive` | Ollama 서버 상태 체크 | `start_thread()` 호출 |
| `ContentsQueueService` | Queue 관리 | `insert_queue()` 호출 |
| `ContentsService` | Contents 관리 | `isExistContents()` 호출 |
| `BaseQueryService` | MongoDB 저장 | `insert_one()` 호출 |

---

## 🚀 빠른 시작 예제

### 예제 1: 산업부 보도자료

```bash
cd /home/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src/docker_shell

python3 main_collect_and_scrapping2.py \
  --single-url "https://www.motie.go.kr/kor/article/ATCL2826a2625/69968/view"
```

### 예제 2: 과기정통부 공고

```bash
python3 main_collect_and_scrapping2.py \
  --single-url "https://www.msit.go.kr/bbs/view.do?sCode=notice&mId=99&mPid=74&nttSeqNo=1234567" \
  --category "B0002"
```

### 예제 3: 수동 지정

```bash
python3 main_collect_and_scrapping2.py \
  --single-url "https://example.com/article/123" \
  --org "A0001" \
  --category "B0001"
```

---

## 🔍 트러블슈팅

### 문제 1: "URL에서 기관을 추론할 수 없습니다"

**해결:**
```bash
# --org 옵션으로 직접 지정
python3 main_collect_and_scrapping2.py \
  --single-url "https://..." \
  --org "A0001"
```

### 문제 2: Ollama 연결 실패

**확인:**
```bash
# Ollama 컨테이너 상태
docker ps | grep ollama

# Ollama 재시작
docker restart ksubscribe_ollama
```

### 문제 3: 스크래핑 실패

**로그 확인:**
```bash
tail -f /app/logs/docker_scraping.log
```

**원인 분석:**
- 404 Not Found - URL 오류
- 403 Forbidden - 접근 차단
- Timeout - 서버 응답 없음

---

## 📚 추가 문서

- [Ollama_분석_프롬프트_상세.md](./Ollama_분석_프롬프트_상세.md) - 5개 프롬프트 상세 설명
- [test_single_article_사용법.md](./kSubscribe_Python_v2.0.0/src/docker_shell/test_single_article_사용법.md) - 원문 직접 입력 테스트
- [기관카테고리_자동추론_가이드.md](./기관카테고리_자동추론_가이드.md) - 자동 추론 규칙 상세

---

이상으로 **단일 URL만으로 Ollama 5개 프롬프트 분석 및 MongoDB 저장**까지 완료하는 가이드를 마칩니다.
