# 네이버 뉴스 날짜 범위별 스크래핑 가이드

> 작성일: 2025-12-29  
> 대상 파일: `collect_naver_news_by_date_excel.sh`, `collect_naver_news_by_date_excel.py`  
> 목적: 특정 키워드와 날짜 범위를 지정하여 네이버 뉴스를 스크래핑하고 엑셀 파일로 저장

---

## 📋 목차

1. [개요](#1-개요)
2. [파일 위치](#2-파일-위치)
3. [사용 방법](#3-사용-방법)
4. [실행 예시](#4-실행-예시)
5. [출력 파일](#5-출력-파일)
6. [주요 기능](#6-주요-기능)
7. [주의사항](#7-주의사항)

---

## 1. 개요

이 스크립트는 네이버 뉴스에서 특정 키워드와 날짜 범위에 해당하는 기사를 수집하여 날짜별로 엑셀 파일로 저장합니다.

**주요 특징:**
- 날짜 범위 지정 가능 (시작일 ~ 종료일)
- 날짜별로 개별 엑셀 파일 생성
- 각 날짜별로 최대 50페이지(약 500개 기사) 수집
- 날짜 변경 시 60초 대기 (API 제한 방지)
- Docker 컨테이너 내에서 실행

---

## 2. 파일 위치

### 쉘 스크립트
```
/home/themiraclesoft/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src/ksubscribe_share/test/collect_naver_news_by_date_excel.sh
```

### Python 스크립트
```
/home/themiraclesoft/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src/ksubscribe_share/test/collect_naver_news_by_date_excel.py
```

### 출력 디렉토리
```
/app/ksubscribe_share/test/news_scarppings/
```
(Docker 컨테이너 내부 경로)

---

## 3. 사용 방법

### 3.1 기본 사용법

```bash
./collect_naver_news_by_date_excel.sh <keyword> <start_date> <end_date>
```

### 3.2 파라미터 설명

| 파라미터 | 설명 | 형식 | 예시 |
|---------|------|------|------|
| `keyword` | 검색 키워드 | 문자열 | `한국전력` |
| `start_date` | 시작 날짜 | `YYYY.MM.DD` | `2025.11.01` |
| `end_date` | 종료 날짜 | `YYYY.MM.DD` | `2025.12.28` |

### 3.3 날짜 형식

- **올바른 형식**: `YYYY.MM.DD` (예: `2025.11.01`, `2025.12.28`)
- **잘못된 형식**: `2025-11-01`, `20251101`, `2025/11/01` 등

---

## 4. 실행 예시

### 예시 1: 한국전력 기사 수집 (2025년 11월 1일 ~ 12월 28일)

```bash
cd /home/themiraclesoft/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src/ksubscribe_share/test
./collect_naver_news_by_date_excel.sh 한국전력 2025.11.01 2025.12.28
```

### 예시 2: 한 달치 기사 수집

```bash
./collect_naver_news_by_date_excel.sh 한국전력 2025.11.01 2025.11.30
```

### 예시 3: 특정 날짜만 수집

```bash
./collect_naver_news_by_date_excel.sh 한국전력 2025.11.01 2025.11.01
```

---

## 5. 출력 파일

### 5.1 파일명 형식

```
naver_news_{keyword}_{YYYYMMDD}.xlsx
```

**예시:**
- `naver_news_한국전력_20251101.xlsx`
- `naver_news_한국전력_20251102.xlsx`
- `naver_news_한국전력_20251228.xlsx`

### 5.2 엑셀 파일 구조

각 엑셀 파일은 다음 컬럼을 포함합니다:

| 컬럼명 | 설명 | 예시 |
|--------|------|------|
| `title` | 기사 제목 | "한국전력, 전력 수요 대비 공급 여유 확보" |
| `link` | 기사 URL | "https://search.naver.com/search.naver?..." |
| `date` | 발행 날짜 | "2025.11.01" |

### 5.3 저장 위치

- **Docker 컨테이너 내부**: `/app/ksubscribe_share/test/news_scarppings/`
- **호스트에서 확인**: Docker 컨테이너 내부 파일이므로 `docker exec` 또는 `docker cp`로 확인

---

## 6. 주요 기능

### 6.1 날짜별 개별 수집

- 각 날짜마다 독립적으로 스크래핑 수행
- 날짜별로 개별 엑셀 파일 생성
- 특정 날짜 수집 실패 시에도 다른 날짜는 계속 진행

### 6.2 페이지네이션 처리

- 각 날짜당 최대 50페이지 수집 (약 500개 기사)
- 페이지당 10개 기사 수집
- 더 이상 기사가 없으면 자동으로 다음 날짜로 이동

### 6.3 중복 제거

- 같은 링크(URL)를 가진 기사는 자동으로 제거
- 동일 페이지 내에서 중복 방지

### 6.4 요청 제한 관리

- 각 페이지 요청 사이에 1초 딜레이
- 날짜 변경 시 60초 대기 (API 제한 방지)
- 마지막 날짜는 대기하지 않음

---

## 7. 주의사항

### 7.1 Docker 컨테이너 필요

이 스크립트는 Docker 컨테이너(`ksubscribe_python_unified`) 내에서 실행됩니다.  
컨테이너가 실행 중이어야 합니다.

**컨테이너 상태 확인:**
```bash
docker ps | grep ksubscribe_python_unified
```

### 7.2 실행 시간

- 날짜 범위가 길수록 실행 시간이 오래 걸립니다
- 예: 58일치 수집 시 약 58분 이상 소요 (날짜 변경 대기 시간 포함)
- 백그라운드 실행 권장

**백그라운드 실행 예시:**
```bash
nohup ./collect_naver_news_by_date_excel.sh 한국전력 2025.11.01 2025.12.28 > scraping.log 2>&1 &
```

### 7.3 네이버 검색 API 제한

- 과도한 요청 시 IP 차단 가능
- 날짜 변경 시 60초 대기 시간은 필수
- 필요 시 `delay` 파라미터 조정 (Python 스크립트 내부)

### 7.4 파일 경로

- 출력 파일은 Docker 컨테이너 내부에 저장됩니다
- 호스트에서 파일을 확인하려면 `docker cp` 사용:

```bash
# 컨테이너에서 호스트로 파일 복사
docker cp ksubscribe_python_unified:/app/ksubscribe_share/test/news_scarppings/naver_news_한국전력_20251101.xlsx ./
```

### 7.5 날짜 형식 오류

날짜 형식이 올바르지 않으면 스크립트가 즉시 종료됩니다:

```bash
❌ 오류: 날짜 형식이 올바르지 않습니다.
   올바른 형식: YYYY.MM.DD (예: 2025.11.01)
```

---

## 8. 실행 흐름

```
1. 쉘 스크립트 실행
   ↓
2. 파라미터 검증 (키워드, 날짜 형식)
   ↓
3. Python 스크립트를 Docker 컨테이너에 복사
   ↓
4. Docker 컨테이너 내에서 Python 스크립트 실행
   ↓
5. 날짜 범위 생성 (시작일 ~ 종료일)
   ↓
6. 각 날짜별로 반복:
   ├─ 네이버 뉴스 검색 (최대 50페이지)
   ├─ 기사 정보 추출 (제목, 링크, 날짜)
   ├─ 엑셀 파일로 저장
   └─ 다음 날짜로 이동 전 60초 대기
   ↓
7. 완료 메시지 출력 및 생성된 파일 목록 표시
```

---

## 9. 문제 해결

### 9.1 스크립트를 찾을 수 없음

```bash
❌ 오류: Python 스크립트를 찾을 수 없습니다
```

**해결 방법:**
- 스크립트 경로 확인
- `collect_naver_news_by_date_excel.py` 파일이 같은 디렉토리에 있는지 확인

### 9.2 Docker 컨테이너 연결 실패

```bash
❌ 스크립트 복사 실패
```

**해결 방법:**
- Docker 컨테이너가 실행 중인지 확인: `docker ps`
- 컨테이너 이름 확인: `ksubscribe_python_unified`

### 9.3 수집된 기사가 없음

특정 날짜에 기사가 없으면 다음 메시지가 출력됩니다:

```
→ 2025.11.15: 수집된 기사 없음
```

이는 정상 동작이며, 해당 날짜는 엑셀 파일이 생성되지 않습니다.

---

## 10. 참고 사항

### 10.1 후속 처리

수집된 엑셀 파일은 다음 단계에서 사용됩니다:

1. **본문 추출**: `collect_article_content_trafilaura.py`로 기사 본문 추출
2. **중복 제거**: `remove_duplicate_articles_from_excel.py`로 중복 기사 제거
3. **CSV 변환**: 중복 제거 후 CSV 파일로 변환
4. **Queue 등록**: `import_csv_to_contents_queue.py`로 `contents_queue`에 등록

### 10.2 관련 스크립트

- `collect_article_content_trafilaura.py`: 엑셀 파일에서 기사 본문 추출
- `remove_duplicate_articles_from_excel.py`: 중복 기사 제거 및 CSV 변환
- `import_csv_to_contents_queue.py`: CSV 파일을 `contents_queue`에 등록

---

## 11. 예시 실행 로그

```
============================================================
네이버 뉴스 날짜별 스크래핑 시작
============================================================
검색어: 한국전력
기간: 2025.11.01 ~ 2025.12.28
컨테이너: ksubscribe_python_unified
============================================================

📋 Python 스크립트를 컨테이너에 복사 중...
✅ 스크립트 복사 완료

🚀 스크래핑 시작...
============================================================
네이버 뉴스 날짜별 스크래핑 시작
검색어: 한국전력
기간: 2025.11.01 ~ 2025.12.28
총 58일 수집 예정
============================================================

[1/58] 2025.11.01 수집 시작...
  [페이지 1] 수집 중... (start=1)
  → 10개 기사 수집 (누적: 10건)
  [페이지 2] 수집 중... (start=11)
  → 10개 기사 수집 (누적: 20건)
  ...
  → 엑셀 저장 완료: /app/ksubscribe_share/test/news_scarppings/naver_news_한국전력_20251101.xlsx (150건)
  → 2025.11.01: 150건 수집 완료
  → 다음 날짜 조회 전 60초 대기...

[2/58] 2025.11.02 수집 시작...
  ...
```

---

**작성자**: Auto  
**최종 수정일**: 2025-12-29



