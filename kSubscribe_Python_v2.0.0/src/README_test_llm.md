# LLM 평가 테스트 스크립트 사용 가이드

## 📋 개요

`test_llm_evaluation.py`는 특정 문서들로 LLM 모델을 평가하기 위한 독립 테스트 스크립트입니다.

- **목적**: contents_queue의 특정 문서만 선택하여 Ollama LLM 분석 평가
- **특징**: 프로덕션 코드 수정 없이 독립 실행
- **장점**: 재시도/통계 계산 건너뛰어 빠른 테스트 가능

---

## 🚀 빠른 시작

### 1. 기본 3개 문서로 평가 (가장 간단)

```bash
cd /home/themiraclesoft/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src
python3 test_llm_evaluation.py
```

→ 하드코딩된 3개 문서 ID로 자동 실행

---

### 2. 파일에서 ID 목록 읽기 (권장)

**Step 1**: ID 목록 파일 작성
```bash
cp test_ids.example.txt test_ids.txt
nano test_ids.txt
```

**test_ids.txt 예시**:
```
# 평가할 문서 ID 목록
68edc849ae3da00bfe2d0cef
68edc849ae3da00bfe2d0cf3
68edc84aae3da00bfe2d0cf7
```

**Step 2**: 실행
```bash
python3 test_llm_evaluation.py --test-ids test_ids.txt
```

---

### 3. 커맨드 라인에서 직접 입력

```bash
python3 test_llm_evaluation.py --test-ids "68edc849ae3da00bfe2d0cef,68edc849ae3da00bfe2d0cf3"
```

---

## 🔧 고급 옵션

### Queue 유지 모드 (재실행 가능)

처리 후에도 contents_queue에서 문서를 삭제하지 않음:
```bash
python3 test_llm_evaluation.py --test-ids test_ids.txt --keep-queue
```

**용도**:
- 같은 문서로 반복 테스트 (다른 모델 비교 등)
- Queue 데이터 보존 필요 시

---

### 상세 로그 모드

MongoDB 저장 결과까지 출력:
```bash
python3 test_llm_evaluation.py --test-ids test_ids.txt --verbose
```

**출력 예시**:
```
✅ 처리 완료 (소요 시간: 12.3초)
📊 요약: 산업통상자원부는 AI 기술 발전을 위한 새로운 정책을 발표했다...
📈 감성 비율: 긍정 70.0%
```

---

### 결과를 JSON 파일로 저장

```bash
python3 test_llm_evaluation.py --test-ids test_ids.txt --save-json results.json
```

**results.json 예시**:
```json
[
  {
    "id": "68edc849ae3da00bfe2d0cef",
    "url": "https://...",
    "success": true,
    "elapsed": 12.3
  },
  {
    "id": "68edc849ae3da00bfe2d0cf3",
    "url": "https://...",
    "success": true,
    "elapsed": 10.8
  }
]
```

---

### 모든 옵션 조합

```bash
python3 test_llm_evaluation.py \
  --test-ids test_ids.txt \
  --keep-queue \
  --verbose \
  --save-json evaluation_20251118.json
```

---

## 📊 출력 결과 해석

### 실행 중 로그

```
================================================================================
🚀 LLM 모델 평가 테스트 시작
================================================================================
실행 시각: 2025-11-18 14:30:00
옵션:
  - Queue 유지: False
  - 상세 로그: False
  - JSON 저장: No
✅ 테스트 대상: 3개 문서

📋 contents_queue에서 문서 조회 중...
  ✅ 68edc849... - 산업통상자원부, AI 기술 발전 정책 발표
  ✅ 68edc849... - 개인정보보호위원회, 데이터 보호 강화
  ✅ 68edc84a... - 과학기술정보통신부, 5G 네트워크 확대

총 3개 문서 처리 시작

================================================================================
[1/3] 처리 중
ID: 68edc849ae3da00bfe2d0cef
URL: https://example.com/news/123
제목: 산업통상자원부, AI 기술 발전 정책 발표
================================================================================
✅ 처리 완료 (소요 시간: 12.3초)
```

---

### 최종 요약

```
================================================================================
📊 LLM 평가 결과 요약
================================================================================
총 문서 수: 3개
  ✅ 성공: 3개
  ❌ 실패: 0개

처리 시간:
  총 시간: 35.4초
  평균 시간: 11.8초/문서

Scraper 통계:
  스크래핑 성공: 3개
  LLM 분석 성공: 3개
================================================================================
```

---

## 🗄️ MongoDB 결과 확인

스크립트 실행 후 출력되는 명령어로 확인:

```bash
# MongoDB 컨테이너 접속
docker exec -it ksubscribe_mongodb mongosh mycontents

# 처리된 문서 조회
db.contents.find({
  _id: { $in: [
    ObjectId("68edc849ae3da00bfe2d0cef"),
    ObjectId("68edc849ae3da00bfe2d0cf3"),
    ObjectId("68edc84aae3da00bfe2d0cf7")
  ]}
}).pretty()

# 요약 결과만 보기
db.contents.find({
  _id: { $in: [ObjectId("68edc849ae3da00bfe2d0cef")] }
}, {
  title: 1,
  'contentsMeta.summary': 1,
  'contentsMeta.sentiment': 1
}).pretty()
```

---

## ❓ 문제 해결

### 1. "Queue에서 문서를 찾을 수 없습니다"

**원인**: contents_queue에 해당 ID의 문서가 없음

**해결**:
```bash
# 먼저 수집 실행
cd docker_shell
python3 main_collect_and_scrapping.py

# 또는 단일 URL 추가
python3 main_collect_and_scrapping2.py \
  --single-url "https://example.com/news" \
  --org A0001 --category B0001
```

---

### 2. "유효하지 않은 ObjectId"

**원인**: ID 형식이 잘못됨

**해결**: 올바른 24자리 hex 문자열인지 확인
```
✅ 올바른 예: 68edc849ae3da00bfe2d0cef
❌ 잘못된 예: 12345, abc, 68edc849 (짧음)
```

---

### 3. Ollama 연결 오류

**원인**: Ollama 서버가 실행되지 않음

**해결**:
```bash
# Docker Compose로 Ollama 시작
docker-compose -f docker-compose-unified.yml up -d ollama

# 상태 확인
docker ps | grep ollama
```

---

## 🔍 고급 사용 사례

### 사례 1: 같은 문서로 다른 모델 비교

```bash
# 모델 A로 평가
python3 test_llm_evaluation.py \
  --test-ids test_ids.txt \
  --keep-queue \
  --save-json results_modelA.json

# config.py에서 모델 변경 (예: gemma2:9b → llama3.1:8b)
# 다시 실행
python3 test_llm_evaluation.py \
  --test-ids test_ids.txt \
  --keep-queue \
  --save-json results_modelB.json

# 결과 비교
diff results_modelA.json results_modelB.json
```

---

### 사례 2: 특정 기관의 문서만 평가

**Step 1**: MongoDB에서 ID 목록 추출
```bash
docker exec -it ksubscribe_mongodb mongosh mycontents --eval '
  db.contents_queue.find(
    {contentOrgId: "A0001"},
    {_id: 1}
  ).forEach(doc => print(doc._id))
' > org_A0001_ids.txt
```

**Step 2**: 평가 실행
```bash
python3 test_llm_evaluation.py --test-ids org_A0001_ids.txt
```

---

### 사례 3: 실패한 문서만 재평가

**Step 1**: MongoDB에서 분석 실패 문서 찾기
```bash
docker exec -it ksubscribe_mongodb mongosh mycontents --eval '
  db.contents.find(
    {"contentsMeta.summary": {$exists: false}},
    {_id: 1}
  ).forEach(doc => print(doc._id))
' > failed_ids.txt
```

**Step 2**: 재평가
```bash
python3 test_llm_evaluation.py --test-ids failed_ids.txt
```

---

## 📝 파일 위치

```
src/
├── test_llm_evaluation.py        # 메인 스크립트
├── test_ids.example.txt          # ID 목록 예시
├── test_ids.txt                  # 실제 사용 (gitignore)
└── README_test_llm.md            # 이 문서
```

---

## ⚙️ 내부 동작 원리

1. **ID 파싱**: 파일 또는 커맨드 라인에서 ObjectId 로드
2. **Queue 조회**: MongoDB contents_queue에서 문서 페치
3. **Ollama 시작**: OllamaAlive 스레드 시작
4. **스크래핑**: Trafilaura로 본문 추출
5. **LLM 분석**: Ollama 5개 프롬프트 실행
   - question_verify (키워드 검증)
   - question_summary (요약)
   - question_sentiment_ratio (감성 비율)
   - sentiment_reason (감성 이유)
   - sentiment_keywords (감성 키워드)
6. **저장**: MongoDB contents 컬렉션에 저장
7. **Queue 삭제**: (--keep-queue가 없으면) contents_queue에서 제거

---

## 🚨 주의사항

1. **프로덕션 영향 없음**
   - 이 스크립트는 독립적으로 실행됨
   - main_collect_and_scrapping.py와 충돌하지 않음

2. **Queue 삭제 주의**
   - 기본적으로 처리 후 Queue에서 삭제됨
   - 재실행하려면 `--keep-queue` 필수

3. **MongoDB 부하**
   - 대량 문서 평가 시 DB 부하 가능
   - 운영 시간 외 실행 권장

4. **Ollama 모델**
   - config.py의 `OLLAMA_MODEL_NAME` 설정 확인
   - 모델에 따라 결과가 다를 수 있음

---

## 📞 문의

- 스크립트 수정 필요 시: `test_llm_evaluation.py` 직접 편집 가능
- 버그 발견 시: develop 브랜치 이슈 등록
