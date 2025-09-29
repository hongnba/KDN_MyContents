# kSubscribe Python v2.0.0

## 설치 및 실행
다음 명령 실행 후 사용:
```bash
cd src
pip install –e .
```

## 패키지 구조

### 🚀 **ksubscribe_server** - FastAPI 서버 패키지
메인 웹 서버 및 API 엔드포인트를 제공하는 패키지
- **fastApi/**: REST API 엔드포인트 정의
- **analysis/**: 🤖 **AI 분석 모듈**
  - OpenAI GPT-4o 기반 분석 (`analysis_openai_v2.py`)
  - Ollama 로컬 LLM 분석 (`analysis_ollama*.py`)
  - RAG(Retrieval-Augmented Generation) 분석
- **similarity/**: 🔍 **유사도 분석 모듈**
  - SentenceTransformer를 사용한 키워드 유사도 계산
  - 코사인 유사도 기반 키워드 매칭
- **summarize/**: 📝 **요약 모듈**
  - GPT 기반 텍스트 요약
  - Ollama 기반 한국어 요약 (EEVE-Korean-10.8B)
  - PDF 문서 요약 기능

### 🔧 **ksubscribe_share** - 공용 패키지
데이터베이스, 모델, 설정 등 공통 기능을 제공하는 패키지
- **db/**: MongoDB 연결 및 데이터 모델
- **models/**: 데이터 구조 정의
- **config/**: 환경별 설정 파일
- **logger.py**: 로깅 시스템

### 📊 **docker_collect** - 데이터 수집 패키지
RSS, OpenAPI, 웹 크롤링을 통한 데이터 수집 (기존 KDN 유지, MongoDB 연동)
- RSS 피드 수집
- OpenAPI 데이터 수집
- Selenium 기반 웹 크롤링

### 🤖 **docker_scraping** - AI 기반 콘텐츠 분석 패키지
**핵심 AI 기능을 담당하는 패키지**
- **🔑 키워드 추출**: 
  - 사전 정의된 키워드와의 유사도 분석
  - TF-IDF 기반 키워드 추출
  - 자동 키워드 생성
- **📊 감정 분석 (Sentiment Classification)**:
  - OpenAI GPT-4o 기반 감정 분석
  - Hugging Face Transformers 기반 감정 분석
  - KOSAC 한국어 감성 사전 활용
  - 기관별 긍정/부정/중립 비율 분석
- **📝 콘텐츠 요약**:
  - 한 줄 요약 (short_summary)
  - 세 줄 요약 (long_summary)
  - AI 기반 자동 요약
- **🏢 기관 연관성 분석**:
  - 기사와 정부기관 간의 연관성 분석
  - 기관별 평판 분석
- **ai_scraping/**: Trafilaura, Newspaper3k를 활용한 웹 스크래핑

### 📱 **docker_talk_send** - 알림톡 전송 패키지
카카오 비즈톡, 이메일, 텔레그램을 통한 알림 전송 (기존 KDN 소스 유지, MongoDB 연동)
- 카카오 알림톡 전송
- 이메일 전송 (HTML 템플릿 지원)
- 텔레그램 봇 전송
- 전송 이력 관리

### 👥 **docker_talk_friend_send** - 친구톡 전송 패키지
카카오 친구톡 전송 기능

### 🛠 **docker_shell** - 실행 스크립트 패키지
Docker 및 Python 실행을 위한 배치 파일 및 셸 스크립트

## 🤖 주요 AI 기능

### 1. **키워드 분석 (Keyword Analysis)**
- **유사도 기반 키워드 매칭**: SentenceTransformer 모델을 사용하여 사전 정의된 키워드와 콘텐츠 간의 유사도 계산
- **자동 키워드 추출**: TF-IDF 및 AI 모델을 통한 핵심 키워드 자동 추출
- **다국어 지원**: 한국어 특화 모델 사용

### 2. **감정 분석 (Sentiment Classification)**
- **다중 모델 지원**: 
  - OpenAI GPT-4o
  - Hugging Face DistilBERT
  - KOSAC 한국어 감성 사전
- **기관별 평판 분석**: 정부기관에 대한 긍정/부정/중립 비율 분석
- **신뢰도 검증**: 여러 모델 간의 결과 비교를 통한 분석 신뢰도 평가

### 3. **유사도 분석 (Similarity Analysis)**
- **코사인 유사도**: 벡터 기반 텍스트 유사도 계산
- **의미적 유사도**: SentenceTransformer를 활용한 의미 기반 유사도 분석
- **키워드 매칭**: 사전 정의된 키워드와의 최적 매칭

## 🔄 데이터 처리 플로우
1. **수집** (docker_collect): RSS/API/웹에서 원시 데이터 수집
2. **스크래핑** (docker_scraping): AI 기반 콘텐츠 분석 및 메타데이터 생성
3. **저장** (ksubscribe_share): MongoDB에 구조화된 데이터 저장
4. **서비스** (ksubscribe_server): FastAPI를 통한 데이터 제공
5. **알림** (docker_talk_send): 분석 결과 기반 맞춤형 알림 전송

