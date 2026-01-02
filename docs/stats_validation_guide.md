# Stats 검증 가이드

이 문서는 `weekly_stats`와 `daily_stats` 컬렉션의 데이터를 검증하는 방법을 설명합니다.

## 목차

1. [개요](#개요)
2. [실행 방법](#실행-방법)
3. [검증 항목](#검증-항목)
4. [검증 방법](#검증-방법)
5. [결과 파일](#결과-파일)

---

## 개요

이 검증 도구는 MongoDB의 `contents` 컬렉션에서 직접 계산한 통계와 `weekly_stats` 또는 `daily_stats` 컬렉션에 저장된 통계를 비교하여 데이터의 정확성을 검증합니다.

### 주요 기능

- **통계 검증**: 기사 수, 긍정/부정/중립 기사 수, 평균 비율 비교
- **키워드 검증**: 키워드 리스트 및 키워드별 출현 회수 비교
- **자동 리포트 생성**: 엑셀 및 CSV 파일로 비교 결과 저장

---

## 실행 방법

### 1. Weekly Stats 검증

#### 기본 실행 (기본값 사용)
```bash
cd /home/themiraclesoft/mycontents
./run_weekly_stats_comparison.sh
```

#### 커스텀 파라미터로 실행
```bash
./run_weekly_stats_comparison.sh [org_id] [start_date] [end_date]
```

**예시:**
```bash
./run_weekly_stats_comparison.sh A0010 2025-12-24 2025-12-30
```

**파라미터:**
- `org_id`: 기관 ID (예: A0010)
- `start_date`: 시작 날짜 (YYYY-MM-DD 형식, 포함)
- `end_date`: 종료 날짜 (YYYY-MM-DD 형식, 미포함)

**기본값:**
- `org_id`: A0010
- `start_date`: 2025-12-24
- `end_date`: 2025-12-30

### 2. Daily Stats 검증

#### 기본 실행 (기본값 사용)
```bash
cd /home/themiraclesoft/mycontents
./run_daily_stats_comparison.sh
```

#### 커스텀 파라미터로 실행
```bash
./run_daily_stats_comparison.sh [org_id] [target_date]
```

**예시:**
```bash
./run_daily_stats_comparison.sh A0010 2025-12-30
```

**파라미터:**
- `org_id`: 기관 ID (예: A0010)
- `target_date`: 조회할 날짜 (YYYY-MM-DD 형식)

**기본값:**
- `org_id`: A0010
- `target_date`: 2025-12-30

---

## 검증 항목

### 1. 통계 검증 (Stats Comparison)

다음 7가지 항목을 검증합니다:

| 항목 | 설명 | 계산 방법 |
|------|------|-----------|
| `totalContentsCounts` | 전체 기사 수 | contents에서 조회된 기사 수 |
| `totalPositiveContentsCount` | 긍정 기사 수 | positiveRatio > 50인 기사 수 |
| `totalNegativeContentsCount` | 부정 기사 수 | negativeRatio > 50인 기사 수 |
| `totalNeutralContentsCount` | 중립 기사 수 | 나머지 기사 수 |
| `averagePositiveRatio` | 평균 긍정 비율 | (긍정 기사 수 / 전체 기사 수) × 100 |
| `averageNegativeRatio` | 평균 부정 비율 | (부정 기사 수 / 전체 기사 수) × 100 |
| `averageNeutralRatio` | 평균 중립 비율 | (중립 기사 수 / 전체 기사 수) × 100 |

#### 분류 로직

각 기사는 다음 로직에 따라 분류됩니다:

1. **긍정**: `positiveRatio > 50`
2. **부정**: `negativeRatio > 50`
3. **중립**: 위 두 조건에 해당하지 않는 경우

> **참고**: 평균 비율은 각 기사의 ratio를 평균내는 것이 아니라, 분류된 기사 수를 전체 기사 수로 나눈 비율입니다.

### 2. 키워드 회수 검증 (Keyword Count Comparison)

#### 긍정 키워드 회수 비교
- `contents`에서 추출한 긍정 키워드별 출현 회수
- `weekly_stats` 또는 `daily_stats`의 `positiveKeywordMap`과 비교

#### 부정 키워드 회수 비교
- `contents`에서 추출한 부정 키워드별 출현 회수
- `weekly_stats` 또는 `daily_stats`의 `negativeKeywordMap`과 비교

**비교 항목:**
- 키워드 일치 여부: 키워드가 양쪽 모두에 존재하는지 확인
- 회수 일치 여부: 키워드의 출현 회수가 일치하는지 확인

### 3. 키워드 리스트 검증 (Keyword List Comparison) - Weekly Only

#### 긍정 키워드 리스트 비교
- `contents`에서 추출한 긍정 키워드 리스트
- `weekly_stats`의 `totalPositiveKeywordList`와 비교

#### 부정 키워드 리스트 비교
- `contents`에서 추출한 부정 키워드 리스트
- `weekly_stats`의 `totalNegativeKeywordList`와 비교

**비교 항목:**
- 키워드 존재 여부: 키워드가 양쪽 모두에 존재하는지 확인

---

## 검증 방법

### 1. Contents 데이터 조회

#### Weekly Stats 검증
- **기간**: `start_date` ~ `end_date` (KST 기준)
- **조건**: 
  - `contentsOrgId` = 지정된 `org_id`
  - `pubDt`가 지정된 기간 내
  - `metaSucYN` = 'Y' (분석 완료된 기사만)

#### Daily Stats 검증
- **날짜**: `target_date` (KST 기준)
- **조건**:
  - `contentsOrgId` = 지정된 `org_id`
  - `pubDt`가 지정된 날짜
  - `metaSucYN` = 'Y' (분석 완료된 기사만)

### 2. 통계 계산

#### 기사 분류
각 기사의 `contentsMeta.sentiments`에서 해당 `org_id`의 `positiveRatio`와 `negativeRatio`를 확인하여 분류합니다.

#### 키워드 추출
- `contentsMeta.sentiments[].positiveKeywords`에서 긍정 키워드 추출
- `contentsMeta.sentiments[].negativeKeywords`에서 부정 키워드 추출
- `Counter`를 사용하여 키워드별 출현 회수 계산

### 3. Stats 데이터 조회

#### Weekly Stats
- **조건**: `orgId` = 지정된 `org_id`, `end_date`가 지정된 `end_date`와 일치
- **조회 필드**: 
  - `totalContentsCounts`
  - `totalPositiveContentsCount`
  - `totalNegativeContentsCount`
  - `totalNeutralContentsCount`
  - `averagePositiveRatio`
  - `averageNegativeRatio`
  - `averageNeutralRatio`
  - `positiveKeywordMap`
  - `negativeKeywordMap`
  - `totalPositiveKeywordList`
  - `totalNegativeKeywordList`

#### Daily Stats
- **조건**: `orgId` = 지정된 `org_id`, `last_calculate_date`가 지정된 `target_date`와 일치
- **조회 필드**:
  - `totalContentsCounts`
  - `totalPositiveContentsCount`
  - `totalNegativeContentsCount`
  - `totalNeutralContentsCount`
  - `averagePositiveRatio`
  - `averageNegativeRatio`
  - `averageNeutralRatio`
  - `positiveKeywordMap`
  - `negativeKeywordMap`

### 4. 비교 및 검증

#### 통계 비교
- contents에서 계산한 값과 stats의 값을 직접 비교
- 일치 여부를 1(일치) 또는 0(불일치)로 표시
- float 값은 소수점 2자리까지 비교 (오차 0.01 이내)

#### 키워드 비교
- 모든 키워드를 오름차순으로 정렬하여 비교
- 키워드 존재 여부 및 출현 회수 일치 여부 확인

---

## 결과 파일

### Weekly Stats 검증 결과

**저장 위치:**
- 로컬: `/home/themiraclesoft/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src/ksubscribe_share/test/weekly_comparison_result/`
- 컨테이너: `/app/ksubscribe_share/test/weekly_comparison_result/`

**생성 파일:**

1. **엑셀 파일**
   - 파일명: `keyword_comparison_results_{org_id}_{start_date}_{end_date}_{생성날짜시간}.xlsx`
   - 예시: `keyword_comparison_results_A0010_20251224_20251230_20260102_123928.xlsx`
   - 시트:
     - `stats_comparison`: 통계 비교 결과
     - `positive_count_comparison`: 긍정 키워드 회수 비교
     - `negative_count_comparison`: 부정 키워드 회수 비교
     - `positive_list_comparison`: 긍정 키워드 리스트 비교
     - `negative_list_comparison`: 부정 키워드 리스트 비교

2. **CSV 파일**
   - `stats_comparison_{org_id}_{start_date}_{end_date}.csv`: 통계 비교
   - `positive_keyword_count_comparison_{org_id}_{start_date}_{end_date}.csv`: 긍정 키워드 회수 비교
   - `negative_keyword_count_comparison_{org_id}_{start_date}_{end_date}.csv`: 부정 키워드 회수 비교
   - `positive_keyword_list_comparison_{org_id}_{start_date}_{end_date}.csv`: 긍정 키워드 리스트 비교
   - `negative_keyword_list_comparison_{org_id}_{start_date}_{end_date}.csv`: 부정 키워드 리스트 비교

### Daily Stats 검증 결과

**저장 위치:**
- 로컬: `/home/themiraclesoft/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src/ksubscribe_share/test/daily_comparison_result/`
- 컨테이너: `/app/ksubscribe_share/test/daily_comparison_result/`

**생성 파일:**

1. **엑셀 파일**
   - 파일명: `keyword_comparison_daily_stats_{org_id}_{target_date}_{생성날짜시간}.xlsx`
   - 예시: `keyword_comparison_daily_stats_A0010_20251230_20260102_123939.xlsx`
   - 시트:
     - `stats_comparison`: 통계 비교 결과
     - `positive_count_comparison`: 긍정 키워드 회수 비교
     - `negative_count_comparison`: 부정 키워드 회수 비교

2. **CSV 파일**
   - `stats_comparison_daily_{org_id}_{target_date}.csv`: 통계 비교
   - `positive_keyword_count_comparison_daily_{org_id}_{target_date}.csv`: 긍정 키워드 회수 비교
   - `negative_keyword_count_comparison_daily_{org_id}_{target_date}.csv`: 부정 키워드 회수 비교

### 파일명 날짜 형식

- 파일명에 포함된 날짜/시간은 **한국 시간(KST)** 기준입니다.
- 형식: `YYYYMMDD_HHMMSS` (예: `20260102_123928`)

---

## 주의사항

1. **시간대 변환**
   - 입력 날짜는 KST(한국 시간) 기준입니다.
   - MongoDB에 저장된 데이터는 UTC 기준이므로, 자동으로 변환하여 조회합니다.

2. **분류 로직**
   - 현재 분류 로직은 `positiveRatio > 50` 또는 `negativeRatio > 50` 기준입니다.
   - 이 로직은 변경될 수 있으므로, 코드를 확인하여 최신 로직을 확인하세요.

3. **데이터 일치**
   - 통계 값이 일치하지 않는 경우, 다음을 확인하세요:
     - 조회 기간/날짜가 정확한지
     - `metaSucYN = 'Y'` 조건이 올바르게 적용되었는지
     - 분류 로직이 stats 생성 시와 동일한지

4. **파일 덮어쓰기 방지**
   - 파일명에 생성 날짜/시간이 포함되어 있어 덮어쓰기가 발생하지 않습니다.
   - 여러 번 실행해도 각각의 결과 파일이 생성됩니다.

---

## 문제 해결

### 컨테이너가 실행되지 않는 경우
```bash
# 컨테이너 상태 확인
docker ps | grep ksubscribe_python_unified

# 컨테이너가 없다면 시작
docker-compose up -d
```

### 결과 파일을 찾을 수 없는 경우
- 로컬 경로와 컨테이너 내부 경로가 볼륨 마운트로 연결되어 있는지 확인
- 파일 권한 문제가 있는지 확인

### 통계 값이 일치하지 않는 경우
- 조회 기간/날짜 확인
- `metaSucYN` 조건 확인
- 분류 로직 확인 (코드 내 `classify_contents_by_sentiment` 함수)

---

## 추가 정보

- Python 스크립트 위치:
  - Weekly: `/app/ksubscribe_share/test/keyword_comparison_weekly_stats.py`
  - Daily: `/app/ksubscribe_share/test/keyword_comparison_daily_stats.py`
- Shell 스크립트 위치:
  - Weekly: `/home/themiraclesoft/mycontents/run_weekly_stats_comparison.sh`
  - Daily: `/home/themiraclesoft/mycontents/run_daily_stats_comparison.sh`

