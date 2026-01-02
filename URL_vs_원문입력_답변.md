# 질문 답변: URL vs 원문 입력

## 질문
> 임의의 기사를 넣으면 된다고 하는데, 기사 URL과 원문을 그대로 긁어서 복사해야 하니? 아니면 URL만 넣으면 알아서 처리가 가능하니?

---

## 답변: **두 가지 모두 가능합니다!**

### ✅ 방법 1: URL만 입력 (자동 스크래핑) - **권장**

**URL만 넣으면 시스템이 자동으로:**
1. 웹페이지에 접속
2. 본문 추출 (스크래핑)
3. Ollama 분석 실행

**핵심 코드 확인:**
```python
# contents_scraping_ollama_trafilaura.py 라인 702-707
# Scrape content using Trafilaura
isSuccess, title, raw_data = self.trafilauraScraper.get_newbody(queue_content.url)
#                                                                 ^^^^^^^^^^^^^^^^
#                                                                 URL만 입력!
```

**사용 예:**
```bash
python3 test_single_article.py \
  --url "https://www.motie.go.kr/kor/article/ATCL2826a2625/69968/view" \
  --org "A0001" \
  --category "B0002"
```

**장점:**
- ✅ 간편함 (URL만 복사-붙여넣기)
- ✅ 최신 내용 보장 (실시간 웹 접속)
- ✅ 제목도 자동 추출

**단점:**
- ❌ 웹사이트 다운 시 실패
- ❌ 스크래핑 시간 소요 (수 초)

---

### ✅ 방법 2: 원문 직접 입력 (스크래핑 생략)

**이미 복사한 원문이 있다면 바로 분석 가능:**

**사용 예:**
```bash
python3 test_single_article.py \
  --text "산업통상자원부는 2025년 산업통계 및 동향분석 기반사업의 보조사업자 선정을 재공고하였다..." \
  --org "A0001" \
  --category "B0002"
```

**또는 파일로:**
```bash
# 1. 원문을 파일로 저장
cat > article.txt << 'EOF'
산업통상자원부는 2025년 산업통계 및 동향분석 기반사업의 
보조사업자 선정을 재공고하였다...
EOF

# 2. 실행
python3 test_single_article.py \
  --file article.txt \
  --org "A0001" \
  --category "B0002"
```

**장점:**
- ✅ 웹사이트 접근 불필요
- ✅ 빠름 (스크래핑 생략)
- ✅ 편집된 텍스트 사용 가능

**단점:**
- ❌ 원문 수동 복사 필요

---

## 📊 비교표

| 항목 | URL 입력 (자동) | 원문 입력 (수동) |
|------|----------------|-----------------|
| **필요 정보** | URL만 | 원문 전체 텍스트 |
| **스크래핑** | 자동 | 생략 |
| **속도** | 느림 (웹 접속 필요) | 빠름 |
| **안정성** | 웹사이트 상태 의존 | 항상 가능 |
| **권장 상황** | 실시간 최신 기사 | 이미 복사한 텍스트 있을 때 |

---

## 🎯 권장사항

### 일반적인 경우: **URL만 입력**
```bash
# 가장 간단하고 빠른 방법
python3 test_single_article.py \
  --url "https://example.com/article" \
  --org "A0001" \
  --category "B0002"
```

### 웹사이트 접근 불가 시: **원문 직접 입력**
```bash
# 원문을 복사해서 파일로 저장 후
python3 test_single_article.py \
  --file article.txt \
  --org "A0001" \
  --category "B0002"
```

---

## 🛠️ 생성된 도구

프로젝트에 다음 파일들을 생성했습니다:

### 1. `test_single_article.py` - 메인 테스트 스크립트
**위치:** `/home/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src/docker_shell/`

**기능:**
- URL 자동 스크래핑 + 분석
- 원문 직접 입력 + 분석
- 결과를 화면 및 JSON 파일로 출력

**실행 예:**
```bash
cd /home/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src/docker_shell

# URL 테스트
python3 test_single_article.py \
  --url "https://www.motie.go.kr/kor/article/ATCL2826a2625/69968/view" \
  --org "A0001" \
  --category "B0002"

# 원문 테스트
python3 test_single_article.py \
  --text "기사 원문..." \
  --org "A0001" \
  --category "B0002"

# 파일 테스트
python3 test_single_article.py \
  --file article.txt \
  --org "A0001" \
  --category "B0002"
```

---

### 2. `test_single_article_사용법.md` - 상세 사용 가이드
**위치:** 같은 디렉토리

**내용:**
- 상세 사용 방법
- 예제 모음
- 기관/카테고리 ID 목록
- 문제 해결 가이드
- 여러 기사 일괄 처리 팁

---

### 3. `simple_test.py` - 설정만 바꿔서 실행
**위치:** 같은 디렉토리

**사용법:**
```python
# simple_test.py 파일을 열어서 상단 설정만 변경
TEST_URL = "https://example.com/article"  # 또는
TEST_TEXT = "원문 텍스트..."
ORG_ID = "A0001"
CATEGORY_ID = "B0002"

# 실행하면 명령어 안내
python3 simple_test.py
```

---

## 💡 실제 사용 시나리오

### 시나리오 1: 새로운 기사 빠르게 테스트
```bash
# 브라우저에서 URL 복사 → 바로 실행
python3 test_single_article.py \
  --url "복사한_URL" \
  --org "A0001" \
  --category "B0002"

# 결과: test_result.json 자동 생성
```

### 시나리오 2: 웹사이트 다운 시 수동 분석
```bash
# 1. 브라우저에서 기사 본문 복사
# 2. article.txt 파일로 저장
# 3. 실행
python3 test_single_article.py \
  --file article.txt \
  --org "A0001" \
  --category "B0002"
```

### 시나리오 3: 여러 기사 일괄 분석
```bash
# urls.txt에 URL 목록 저장
cat > urls.txt << 'EOF'
https://www.motie.go.kr/article/1
https://www.motie.go.kr/article/2
https://www.motie.go.kr/article/3
EOF

# 반복 실행
while read url; do
  python3 test_single_article.py \
    --url "$url" \
    --org "A0001" \
    --category "B0002"
  sleep 2  # 서버 부하 방지
done < urls.txt
```

---

## 🔍 내부 동작 원리

### URL 입력 시 흐름
```
[URL 입력]
    ↓
[TrafilauraScraper.get_newbody(url)]  ← 자동 스크래핑
    ↓
[원문 텍스트 추출]
    ↓
[AnalysisOllamaGenerateCall.analysis_main(text)]  ← Ollama 분석
    ↓
[결과 출력 및 저장]
```

### 원문 입력 시 흐름
```
[원문 텍스트 입력]
    ↓
[AnalysisOllamaGenerateCall.analysis_main(text)]  ← 바로 분석
    ↓
[결과 출력 및 저장]
```

**핵심:** 스크래핑 단계를 건너뛰는 것만 다를 뿐, 분석 로직은 동일합니다.

---

## ✅ 최종 답변 요약

### Q1: URL만 넣어도 되나요?
**A: 네, URL만 넣으면 자동으로 스크래핑해서 분석합니다.**

### Q2: 원문을 복사해야 하나요?
**A: 선택사항입니다. URL이 있으면 원문 복사 불필요합니다.**

### Q3: 둘 중 뭐가 더 좋나요?
**A: 일반적으로 URL 입력이 더 간편합니다. 웹사이트 접근이 안 될 때만 원문 직접 입력하세요.**

---

## 📚 관련 문서

1. **Ollama_분석_프롬프트_상세.md**
   - Ollama에 전달되는 5가지 프롬프트 상세 설명
   - 각 프롬프트의 입출력 예시

2. **test_single_article_사용법.md**
   - 테스트 스크립트 완전 가이드
   - 예제 모음 및 문제 해결

3. **main_collect_and_scrapping2_분석보고서.md**
   - 전체 시스템 구조 설명
   - 모듈별 역할 및 데이터 흐름

4. **main_collect_and_scrapping2_흐름도.md**
   - 시각화된 시스템 흐름도
   - Mermaid 다이어그램

---

이상으로 URL vs 원문 입력 질문에 대한 답변을 마칩니다.
