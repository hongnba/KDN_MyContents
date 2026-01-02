# Ollama 모델 분석 상세 - 프롬프트 및 직접 테스트 가이드

## 질문 1: 스크래핑/크롤링 없이 Ollama에 원문 기사를 입력할 수 있나요?

### 답변: **네, 가능합니다!**

코드 구조상 LLM 분석 로직은 독립적으로 분리되어 있어, 원문 텍스트만 있으면 Ollama 모델을 직접 호출할 수 있습니다.

### 방법 1: Python 코드로 직접 호출

```python
from ksubscribe_server.analysis.analysis_ollama_generate import AnalysisOllamaGenerateCall
from ksubscribe_share.logger import Logger
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO

# 1. 분석기 초기화
analyzer = AnalysisOllamaGenerateCall()
logger = Logger().setup_logger(Logger.docker_scraping_logger_name)

# 2. 테스트할 원문 기사 (직접 입력)
test_article = """
산업통상자원부는 2025년 산업통계 및 동향분석 기반사업의 보조사업자 선정을 재공고하였다. 
사업을 수행하고자 하는 기관은 지정된 절차에 따라 신청해야 한다. 
공고일은 2025년 1월 20일이다.
"""

# 3. 사전정의 키워드 목록 (DB에서 가져오는 대신 직접 지정)
pred_keywords = "데이터, 플랫폼, 에너지, 산업통계, 동향분석"

# 4. 기관 목록 (DB에서 가져오는 대신 직접 지정)
org_names = "산업통상자원부, 과학기술정보통신부, 환경부"

# 5. 큐 정보 생성 (메타데이터용 - 실제 큐에 없어도 됨)
queue_content = ContentsQueueVO()
queue_content.contentOrgId = "A0001"
queue_content.url = "https://example.com/test"

# 6. Ollama 분석 실행
success, result, summary, sentiment, error = analyzer.analysis_main(
    content=test_article,
    pred_keyword_list=pred_keywords,
    org_name_list=org_names,
    mycontents_logger=logger,
    queueContent=queue_content
)

# 7. 결과 출력
if success:
    print("=== 분석 성공 ===")
    print(f"키워드: {result.contentsMeta.keywords}")
    print(f"짧은 요약: {result.contentsMeta.shortSummary}")
    print(f"긴 요약: {result.contentsMeta.longSummary}")
    print(f"감성 분석: {result.contentsMeta.sentiments}")
else:
    print("=== 분석 실패 ===")
    print(f"오류: {error}")
```

### 방법 2: Ollama Client 직접 사용 (저수준)

```python
from langchain_ollama import ChatOllama
import ksubscribe_share.config as CONF
import json

# Ollama 클라이언트 초기화
chat_ollama = ChatOllama(
    model=CONF.OLLAMA_MODEL,
    base_url=CONF.OLLAMA_URL,
    format="json"
)

# 원문 기사
article_text = "여기에 기사 원문을 넣으세요..."

# 프롬프트 구성 (예: 요약)
prompt = f"""
contents : {article_text}
위의 기사를 분석하여 아래 형식에 맞춰 JSON 객체로 응답해줘:
{{
    "short_summary": "한줄 기사 요약",
    "long_summary": "5줄 이상으로 기사 요약"
}}
"""

# Ollama 호출
result = chat_ollama._client.generate(
    model=CONF.OLLAMA_MODEL,
    prompt=prompt,
    format="json"
)

# 결과 파싱
response_json = json.loads(result.response)
print(f"짧은 요약: {response_json['short_summary']}")
print(f"긴 요약: {response_json['long_summary']}")
```

### 방법 3: REST API로 직접 호출 (curl/Python requests)

```bash
# Ollama API 직접 호출 (스크래핑 없이)
curl -X POST http://10.99.2.71:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-3-Korean-Bllossom-8B-Q4_K_M:latest",
    "prompt": "다음 기사를 요약해줘: [기사 원문...]",
    "format": "json",
    "stream": false
  }'
```

---

## 질문 2: Ollama 모델에게 주어지는 프롬프트(요청)는 무엇인가요?

### 답변: **총 5개의 프롬프트가 순차적으로 실행됩니다**

현재 코드(`analysis_ollama_generate.py`)에서는 한 기사당 **최소 4~5회** Ollama를 호출합니다.

---

## 📋 프롬프트 상세 분석

### 프롬프트 1: `question_verify` - **키워드 관련성 사전 검증**

**목적**: 기사가 DB의 사전정의 키워드와 관련이 있는지 사전 검증

**입력**:
- `[contents]`: 기사 원문
- `[pred_keywords_from_db]`: DB에 저장된 사전정의 키워드 목록 (예: "데이터, 플랫폼, 에너지")

**프롬프트 전문**:
```
[Step 1] 다음 기사(contents)와 db_keyword_list를 제공합니다.
- contents: [기사 원문]
- db_keyword_list: [데이터, 플랫폼, 에너지, ...]

[Step 2] 아래 요구사항에 따라 JSON 객체로만 답변해 주세요.

JSON 형식:
{
    "ai_keyword": 기사에서 주요 이슈/주제를 추출한 핵심 키워드 리스트,
    "db_keyword_list": 제공한 db_keyword_list를 그대로,
    "related": ai_keyword와 db_keyword_list를 비교하여 1개 이상 관련 있으면 true, 없으면 false,
    "reason": related가 true일 경우, db_keyword_list 안에서 관련된 최대 10개 키워드 선택
}
```

**출력 예시**:
```json
{
    "ai_keyword": ["산업통계", "동향분석", "보조사업"],
    "db_keyword_list": ["데이터", "플랫폼", "에너지", "산업통계", "동향분석"],
    "related": true,
    "reason": ["산업통계", "동향분석"]
}
```

**코드 위치**:
- `analysis_ollama_generate.py`, 라인 105-112
- 실행: `result_verify = self.chat_ollama._client.generate(...)`

---

### 프롬프트 2: `question_summary` - **기사 요약 및 키워드 추출**

**목적**: 기사의 짧은/긴 요약 생성

**입력**:
- `[contents]`: 기사 원문
- `[organization]`: 관련 기관명 (예: "산업통상자원부")

**프롬프트 전문**:
```
contents : [기사 원문]
organization : [산업통상자원부]

위의 기사를 분석하여 아래 형식에 맞춰 JSON 객체로 응답해줘 (\n, \r\n, \t 제거).
JSON 객체의 구조는 다음과 같아:
{
    "short_summary": "한줄 기사 요약",
    "long_summary": "5줄 이상으로 기사 요약. organization을 중심으로 요약해줘."
}
```

**출력 예시**:
```json
{
    "short_summary": "산업통상자원부가 산업통계 기반사업 보조사업자를 재공고했다.",
    "long_summary": "산업통상자원부는 2025년 산업통계 및 동향분석 기반사업의 보조사업자 선정을 재공고했다. 사업 수행을 희망하는 기관은 정해진 절차에 따라 신청해야 하며, 공고일은 2025년 1월 20일이다. 이번 재공고는 산업 데이터 분석 역량 강화를 목표로 하고 있다."
}
```

**코드 위치**:
- `analysis_ollama_generate.py`, 라인 124-131
- 실행: `result_summary = self.chat_ollama._client.generate(...)`

---

### 프롬프트 3-1: `question_sentiment_ratio` - **감성 비율 분석**

**목적**: 기사가 특정 기관에 대해 긍정/부정/중립 비율 추정

**입력**:
- `[contents]`: 기사 원문
- `[organization]`: 대상 기관명
- `[synonyms]`: 기관 별칭/약어 (예: "산업부, MOTIE")

**프롬프트 전문**:
```
기사 : [기사 원문]
기관 : [산업통상자원부] (이 기관은 [산업부, MOTIE]로도 불립니다.)

위 기사에서 해당 기관 또는 그 별칭([synonyms])이 언급된 부분을 중심으로 감성 분석을 수행해 줘.
기관에 대한 언급 중 긍정 / 부정 / 중립의 비율을 추정해서 아래 JSON 형식으로만 답변해.

{
    "positiveRatio": "긍정 비율 (0~100, float, % 기호 없이)",
    "neutralRatio": "중립 비율 (0~100, float, % 기호 없이)",
    "negativeRatio": "부정 비율 (0~100, float, % 기호 없이)"
}

세 비율의 합은 100이 되어야 해. 주석이나 설명은 넣지 마.
```

**출력 예시**:
```json
{
    "positiveRatio": 70.0,
    "neutralRatio": 20.0,
    "negativeRatio": 10.0
}
```

**코드 위치**:
- `analysis_ollama_generate.py`, 라인 210-213
- 실행: `result_sentiment_ratio = self.chat_ollama._client.generate(...)`

---

### 프롬프트 3-2: `sentiment_reason` - **감성 판단 이유 설명**

**목적**: 위에서 계산한 긍정/부정 비율의 근거 설명

**입력**:
- `[contents]`: 기사 원문
- `[organization]`: 대상 기관명
- `[synonyms]`: 기관 별칭
- `[positiveRatio]`: 3-1에서 계산한 긍정 비율
- `[negativeRatio]`: 3-1에서 계산한 부정 비율

**프롬프트 전문**:
```
기사 : [기사 원문]
기관 : [산업통상자원부] (이 기관은 [산업부, MOTIE]로도 불립니다.)

해당 기관을 대상으로 기사를 분석된 감성 비율은 다음과 같아:
    - 긍정: [70.0]
    - 부정: [10.0]

이 비율을 판단한 이유와 주요 키워드를 작성해줘.
출력은 아래 JSON 형식으로 해.

{
    "reason": "긍정과 부정 비율을 종합적으로 판단한 근거 (한 문단)",
    "positiveReason": "긍정 비율 판단 근거 (문장 형식)",
    "negativeReason": "부정 비율 판단 근거 (문장 형식)"
}
```

**출력 예시**:
```json
{
    "reason": "산업통상자원부가 사업자 선정을 재공고한 점은 투명성과 공정성을 강화하려는 긍정적 노력으로 해석된다.",
    "positiveReason": "재공고를 통해 더 많은 기관에 참여 기회를 제공하고 있다.",
    "negativeRatio": "일부 일정 지연 가능성이 언급되었다."
}
```

**코드 위치**:
- `analysis_ollama_generate.py`, 라인 226-231
- 실행: `result_sentiment_reason = self.chat_ollama._client.generate(...)`

---

### 프롬프트 3-3: `sentiment_keywords` - **긍정/부정 키워드 추출**

**목적**: 기관 평판에 영향을 주는 긍정/부정 키워드 추출

**입력**:
- `[contents]`: 기사 원문
- `[organization]`: 대상 기관명
- `[synonyms]`: 기관 별칭
- `[positiveRatio]`, `[negativeRatio]`: 3-1에서 계산한 비율

**프롬프트 전문**:
```
기사 : [기사 원문]
기관 : [산업통상자원부] (이 기관은 [산업부, MOTIE]로도 불립니다.)

이 기사는 여러 주제를 다룰 수 있지만, 
**오직 해당 기관([organization])의 이미지, 평판, 또는 대중 인식에 영향을 미치는 내용만** 분석해 줘.

기관과 직접적으로 관련된 **긍정적인 요인**과 **부정적인 요인**을 찾아 아래 JSON 형식으로 정리해 줘.
단순한 단어나 기사 전반의 키워드가 아니라, 
기관의 평판(이미지)에 영향을 주는 문맥 있는 표현을 뽑아야 해. 
(예: "기술 혁신", "성과 향상", "비리 의혹", "경영 악화" 등)

{
    "positiveKeywords": ["긍정 키워드1", "긍정 키워드2", "긍정 키워드3"],
    "negativeKeywords": ["부정 키워드1", "부정 키워드2", "부정 키워드3"]
}

출력 시:
- JSON만 출력해. 
- 주석, 설명, 문장형 해석은 절대 넣지 마.
```

**출력 예시**:
```json
{
    "positiveKeywords": ["사업자 선정", "투명성 강화", "공정한 절차"],
    "negativeKeywords": ["재공고", "일정 지연", "혼란 가중"]
}
```

**코드 위치**:
- `analysis_ollama_generate.py`, 라인 243-249
- 실행: `result_sentiment_keywords = self.chat_ollama._client.generate(...)`

---

## 📊 실행 순서 및 흐름

```
┌─────────────────────────────────────────────────────────┐
│ 1단계: 키워드 관련성 검증 (question_verify)              │
│  입력: 기사 원문 + DB 키워드 목록                        │
│  출력: ai_keyword, related(true/false), reason           │
│  → related=false면 키워드 추출 스킵                      │
└──────────────────┬──────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────┐
│ 2단계: 요약 생성 (question_summary)                      │
│  입력: 기사 원문 + 기관명                                │
│  출력: short_summary, long_summary                       │
│  → MongoDB contents.contentsMeta에 저장                  │
└──────────────────┬──────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────┐
│ 3-1단계: 감성 비율 (question_sentiment_ratio)            │
│  입력: 기사 원문 + 기관명 + 별칭                         │
│  출력: positiveRatio, negativeRatio, neutralRatio        │
└──────────────────┬──────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────┐
│ 3-2단계: 감성 이유 (sentiment_reason)                    │
│  입력: 기사 원문 + 기관 + 3-1의 비율                     │
│  출력: reason, positiveReason, negativeReason            │
└──────────────────┬──────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────┐
│ 3-3단계: 감성 키워드 (sentiment_keywords)                │
│  입력: 기사 원문 + 기관 + 3-1의 비율                     │
│  출력: positiveKeywords[], negativeKeywords[]            │
│  → MongoDB contents.contentsMeta.sentiments에 저장       │
└─────────────────────────────────────────────────────────┘
```

---

## 🔍 코드에서 실제 호출 위치

| 단계 | 프롬프트 변수명 | 호출 라인 | 결과 변수 | 용도 |
|------|----------------|-----------|-----------|------|
| 1 | `question_verify` | 107 | `result_verify` | 키워드 관련성 검증 |
| 2 | `question_summary` | 127 | `result_summary` | 요약 생성 |
| 3-1 | `question_sentiment_ratio` | 210 | `result_sentiment_ratio` | 감성 비율 |
| 3-2 | `sentiment_reason` | 228 | `result_sentiment_reason` | 감성 이유 |
| 3-3 | `sentiment_keywords` | 245 | `result_sentiment_keywords` | 감성 키워드 |

### 파일 경로
- 프롬프트 정의: `/src/ksubscribe_server/analysis/analysis_ollama_base.py` (라인 122-260)
- 실행 로직: `/src/ksubscribe_server/analysis/analysis_ollama_generate.py` (라인 96-260)

---

## ⚙️ 환경 설정 (CONF 값)

코드에서 사용하는 Ollama 설정:
```python
# ksubscribe_share/config.py
OLLAMA_URL = "http://10.99.2.71:11434"
OLLAMA_MODEL = "llama-3-Korean-Bllossom-8B-Q4_K_M:latest"
```

---

## 💡 직접 테스트하기 (간단한 예제)

### 최소 코드로 Ollama 요약만 실행

```python
from langchain_ollama import ChatOllama
import json

# 1. Ollama 클라이언트 설정
client = ChatOllama(
    model="llama-3-Korean-Bllossom-8B-Q4_K_M:latest",
    base_url="http://10.99.2.71:11434",
    format="json"
)

# 2. 테스트 기사
article = """
산업통상자원부는 2025년 산업통계 및 동향분석 기반사업의 보조사업자 선정을 재공고하였다. 
사업을 수행하고자 하는 기관은 지정된 절차에 따라 신청해야 한다.
"""

# 3. 요약 프롬프트
prompt = f"""
contents : {article}
위의 기사를 분석하여 아래 형식에 맞춰 JSON 객체로 응답해줘:
{{
    "short_summary": "한줄 기사 요약",
    "long_summary": "5줄 이상으로 기사 요약"
}}
"""

# 4. Ollama 호출
result = client._client.generate(
    model="llama-3-Korean-Bllossom-8B-Q4_K_M:latest",
    prompt=prompt,
    format="json"
)

# 5. 결과 출력
response = json.loads(result.response)
print("짧은 요약:", response['short_summary'])
print("긴 요약:", response['long_summary'])
```

---

## 📌 요약

### 질문 1 답변
- ✅ **스크래핑/크롤링 없이 Ollama에 원문 기사를 직접 입력 가능합니다.**
- 방법: `AnalysisOllamaGenerateCall.analysis_main()` 메서드에 텍스트를 직접 전달하거나, Ollama Client를 직접 사용.

### 질문 2 답변
- ✅ **총 5개의 프롬프트가 순차적으로 Ollama에 전달됩니다:**
  1. **키워드 검증** (`question_verify`)
  2. **요약 생성** (`question_summary`)
  3. **감성 비율** (`question_sentiment_ratio`)
  4. **감성 이유** (`sentiment_reason`)
  5. **감성 키워드** (`sentiment_keywords`)

- 각 프롬프트는 독립적으로 실행되며, 이전 단계의 결과를 다음 단계의 입력으로 사용합니다 (특히 3-2, 3-3은 3-1의 비율 결과를 사용).

---

이상으로 Ollama 분석 프롬프트 상세 설명을 마칩니다.
