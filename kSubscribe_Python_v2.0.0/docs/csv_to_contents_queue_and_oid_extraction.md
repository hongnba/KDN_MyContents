# CSV 파일을 contents_queue에 저장하고 OID 추출하기

> 작성일: 2025-12-29  
> 목적: CSV 파일의 기사 정보를 MongoDB `contents_queue` 컬렉션에 저장하고, 저장된 문서의 ObjectId를 텍스트 파일로 추출하는 전체 과정 가이드

---

## 📋 목차

1. [개요](#1-개요)
2. [사전 준비](#2-사전-준비)
3. [단계별 실행 가이드](#3-단계별-실행-가이드)
4. [CSV 파일 형식](#4-csv-파일-형식)
5. [스크립트 상세 설명](#5-스크립트-상세-설명)
6. [실행 예시](#6-실행-예시)
7. [문제 해결](#7-문제-해결)
8. [주요 특징](#8-주요-특징)

---

## 1. 개요

이 가이드는 다음 두 단계로 구성된 워크플로우를 설명합니다:

1. **CSV → contents_queue**: CSV 파일의 기사 정보를 MongoDB `contents_queue` 컬렉션에 저장
2. **contents_queue → OID 텍스트 파일**: 저장된 문서의 ObjectId를 추출하여 텍스트 파일로 저장

### 사용되는 스크립트

- `import_csv_to_contents_queue.py`: CSV 파일을 읽어서 `contents_queue`에 저장
- `extract_oids_from_csv.py`: CSV의 URL을 기반으로 `contents_queue`에서 OID를 추출하여 텍스트 파일로 저장

### 전체 워크플로우

```
CSV 파일 (날짜, 기사 제목, 기사 URL)
    ↓
[1단계] import_csv_to_contents_queue.py
    ↓
MongoDB contents_queue 컬렉션
    ↓
[2단계] extract_oids_from_csv.py
    ↓
텍스트 파일 (OID 목록)
```

---

## 2. 사전 준비

### 2.1 필요한 파일

- **CSV 파일**: 기사 정보가 담긴 CSV 파일 (형식은 아래 참조)
- **Python 스크립트**:
  - `import_csv_to_contents_queue.py`
  - `extract_oids_from_csv.py`

### 2.2 파일 위치

**스크립트 위치:**
```
/home/themiraclesoft/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src/ksubscribe_share/test/
```

**Docker 컨테이너 내부 경로:**
```
/app/ksubscribe_share/test/
```

### 2.3 Docker 컨테이너 확인

작업은 Docker 컨테이너(`ksubscribe_python_unified`) 내에서 실행됩니다.

```bash
# 컨테이너 상태 확인
docker ps | grep ksubscribe_python_unified
```

---

## 3. 단계별 실행 가이드

### 3.1 1단계: CSV 파일을 contents_queue에 저장

#### 명령어 형식

```bash
docker exec ksubscribe_python_unified python3 /app/ksubscribe_share/test/import_csv_to_contents_queue.py <csv_file_path>
```

#### 실행 예시

```bash
# Docker 컨테이너 내부에서 실행
docker exec ksubscribe_python_unified python3 /app/ksubscribe_share/test/import_csv_to_contents_queue.py /app/ksubscribe_share/test/refined_new_scarppings/naver_news_한국전력_deduped_20251101_20251203.csv
```

#### 동작 과정

1. CSV 파일 읽기 (`utf-8-sig` 인코딩)
2. 각 행에서 날짜, 제목, URL 추출
3. URL 중복 체크 (`ContentsQueueService.isExistQueue()`)
4. 중복이 아닌 경우 `contents_queue`에 저장
5. 저장 결과 요약 출력

#### 출력 예시

```
================================================================================
CSV 파일에서 contents_queue로 데이터 가져오기 시작
📁 파일 경로: /app/ksubscribe_share/test/refined_new_scarppings/naver_news_한국전력_deduped_20251101_20251203.csv
================================================================================
📝 CSV 파일에서 349건의 기사를 읽었습니다.
📅 수집일: 20251229
🏢 기관 ID: A0010
📂 카테고리 ID: B0010
🔑 수집 키워드: 한국전력
================================================================================
[1/349] ✅ 저장 성공: 남양주시, 민‧관‧군 합동 '재난대응 안전한국훈련'...
[2/349] ✅ 저장 성공: 글로벌전력산업 표준 논의의 장, 서울에서 열린다...
...
================================================================================
📊 저장 결과 요약:
  ✅ 성공: 349건
  ⏭️  건너뜀 (중복): 0건
  ❌ 실패: 0건
  📝 전체: 349건
================================================================================
```

### 3.2 2단계: OID 추출 및 텍스트 파일 저장

#### 명령어 형식

```bash
docker exec ksubscribe_python_unified python3 /app/ksubscribe_share/test/extract_oids_from_csv.py <csv_file_path> <output_file_name>
```

#### 실행 예시

```bash
# Docker 컨테이너 내부에서 실행
docker exec ksubscribe_python_unified python3 /app/ksubscribe_share/test/extract_oids_from_csv.py /app/ksubscribe_share/test/refined_new_scarppings/naver_news_한국전력_deduped_20251101_20251203.csv test_ids_1101_1203
```

#### 동작 과정

1. CSV 파일에서 URL 목록 추출
2. MongoDB `contents_queue`에서 URL로 문서 조회
   - 오늘 날짜(`collectDt`)에 저장된 문서만 조회
   - 기관 ID(`A0010`) 필터링
3. 각 URL에 대응하는 ObjectId 추출
4. 텍스트 파일로 저장 (한 줄에 하나씩)

#### 출력 예시

```
================================================================================
CSV 파일에서 URL 추출 및 contents_queue _id 조회
================================================================================
📁 CSV 파일: /app/ksubscribe_share/test/refined_new_scarppings/naver_news_한국전력_deduped_20251101_20251203.csv
📝 출력 파일: /app/ksubscribe_share/test/test_ids_1101_1203.txt
🏢 기관 ID: A0010
================================================================================

1단계: CSV 파일에서 URL 추출 중...
   ✅ 349개의 URL 추출 완료

2단계: contents_queue에서 _id 조회 중...
📋 contents_queue에서 349개 URL 조회 중...
  ✅ 69522b07... - 남양주시, 민‧관‧군 합동 '재난대응 안전한국훈련'...
  ✅ 69522b08... - 글로벌전력산업 표준 논의의 장, 서울에서 열린다...
  ...

📊 조회 결과: 349건 (고유) / 349건 (CSV)

3단계: _id를 텍스트 파일로 저장 중...

✅ _id 저장 완료: /app/ksubscribe_share/test/test_ids_1101_1203.txt
   총 349건의 고유 _id 저장

================================================================================
✅ 모든 작업 완료!
================================================================================
```

### 3.3 결과 파일 확인

#### 텍스트 파일 형식

생성된 텍스트 파일은 한 줄에 하나의 ObjectId가 저장됩니다:

```
69522b07bce21ed1adfea616
69522b08bce21ed1adfea617
69522b09bce21ed1adfea618
...
```

#### 파일 위치

```
/app/ksubscribe_share/test/test_ids_1101_1203.txt
```

#### 호스트에서 확인

```bash
# Docker 컨테이너에서 호스트로 복사
docker cp ksubscribe_python_unified:/app/ksubscribe_share/test/test_ids_1101_1203.txt ./

# 파일 내용 확인
cat test_ids_1101_1203.txt | head -10
```

---

## 4. CSV 파일 형식

### 4.1 필수 컬럼

CSV 파일은 다음 컬럼을 포함해야 합니다:

| 컬럼명 | 설명 | 예시 |
|--------|------|------|
| `날짜` | 기사 발행일 | `2025-11-01` 또는 `20251101` |
| `기사 제목` | 기사 제목 | `"한국전력, 전력 수요 대비 공급 여유 확보"` |
| `기사 URL` | 기사 URL | `https://www.yna.co.kr/view/AKR20251101031000003` |

### 4.2 날짜 형식

다음 형식을 지원합니다:

- **YYYY-MM-DD**: `2025-11-01`
- **YYYYMMDD**: `20251101`
- **MM월 DD일**: `11월 01일` (연도는 2025로 가정)

### 4.3 CSV 파일 예시

```csv
날짜,구분,기사 제목,기사 URL
2025-11-01,,"남양주시, 민‧관‧군 합동 '재난대응 안전한국훈련'",https://sports.donga.com/region/article/all/20251101/132682399/1
2025-11-01,,"글로벌전력산업 표준 논의의 장, 서울에서 열린다",https://www.yna.co.kr/view/AKR20251101031000003?input=1195m
2025-11-02,,"AI·반도체전력수요 급등…'전력망 병목' 반도체 산업 리스크 부상",https://www.etnews.com/20251102000001
```

### 4.4 주의사항

- **인코딩**: CSV 파일은 `UTF-8` 또는 `UTF-8 with BOM` (`utf-8-sig`) 형식이어야 합니다.
- **기사 제목**: 제목에 쉼표나 따옴표가 포함된 경우, CSV 표준에 따라 적절히 이스케이프되어야 합니다.
- **URL 중복**: 동일한 URL이 이미 `contents_queue`에 존재하면 건너뜁니다.

---

## 5. 스크립트 상세 설명

### 5.1 import_csv_to_contents_queue.py

#### 주요 기능

- CSV 파일 읽기 및 파싱
- 날짜 형식 변환
- URL 중복 체크
- MongoDB `contents_queue`에 저장
- 저장 결과 통계 출력

#### 설정 상수

```python
CONTENT_ORG_ID = "A0010"  # 한국전력
CATE_ID = "B0010"         # 네이버 뉴스
COLLECT_KEYWORD = "한국전력"
```

#### 저장되는 필드

- `contentOrgId`: 기관 ID (A0010)
- `cateId`: 카테고리 ID (B0010)
- `title`: 기사 제목
- `url`: 기사 URL
- `shortUrl`: 랜덤 문자열 (5자)
- `pubDt`: 발행일 (ISODate 형식, UTC)
- `collectDt`: 수집일 (ISODate 형식, UTC, 현재 시간)
- `collectKeyword`: 수집 키워드 (한국전력)
- `_id`: MongoDB가 자동 생성

### 5.2 extract_oids_from_csv.py

#### 주요 기능

- CSV 파일에서 URL 목록 추출
- MongoDB `contents_queue`에서 URL로 문서 조회
- ObjectId 추출 및 중복 제거
- 텍스트 파일로 저장

#### 조회 조건

- `url`: CSV 파일의 URL 목록에 포함
- `contentOrgId`: A0010 (한국전력)
- `collectDt`: 오늘 날짜 (UTC 기준, 00:00:00 ~ 23:59:59)

#### 중복 처리

- 같은 URL에 대해 여러 문서가 있을 경우, 가장 최근 문서(`collectDt` 기준)만 선택
- 최종적으로 고유한 ObjectId만 저장

---

## 6. 실행 예시

### 6.1 전체 워크플로우 실행 예시

```bash
# 1단계: CSV 파일을 contents_queue에 저장
docker exec ksubscribe_python_unified python3 /app/ksubscribe_share/test/import_csv_to_contents_queue.py \
  /app/ksubscribe_share/test/refined_new_scarppings/naver_news_한국전력_deduped_20251101_20251203.csv

# 2단계: OID 추출 및 텍스트 파일 저장
docker exec ksubscribe_python_unified python3 /app/ksubscribe_share/test/extract_oids_from_csv.py \
  /app/ksubscribe_share/test/refined_new_scarppings/naver_news_한국전력_deduped_20251101_20251203.csv \
  test_ids_1101_1203

# 3단계: 결과 파일 확인
docker exec ksubscribe_python_unified wc -l /app/ksubscribe_share/test/test_ids_1101_1203.txt
docker exec ksubscribe_python_unified head -5 /app/ksubscribe_share/test/test_ids_1101_1203.txt
```

### 6.2 호스트에서 실행 (스크립트가 호스트에 있는 경우)

```bash
# CSV 파일을 Docker 컨테이너에 복사
docker cp ./naver_news_한국전력_deduped_20251101_20251203.csv \
  ksubscribe_python_unified:/app/ksubscribe_share/test/refined_new_scarppings/

# 1단계 실행
docker exec ksubscribe_python_unified python3 /app/ksubscribe_share/test/import_csv_to_contents_queue.py \
  /app/ksubscribe_share/test/refined_new_scarppings/naver_news_한국전력_deduped_20251101_20251203.csv

# 2단계 실행
docker exec ksubscribe_python_unified python3 /app/ksubscribe_share/test/extract_oids_from_csv.py \
  /app/ksubscribe_share/test/refined_new_scarppings/naver_news_한국전력_deduped_20251101_20251203.csv \
  test_ids_1101_1203

# 결과 파일을 호스트로 복사
docker cp ksubscribe_python_unified:/app/ksubscribe_share/test/test_ids_1101_1203.txt ./
```

---

## 7. 문제 해결

### 7.1 CSV 파일을 찾을 수 없음

**오류 메시지:**
```
❌ 오류: 파일을 찾을 수 없습니다: /path/to/file.csv
```

**해결 방법:**
- 파일 경로 확인
- Docker 컨테이너 내부 경로인지 확인
- 필요시 `docker cp`로 파일 복사

### 7.2 날짜 파싱 오류

**오류 메시지:**
```
⚠️  날짜 파싱 오류 (행 건너뜀): 날짜 형식을 인식할 수 없습니다: ...
```

**해결 방법:**
- 날짜 형식 확인 (YYYY-MM-DD, YYYYMMDD, MM월 DD일)
- CSV 파일의 날짜 컬럼 이름이 `날짜`인지 확인

### 7.3 OID가 추출되지 않음

**원인:**
- CSV 파일의 URL과 `contents_queue`의 URL이 일치하지 않음
- `collectDt`가 오늘 날짜가 아님
- `contentOrgId`가 일치하지 않음

**해결 방법:**
- 1단계 실행 후 바로 2단계 실행 (같은 날에 실행)
- URL 형식 확인 (공백, 인코딩 등)
- MongoDB에서 직접 확인:
  ```bash
  docker exec ksubscribe_python_unified python3 -c "
  from ksubscribe_share.db.mongoManager import MongoManager
  from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
  mongo = MongoManager()
  coll = mongo.getCollection('contents_queue')
  print(coll.count_documents({'contentOrgId': 'A0010'}))
  "
  ```

### 7.4 중복 URL 처리

**상황:**
- 동일한 URL이 이미 `contents_queue`에 존재

**동작:**
- `import_csv_to_contents_queue.py`는 자동으로 중복을 건너뜀
- `extract_oids_from_csv.py`는 가장 최근 문서만 선택

**확인:**
- 로그에서 "⏭️ 이미 존재하는 URL (건너뜀)" 메시지 확인

---

## 8. 주요 특징

### 8.1 자동 중복 제거

- `import_csv_to_contents_queue.py`: URL 기반 중복 체크
- `extract_oids_from_csv.py`: URL별 최신 문서만 선택

### 8.2 날짜 필터링

- `extract_oids_from_csv.py`는 오늘 날짜에 저장된 문서만 조회
- 같은 날에 1단계와 2단계를 실행해야 정확한 결과를 얻을 수 있음

### 8.3 로그 출력

- 각 단계별 상세한 진행 상황 출력
- 성공/실패/건너뜀 건수 통계 제공
- 오류 발생 시 상세한 에러 메시지 출력

### 8.4 에러 처리

- 파일 읽기 오류 처리
- 날짜 파싱 오류 처리
- MongoDB 연결 오류 처리
- 부분 실패 시에도 계속 진행

---

## 9. 후속 작업

### 9.1 LLM 평가 실행

생성된 OID 텍스트 파일은 `test_llm_evaluation.py`에서 사용할 수 있습니다:

```bash
docker exec ksubscribe_python_unified python3 /app/ksubscribe_share/test/test_llm_evaluation.py \
  --ollama-model gpt-oss:20b \
  --test-ids test_ids_1101_1203.txt
```

### 9.2 배치 실행

여러 CSV 파일을 처리하는 경우:

```bash
#!/bin/bash
CSV_FILES=(
  "naver_news_한국전력_deduped_20251101_20251115.csv"
  "naver_news_한국전력_deduped_20251116_20251130.csv"
)

for csv_file in "${CSV_FILES[@]}"; do
  echo "처리 중: $csv_file"
  
  # 1단계
  docker exec ksubscribe_python_unified python3 /app/ksubscribe_share/test/import_csv_to_contents_queue.py \
    "/app/ksubscribe_share/test/refined_new_scarppings/$csv_file"
  
  # 2단계
  output_name=$(basename "$csv_file" .csv | sed 's/naver_news_한국전력_deduped_//')
  docker exec ksubscribe_python_unified python3 /app/ksubscribe_share/test/extract_oids_from_csv.py \
    "/app/ksubscribe_share/test/refined_new_scarppings/$csv_file" \
    "test_ids_${output_name}"
done
```

---

## 10. 참고 사항

### 10.1 관련 스크립트

- `remove_duplicate_articles_from_excel.py`: Excel 파일에서 중복 제거 후 CSV 생성
- `test_llm_evaluation.py`: OID 텍스트 파일을 사용하여 LLM 평가 실행

### 10.2 MongoDB 컬렉션

- **contents_queue**: 수집 대기 중인 기사 정보
- **contents**: LLM 분석이 완료된 기사 정보

### 10.3 시간대

- 모든 날짜/시간은 UTC 기준으로 저장됩니다.
- 로그는 KST(한국 시간)로 표시됩니다.

---

**작성자**: Auto  
**최종 수정일**: 2025-12-29



