# test_llm_evaluation.py 사용 가이드

## 📋 개요

`test_llm_evaluation.py`는 특정 문서들로 LLM 모델을 평가하고 비교하는 테스트 스크립트입니다.

### 주요 기능
- 특정 ObjectId 목록으로 LLM 평가 실행
- 텍스트 파일 또는 커맨드 라인에서 ID 입력 지원
- 여러 LLM 모델 비교 테스트
- 결과 스냅샷 자동 저장 (모델명_날짜_시간.json)
- Queue 유지 모드로 재실행 가능
- JSON 파일로 프롬프트를 안전하게 덮어쓰고 테스트

### ⚠️ 분석 파이프라인 버전 주의
현재 이 스크립트는 `ContentsScrapingOllamaTrafilaura` 클래스를 사용하여 분석을 수행합니다.
해당 클래스는 기본적으로 **Legacy 5-step 분석**(`analysis_main`)을 호출하도록 설정되어 있습니다.
최신 **3-step 통합 분석**(`analysis_main_3step`)을 테스트하려면 `ContentsScrapingOllamaTrafilaura` 코드를 수정하거나, 이 테스트 스크립트에서 호출 방식을 변경해야 합니다.

---

## 🚀 빠른 시작

> ⚠️ `--test-ids`와 `--ollama-model`은 둘 다 **필수**입니다. 생략하면 argparse 단계에서 바로 종료됩니다.

### 1. 추천: 테스트 ID 파일 사용

```bash
docker exec ksubscribe_python_unified python3 /app/ksubscribe_share/test/test_llm_evaluation.py \
  --test-ids /app/ksubscribe_share/test/test_ids.txt \
  --ollama-model llama-3-Korean-Bllossom-8B-Q4_K_M:latest
```

`test_ids.txt`는 상대/절대 경로 모두 지원합니다. 파일이 상대 경로면 스크립트 위치(`/app/ksubscribe_share/test/`) 기준으로 자동 탐색한 뒤 로드합니다.

### 2. 커맨드 라인에서 직접 ID 입력

```bash
docker exec ksubscribe_python_unified python3 /app/ksubscribe_share/test/test_llm_evaluation.py \
  --test-ids "68edc849ae3da00bfe2d0cef,68edc849ae3da00bfe2d0cf3,68edc84aae3da00bfe2d0cf7" \
  --ollama-model gpt-oss:20b
```

**test_ids.txt 파일 형식:**
```
# 주석은 # 으로 시작
68edc849ae3da00bfe2d0cef
68edc849ae3da00bfe2d0cf3
68edc84aae3da00bfe2d0cf7

# 빈 줄은 무시됨
```

---

## 📝 명령어 옵션

### 필수 옵션

#### `--test-ids IDS`
- 테스트할 문서 ID 지정 (파일 경로 또는 쉼표 구분 목록)
- 상대경로를 주면 스크립트 경로 기준으로 자동 탐색 후 로드
- 파일에 있는 ID는 주석/빈 줄을 무시하고 ObjectId 여부를 검증

#### `--ollama-model MODEL`
- 사용할 Ollama 모델 지정
- 예시: `llama-3-Korean-Bllossom-8B-Q4_K_M:latest`, `gpt-oss:20b`, `exaone-3.5:latest`

### 선택 옵션

#### `--keep-queue`
- 처리 후에도 contents_queue에서 문서를 삭제하지 않음
- 같은 문서로 여러 모델을 테스트할 때 유용
- 기본값: False (처리 후 Queue에서 삭제)

```bash
docker exec ksubscribe_python_unified python3 /app/ksubscribe_share/test/test_llm_evaluation.py \
  --ollama-model llama-3-Korean-Bllossom-8B-Q4_K_M:latest \
  --keep-queue
```

#### `--verbose` 또는 `-v`
- 상세 로그 출력 (MongoDB 결과 포함)
- 요약, 감성 분석 결과 등을 실시간으로 확인

```bash
docker exec ksubscribe_python_unified python3 /app/ksubscribe_share/test/test_llm_evaluation.py \
  --ollama-model gpt-oss:20b \
  --verbose
```

#### `--save-json FILE`
- 평가 결과를 JSON 파일로 저장
- 파일명 지정 가능 (생략 시 모델명+타임스탬프 자동 생성)
- 저장 시 절대경로로 변환해 출력하므로 컨테이너 안/밖 어디에서든 바로 경로를 복사할 수 있음

```bash
docker exec ksubscribe_python_unified python3 /app/ksubscribe_share/test/test_llm_evaluation.py \
  --ollama-model gpt-oss:20b \
  --save-json gpt_results.json
```

#### `--dump-raw [DIR]`
- 원문 텍스트 덤프
- 인자 생략 시: 콘솔 출력 + `test/outputs` 폴더에 저장
- `stdout` 지정 시: 콘솔 출력만
- 경로 지정 시: 해당 경로에 저장

```bash
# 기본 outputs 폴더에 저장
docker exec ksubscribe_python_unified python3 /app/ksubscribe_share/test/test_llm_evaluation.py \
  --ollama-model gpt-oss:20b \
  --dump-raw

# 콘솔 출력만
docker exec ksubscribe_python_unified python3 /app/ksubscribe_share/test/test_llm_evaluation.py \
  --ollama-model gpt-oss:20b \
  --dump-raw stdout

# 특정 경로에 저장
docker exec ksubscribe_python_unified python3 /app/ksubscribe_share/test/test_llm_evaluation.py \
  --ollama-model gpt-oss:20b \
  --dump-raw /app/my_dumps
```

#### `--prompt-overrides FILE`
- 테스트할 프롬프트를 JSON 파일에서 불러와 일시적으로 덮어씀
- 파일 형식: `{"question_summary": "...", "question_sentiment_ratio": "..."}`
- 지정하지 않으면 기본 코드 프롬프트 사용

```json
{
  "question_summary": "contents : [contents]\norganization : [organization]\n...",
  "question_sentiment_ratio": "기사 : [contents]\n기관 : [organization]\n..."
}
```

```bash
docker exec ksubscribe_python_unified python3 /app/ksubscribe_share/test/test_llm_evaluation.py \
  --ollama-model gpt-oss:20b \
  --prompt-overrides /app/ksubscribe_share/test/prompts/alt_summary.json
```

> ℹ️ JSON에 정의한 키만 교체되며, 나머지는 기본 프롬프트가 유지됩니다. 파일 수정만으로 여러 버전을 빠르게 비교할 수 있습니다.

### 자동 GPU 상태 로그
- 스크립트는 실행 직전과 종료 직후 `nvidia-smi`를 호출해 GPU 메모리 사용량을 기록합니다.
- 로그 예시: `[GPU] 테스트 시작 직전 GPU 상태: 모델이 올라간 것으로 감지 (GPU0:1250MB, GPU1:30MB ...)`
- 테스트 후 “모델이 올라갔다가 내려갔는지” 여부를 자동으로 요약하므로 별도 명령 없이 GPU 점유 추이를 확인할 수 있습니다.

---

## 🔄 여러 모델 비교 테스트

### 시나리오: Llama vs GPT-OSS 비교

```bash
# 1단계: Llama 모델로 테스트 (Queue 유지)
docker exec ksubscribe_python_unified python3 /app/ksubscribe_share/test/test_llm_evaluation.py \
  --ollama-model llama-3-Korean-Bllossom-8B-Q4_K_M:latest \
  --keep-queue

# 2단계: 같은 문서로 GPT-OSS 테스트
docker exec ksubscribe_python_unified python3 /app/ksubscribe_share/test/test_llm_evaluation.py \
  --ollama-model gpt-oss:20b \
  --keep-queue

# 3단계: 결과 비교
ls -l /app/ksubscribe_share/test/result/
```

**결과 파일 예시:**
```
llama-3-Korean-Bllossom-8B-Q4_K_M-latest_20251119_090001.json
gpt-oss-20b_20251119_091523.json
```

---

## 📊 출력 결과 이해하기

### 1. 실행 시작 로그
```
🚀 LLM 모델 평가 테스트 시작
실행 시각: 2025-11-19 09:00:01
옵션:
  - Queue 유지: False
  - 상세 로그: False
  - JSON 저장: No
  - 원문 덤프: No
✅ 테스트 대상: 3개 문서
```

### 2. 문서 조회 결과
```
📋 mycontents.contents_queue에서 문서 조회 중...
  ✅ 68edc849... - "이게 8천 원이라고요? 심했다"…한국전력 '부실 급식' 논란
  ✅ 68edc849... - 한국전력, 5년간 안전·환경 법령 110건 위반
  ✅ 68edc84a... - 한국전력-한수원, 368억원 소송전
```

### 3. 개별 문서 처리
```
[1/3] 처리 중
ID: 68edc849ae3da00bfe2d0cef
URL: https://news.kbs.co.kr/news/pc/view/view.do?ncd=8379101
제목: "이게 8천 원이라고요? 심했다"…한국전력 '부실 급식' 논란
✅ 처리 완료 (소요 시간: 10.2초)
```

### 4. 저장 상태 확인
```
📂 저장 상태:
  - DB(contents): 없음
  - Queue(contents_queue): 있음
  - Export 파일: /app/exports/llama-3-Korean-Bllossom-8B-Q4_K_M-latest_content_20251119_085709.json
```

### 5. 최종 요약
```
📊 LLM 평가 결과 요약
총 문서 수: 3개
  ✅ 성공: 3개
  ❌ 실패: 0개

처리 시간:
  총 시간: 32.1초
  평균 시간: 10.7초/문서

Scraper 통계:
  스크래핑 성공: 3개
  LLM 분석 성공: 2개
```

### 6. 스냅샷 저장
```
💾 contents 최신 3건 스냅샷 저장: /app/ksubscribe_share/test/result/llama-3-Korean-Bllossom-8B-Q4_K_M-latest_20251119_090001.json
📍 스냅샷 JSON 절대경로: /app/ksubscribe_share/test/result/llama-3-Korean-Bllossom-8B-Q4_K_M-latest_20251119_090001.json
```

### 7. GPU 상태 로그
```
[GPU] 테스트 시작 직전 GPU 상태: GPU 점유 없음 (GPU0:30MB, GPU1:28MB)
[GPU] 테스트 완료 후 GPU 상태: 모델이 올라간 것으로 감지 (GPU0:1280MB, GPU1:32MB)
[GPU] 모델이 테스트 중 GPU에 올라갔다가 종료 후 내려갔습니다.
```

---

## 📁 출력 파일 구조

### 스냅샷 JSON 파일 구조
```json
{
  "meta": {
    "created_at": "2025-11-19T09:00:01.396099",
    "model": "llama-3-Korean-Bllossom-8B-Q4_K_M:latest",
    "count": 3
  },
  "docs": [
    {
      "_id": "691d8705a3ec965f618db40b",
      "title": "한국전력-한수원, 368억원 소송전…",
      "url": "https://www.gokorea.kr/news/articleView.html?idxno=842077",
      "contentsOrgId": "A0010",
      "categoryId": "B0010",
      "contentsMeta": {
        "keywords": ["원자력", "한국전력", "공사비"],
        "shortSummary": "...",
        "longSummary": "...",
        "sentiments": [...]
      },
      "metaAnalyzeDt": "2025-11-19T09:00:01.215000"
    }
  ]
}
```

---

## 🔍 MongoDB에서 결과 확인

스크립트 실행 후 MongoDB에서 직접 확인하는 방법:

```bash
# 1. MongoDB 컨테이너 접속
docker exec -it ksubscribe_mongodb mongosh mycontents

# 2. 처리된 문서 조회
db.contents.find({
  _id: { $in: [
    ObjectId("68edc849ae3da00bfe2d0cef"),
    ObjectId("68edc849ae3da00bfe2d0cf3"),
    ObjectId("68edc84aae3da00bfe2d0cf7")
  ]}
}).pretty()

# 3. 요약만 확인
db.contents.find({
  _id: { $in: [
    ObjectId("68edc849ae3da00bfe2d0cef")
  ]}
}, {
  title: 1,
  'contentsMeta.shortSummary': 1,
  'contentsMeta.longSummary': 1,
  'contentsMeta.sentiments': 1
}).pretty()
```

---

## ⚙️ 기본 설정 커스터마이징

- 기본 하드코딩 ID(`DEFAULT_TEST_IDS`)는 더 이상 자동으로 사용되지 않습니다. 기존과 똑같은 세트를 쓰고 싶다면 위 ID를 `--test-ids` 인자에 직접 넘기거나 파일에 적어 호출하세요.

---

## 🐛 문제 해결

### 문제 1: Queue에 문서가 없음
```
❌ Queue에서 문서를 찾을 수 없습니다.
```

**해결책:**
```bash
# 먼저 수집을 실행
docker exec ksubscribe_python_unified python3 /app/docker_shell/main_collect_and_scrapping.py
```

### 문제 2: Ollama 서버 연결 실패
```
❌ Ollama 서버에 연결할 수 없습니다.
```

**해결책:**
```bash
# Ollama 컨테이너 상태 확인
docker ps | grep ollama

# Ollama 컨테이너 재시작
docker restart ksubscribe_ollama
```

### 문제 3: LLM 분석 실패 (JSON 파싱 오류)
```
ERROR - Expecting ',' delimiter: line 1 column 256
```

**원인:** GPT 모델이 JSON이 아닌 일반 텍스트로 응답

**해결책:** 스크립트가 자동으로 처리 (`format=None` 설정)
```python
# GPT 모델일 경우 format 제거 (JSON 포맷이 답변을 방해할 수 있음)
if 'gpt' in os.environ.get('OLLAMA_MODEL', '').lower():
    ollamaAnalysis.chat_ollama.format = None
```

---

## 💡 활용 팁

### 1. 배치 테스트 스크립트 작성

```bash
#!/bin/bash
# test_all_models.sh

MODELS=(
  "llama-3-Korean-Bllossom-8B-Q4_K_M:latest"
  "gpt-oss:20b"
  "exaone-3.5:latest"
)

for MODEL in "${MODELS[@]}"; do
  echo "Testing with $MODEL..."
  docker exec ksubscribe_python_unified python3 /app/ksubscribe_share/test/test_llm_evaluation.py \
    --ollama-model "$MODEL" \
    --keep-queue
  echo "Completed: $MODEL"
  echo "---"
done
```

### 2. 결과 파일 비교

```bash
# 모든 스냅샷 파일 확인
docker exec ksubscribe_python_unified ls -lh /app/ksubscribe_share/test/result/

# 특정 모델 결과 확인
docker exec ksubscribe_python_unified cat /app/ksubscribe_share/test/result/gpt-oss-20b_*.json | jq '.meta'
```

### 3. 성능 비교 분석

```bash
# 각 모델의 처리 시간 비교
docker exec ksubscribe_python_unified cat /app/ksubscribe_share/test/result/*.json | \
  jq -r '.meta | "\(.model): \(.count)개 문서"'
```

---

## 📚 관련 문서

- [Ollama 분석 사용법](../OLLAMA_분석_사용법.md)
- [단일 URL Ollama 분석 가이드](../단일URL_Ollama분석_가이드.md)
- [파이프라인 실행 후 결과 조회 가이드](./파이프라인_실행_후_결과조회_가이드.md)

---

## 📅 업데이트 이력

- **2025-12-01**: 최신 스크립트 반영
  - `--test-ids` / `--ollama-model` 필수화 및 상대경로 자동 인식 설명 추가
  - GPU 상태 자동 로깅 및 결과 JSON 절대경로 출력 기능 문서화
- **2025-11-19**: 초안 작성
  - 기본 사용법 문서화
  - 모델 비교 테스트 시나리오 추가
  - 스냅샷 파일명에 모델 이름 포함 기능
  - DEFAULT_TEST_IDS 하드코딩 기능
