# 단일 문서 Ollama 분석 스크립트 사용 가이드

## 📋 개요

이 스크립트는 MongoDB `contents_queue`에 있는 단일 문서를 선택하여 Ollama 기반 5가지 분석 업무를 수행합니다.

---

## 🎯 5가지 분석 업무

### 순서 및 의존성

```
1️⃣  검증 (독립 실행)
   └─ 문서가 DB 키워드와 관련 있는지 확인
   └─ 출력: ai_keyword, related, reason

2️⃣  요약 (독립 실행)
   └─ 짧은 요약(1줄) + 긴 요약(5줄 이상)
   └─ 출력: short_summary, long_summary

3️⃣  감성 비율 (독립 실행)
   └─ 긍정/부정/중립 비율 분석
   └─ 출력: positiveRatio, negativeRatio, neutralRatio
   ↓
   ├─→ 4️⃣  감성 이유 (3번 결과 필요)
   │    └─ 비율 판단 근거 설명
   │    └─ 출력: reason, positiveReason, negativeReason
   │
   └─→ 5️⃣  감성 키워드 (3번 결과 필요)
        └─ 긍정/부정 키워드 추출
        └─ 출력: positiveKeywords, negativeKeywords

최종: 3, 4, 5번 결과를 SentimentInfo 객체로 통합
```

---

## 🚀 실행 방법

### 1. 기본 실행 (기본 선택 문서 사용)

```bash
cd /home/mycontents/KDN_MyContents
python run_single_document_analysis.py
```

**기본 선택 문서:**
- ID: `68edc849ae3da00bfe2d0cf2`
- 제목: "한국전력기술, 생성형 AI 실무·보안 교육으로 디지털 혁신 가속화"

---

### 2. 특정 문서 ID 지정

```bash
python run_single_document_analysis.py --document-id <MongoDB ObjectId>
```

**예제:**
```bash
python run_single_document_analysis.py --document-id 68edc849ae3da00bfe2d0cee
```

---

### 3. 최신 문서 선택

```bash
python run_single_document_analysis.py --latest
```

가장 최근에 수집된 문서(`collectDt` 기준)를 자동으로 선택합니다.

---

### 4. 사용 가능한 문서 목록 확인

```bash
python run_single_document_analysis.py --list
```

MongoDB `contents_queue`에 있는 모든 문서의 ID, 제목, URL을 출력합니다.

---

## 📊 결과 저장 위치

### MongoDB (원본 분석 결과)
- 컬렉션: `mycontents.contents`
- 저장 내용:
  - `contentsRaw`: 스크래핑한 원문
  - `contentsMeta`: 분석 결과 (요약, 키워드, 감성 정보)

### MariaDB (구조화된 결과)
- 테이블 1: `ARTICLES_SUMMARY`
  - `short_summary`: 짧은 요약
  - `long_summary`: 긴 요약
  - `success`: 성공 여부
  - `url`: 문서 URL

- 테이블 2: `ARTICLE_KEYWORDS`
  - `keywords`: 사전 정의 키워드 (유사도 기반)
  - `ai_keywords`: AI가 추출한 키워드
  - `success`: 성공 여부
  - `url`: 문서 URL

---

## ⚙️ 필요한 컨테이너

스크립트 실행 전 다음 컨테이너가 **반드시 실행 중**이어야 합니다:

```bash
# 컨테이너 상태 확인
docker ps

# 필요한 컨테이너 (모두 Up 상태여야 함)
ksubscribe_mongodb         # MongoDB (문서 저장소)
ksubscribe_ollama          # Ollama LLM (분석 엔진)
ksubscribe_mariadb         # MariaDB (결과 저장)
parsing-container          # 문서 파싱
```

**확인 방법:**
```bash
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "mongodb|ollama|mariadb|parsing"
```

모든 컨테이너가 `Up` 상태여야 합니다.

---

## 📝 로그 확인

### 실시간 로그 (콘솔 출력)
스크립트 실행 시 진행 상황이 실시간으로 출력됩니다.

### 저장된 로그 파일
프로젝트의 로그 디렉토리에 저장됩니다:
```
/home/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/logs/
```

**주요 로그 파일:**
- `docker_scraping_result.log`: 스크래핑 및 분석 결과
- `docker_scraping.log`: 스크래핑 상세 로그

---

## 🔧 문제 해결

### 1. "문서를 찾을 수 없습니다" 오류

**원인:** 지정한 문서 ID가 MongoDB에 존재하지 않습니다.

**해결:**
```bash
# 사용 가능한 문서 목록 확인
python run_single_document_analysis.py --list

# 출력된 ID 중 하나를 선택하여 재실행
python run_single_document_analysis.py --document-id <올바른_ID>
```

---

### 2. "ModuleNotFoundError" 오류

**원인:** Python 경로 설정 문제

**해결:**
```bash
# 현재 디렉토리 확인
pwd
# 출력: /home/mycontents/KDN_MyContents

# 스크립트가 KDN_MyContents 폴더에 있는지 확인
ls run_single_document_analysis.py

# 있다면 다시 실행
python run_single_document_analysis.py
```

---

### 3. "Ollama 연결 실패" 오류

**원인:** Ollama 컨테이너가 실행 중이 아니거나 건강하지 않음

**해결:**
```bash
# Ollama 컨테이너 상태 확인
docker ps | grep ollama

# 출력 예: ksubscribe_ollama  Up 19 hours (healthy)

# Unhealthy이면 재시작
docker restart ksubscribe_ollama

# 건강 상태 확인 (30초 대기 후)
docker ps | grep ollama
```

---

### 4. "contents_queue가 비어 있습니다" 오류

**원인:** MongoDB `contents_queue` 컬렉션에 문서가 없음

**해결:**
```bash
# MongoDB에서 문서 확인
docker exec ksubscribe_mongodb mongo mycontents --quiet --eval \
  'db.contents_queue.count()'

# 출력이 0이면 데이터 수집 필요
# collect 기능을 사용하거나 수동으로 문서 추가 필요
```

---

### 5. GPU 메모리 부족 (OOM) 오류

**원인:** Ollama 모델이 GPU 메모리를 초과하여 사용

**해결:**
```bash
# GPU 메모리 사용량 확인
nvidia-smi

# 다른 모델이 로드되어 있으면 Ollama 재시작
docker restart ksubscribe_ollama

# 재시작 후 30초 대기 후 재실행
sleep 30
python run_single_document_analysis.py
```

---

## 💡 팁

### 여러 문서 연속 분석

다음과 같이 bash 스크립트로 여러 문서를 순차 분석할 수 있습니다:

```bash
#!/bin/bash
# 파일명: analyze_multiple.sh

# 분석할 문서 ID 목록
DOCUMENT_IDS=(
    "68edc849ae3da00bfe2d0cee"
    "68edc849ae3da00bfe2d0cef"
    "68edc849ae3da00bfe2d0cf0"
)

# 각 문서 순차 분석
for doc_id in "${DOCUMENT_IDS[@]}"; do
    echo "========================================="
    echo "분석 시작: $doc_id"
    echo "========================================="
    python run_single_document_analysis.py --document-id "$doc_id"
    echo ""
    echo "대기 중... (10초)"
    sleep 10
done

echo "모든 문서 분석 완료"
```

**실행:**
```bash
chmod +x analyze_multiple.sh
./analyze_multiple.sh
```

---

## 📞 문의

- 작성일: 2025-11-12
- 작성자: AI Assistant
- 용도: 회사 동료가 코드 수정 없이 그대로 실행 가능

**주의사항:**
- 이 스크립트는 **기존 코드를 수정하지 않습니다**
- 원본 프로젝트 코드는 `/home/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src`에 그대로 유지됩니다
- 스크립트는 원본 코드의 함수를 **import하여 사용**만 합니다

---

## 📚 참고 자료

### 관련 파일 위치

**원본 코드:**
```
/home/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src/
├── docker_shell/
│   └── main_collect_and_scrapping.py      # 원본 파이프라인 스크립트
├── docker_scraping/
│   └── contents_scraping_ollama_trafilaura.py  # 스크래핑 로직
├── ksubscribe_server/analysis/
│   ├── analysis_ollama_generate.py        # 5가지 분석 업무 구현
│   └── analysis_ollama_base.py            # 프롬프트 템플릿 정의
└── ksubscribe_share/
    └── db/service/
        ├── contentsQueueService.py        # MongoDB Queue 접근
        ├── articleKeywordsService.py      # MariaDB Keywords 저장
        └── articleSummaryService.py       # MariaDB Summary 저장
```

**설정 파일:**
```
/home/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src/ksubscribe_share/
└── config_linux.py                        # Ollama 모델 설정 등
```

---

## ✅ 체크리스트 (실행 전 확인)

실행 전 다음 항목을 확인하세요:

- [ ] 모든 필요한 컨테이너가 Up 상태인가? (`docker ps`)
- [ ] Ollama 컨테이너가 Healthy 상태인가?
- [ ] MongoDB `contents_queue`에 문서가 있는가? (`--list`로 확인)
- [ ] GPU 메모리가 충분한가? (`nvidia-smi`로 확인)
- [ ] Python 경로가 올바른가? (`pwd` → `/home/mycontents/KDN_MyContents`)

모두 확인했다면:
```bash
python run_single_document_analysis.py
```

**성공 시 출력 예:**
```
================================================================================
단일 문서 Ollama 분석 시작
================================================================================
...
✅ 문서 조회 성공
   - 문서 ID: 68edc849ae3da00bfe2d0cf2
   - 제목: 한국전력기술, 생성형 AI 실무·보안 교육으로 디지털 혁신 가속화
...
✅ 분석 완료
================================================================================
단일 문서 Ollama 분석 종료
================================================================================
```
