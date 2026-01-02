# 단일 기사 Ollama 분석 테스트 가이드

## 📖 개요

`test_single_article.py` 스크립트를 사용하면 **크롤링/큐 없이** 단일 기사를 바로 Ollama로 분석할 수 있습니다.

---

## 🚀 사용 방법

### 방법 1: URL만 입력 (자동 스크래핑) - **추천**

URL만 제공하면 자동으로 웹페이지에 접속해서 본문을 추출합니다.

```bash
cd /home/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src/docker_shell

python test_single_article.py \
  --url "https://www.motie.go.kr/kor/article/ATCL2826a2625/69968/view" \
  --org "A0001" \
  --category "B0002"
```

**필수 파라미터:**
- `--url`: 분석할 기사의 URL
- `--org`: 기관 ID (예: A0001 = 산업통상자원부)
- `--category`: 카테고리 ID (예: B0002 = 사업공고)

**장점:**
- 간단함! URL만 복사-붙여넣기
- 자동으로 최신 본문 가져옴

**단점:**
- 웹사이트가 다운되면 실패
- 스크래핑에 수 초 소요

---

### 방법 2: 원문 텍스트 직접 입력 (스크래핑 생략)

이미 원문을 복사했다면, 스크래핑 단계를 건너뛰고 바로 분석 가능합니다.

```bash
python test_single_article.py \
  --text "산업통상자원부는 2025년 산업통계 및 동향분석 기반사업의 보조사업자 선정을 재공고하였다..." \
  --org "A0001" \
  --category "B0002"
```

**장점:**
- 웹사이트 접근 불필요
- 빠름 (스크래핑 생략)
- 이미 편집된 텍스트 사용 가능

**단점:**
- 원문을 직접 복사해야 함

---

### 방법 3: 텍스트 파일에서 읽기

긴 기사는 파일로 저장해서 사용하세요.

**1. 원문 파일 생성 (`article.txt`)**
```
산업통상자원부는 2025년 산업통계 및 동향분석 기반사업의 보조사업자 선정을 재공고하였다. 
사업을 수행하고자 하는 기관은 지정된 절차에 따라 신청해야 한다. 
공고일은 2025년 1월 20일이다.
...
```

**2. 실행**
```bash
python test_single_article.py \
  --file article.txt \
  --org "A0001" \
  --category "B0002" \
  --url-meta "https://www.motie.go.kr/kor/article/..."
```

**선택 파라미터:**
- `--url-meta`: 원본 URL (메타데이터용, 생략 가능)

---

## 📊 출력 예시

스크립트를 실행하면 다음과 같은 결과가 출력됩니다:

```
=== URL 기반 테스트 시작 ===
URL: https://www.motie.go.kr/kor/article/...
기관: A0001, 카테고리: B0002

1단계: 웹 스크래핑 중...
✅ 스크래핑 성공!
제목: 「산업통계 및 동향분석 기반사업」재공고...
본문 길이: 1523 자

2단계: Ollama 분석 중...
✅ Ollama 분석 성공!

============================================================
📊 분석 결과
============================================================

🔑 키워드:
  - 산업통계
  - 동향분석
  - 재공고

📝 짧은 요약:
  2025년 산업통계 및 동향분석 기반사업 보조사업자 재공고.

📄 긴 요약:
  산업통상자원부는 2025년 산업통계 및 동향분석 기반사업의 보조사업자 선정을
  재공고하였다. 사업을 수행하고자 하는 기관은 지정된 절차에 따라 신청해야 한다.
  공고일은 2025년 1월 20일이다.

💡 사전정의 키워드:
  - 데이터: 0.85
  - 플랫폼: 0.65
  - 에너지: 0.45

😊 감성 분석:
  기관: 산업통상자원부 (A0001)
    긍정: 90.0%
    부정: 0.0%
    중립: 10.0%
    이유: 재공고를 통해 사업자 선발을 적극적으로 추진하고 있다는 긍정적인 내용이 주를 이루고 있기 때문.

============================================================

결과를 test_result.json에 저장했습니다.
```

**결과 파일**: `test_result.json` (같은 디렉토리에 자동 저장)

---

## 🔧 기관 ID 및 카테고리 ID 목록

### 주요 기관 ID (orgId)

| 기관 ID | 기관명 |
|---------|--------|
| A0001 | 산업통상자원부 |
| A0002 | 과학기술정보통신부 |
| A0003 | 환경부 |
| A0004 | 나라장터 |
| ... | (MongoDB `contents_org` 참조) |

### 주요 카테고리 ID (cateId)

| 카테고리 ID | 카테고리명 |
|-------------|------------|
| B0001 | 보도자료 |
| B0002 | 사업공고 |
| B0003 | 정책자료 |
| B0005 | 입찰정보 |
| B0010 | 뉴스 |
| ... | (MongoDB `common_code` 참조) |

**전체 목록 조회:**
```bash
# MongoDB에서 조회
docker exec -i ksubscribe_mongodb mongo mycontents --quiet --eval 'db.contents_org.find({}, {orgId:1, orgName:1}).pretty()'
```

---

## 🧪 실제 테스트 예제

### 예제 1: 산업통상자원부 사업공고 분석

```bash
python test_single_article.py \
  --url "https://www.motie.go.kr/kor/article/ATCL2826a2625/69968/view" \
  --org "A0001" \
  --category "B0002"
```

### 예제 2: 짧은 텍스트로 빠른 테스트

```bash
python test_single_article.py \
  --text "산업통상자원부가 신재생에너지 확대를 위한 새로운 정책을 발표했다. 태양광 발전 보조금이 증가하며, 2030년까지 재생에너지 비율을 30%로 높이겠다는 목표를 제시했다." \
  --org "A0001" \
  --category "B0003"
```

### 예제 3: 원문 파일 사용

**1. 파일 생성**
```bash
cat > /tmp/test_article.txt << 'EOF'
과학기술정보통신부는 AI 기술 개발 지원 사업을 확대한다고 밝혔다.
이번 사업은 중소기업과 스타트업을 대상으로 하며, 총 100억 원의 예산이 투입된다.
신청은 1월 31일까지이며, 선정 결과는 2월 중 발표될 예정이다.
EOF
```

**2. 실행**
```bash
python test_single_article.py \
  --file /tmp/test_article.txt \
  --org "A0002" \
  --category "B0002" \
  --url-meta "https://www.msit.go.kr/test"
```

---

## 📝 결과 파일 (test_result.json)

분석 결과는 자동으로 `test_result.json` 파일에 저장됩니다:

```json
{
  "url": "https://www.motie.go.kr/kor/article/...",
  "keywords": [
    "산업통계",
    "동향분석",
    "재공고"
  ],
  "shortSummary": "2025년 산업통계 및 동향분석 기반사업 보조사업자 재공고.",
  "longSummary": "산업통상자원부는 2025년 산업통계 및 동향분석 기반사업의 보조사업자 선정을 재공고하였다...",
  "predKeywords": {
    "데이터": 0.85,
    "플랫폼": 0.65,
    "에너지": 0.45
  },
  "sentiments": [
    {
      "orgId": "A0001",
      "orgName": "산업통상자원부",
      "positiveRatio": 90.0,
      "negativeRatio": 0.0,
      "neutralRatio": 10.0,
      "reason": "재공고를 통해 사업자 선발을 적극적으로 추진하고 있다는 긍정적인 내용이 주를 이루고 있기 때문."
    }
  ]
}
```

---

## ⚠️ 주의사항

### 1. Ollama 서버 실행 확인
스크립트 실행 전 Ollama 서버가 작동 중인지 확인하세요:

```bash
# Ollama 컨테이너 상태 확인
docker ps | grep ollama

# Ollama API 접근 테스트
curl http://localhost:11434/api/tags
```

### 2. MongoDB 연결 확인
```bash
docker exec -i ksubscribe_mongodb mongo --eval 'db.adminCommand({ping:1})'
```

### 3. 필수 Python 패키지
```bash
# 필요 시 설치
pip install langchain_ollama pymongo selenium beautifulsoup4
```

---

## 🔍 문제 해결

### 오류: "Scraping failed"
- 원인: 웹사이트 접근 실패 또는 본문 추출 실패
- 해결: `--text` 또는 `--file` 옵션으로 원문 직접 입력

### 오류: "Ollama 분석 실패"
- 원인: Ollama 서버 다운 또는 모델 미설치
- 해결:
  ```bash
  # Ollama 컨테이너 재시작
  docker restart ksubscribe_ollama
  
  # 모델 설치 확인
  docker exec -i ksubscribe_ollama ollama list
  ```

### 오류: "Could not find org/category"
- 원인: 잘못된 orgId 또는 cateId
- 해결: MongoDB에서 정확한 ID 확인
  ```bash
  docker exec -i ksubscribe_mongodb mongo mycontents --quiet --eval 'db.contents_org.find({}, {orgId:1, orgName:1})'
  ```

---

## 💡 팁

### 1. 여러 기사 일괄 분석
여러 URL을 파일에 저장하고 반복 실행:

```bash
# urls.txt 파일 생성
cat > urls.txt << 'EOF'
https://www.motie.go.kr/article/1
https://www.motie.go.kr/article/2
https://www.motie.go.kr/article/3
EOF

# 반복 실행
while read url; do
  python test_single_article.py --url "$url" --org "A0001" --category "B0002"
done < urls.txt
```

### 2. 결과를 별도 파일로 저장
```bash
python test_single_article.py \
  --url "..." \
  --org "A0001" \
  --category "B0002" \
  > result_$(date +%Y%m%d_%H%M%S).log 2>&1
```

### 3. 도움말 보기
```bash
python test_single_article.py --help
```

---

## 📚 관련 문서

- `Ollama_분석_프롬프트_상세.md`: Ollama에 전달되는 프롬프트 설명
- `main_collect_and_scrapping2_분석보고서.md`: 전체 파이프라인 설명
- `main_collect_and_scrapping2_흐름도.md`: 시스템 흐름도

---

이상으로 단일 기사 테스트 가이드를 마칩니다.
