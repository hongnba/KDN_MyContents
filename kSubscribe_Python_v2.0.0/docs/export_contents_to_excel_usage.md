# export_contents_to_excel.py 사용 가이드

> 작성일: 2025-01-XX  
> 목적: MongoDB contents collection에서 날짜별로 데이터를 조회하여 CSV/Excel로 저장

---

## 📋 기능

- 날짜 리스트를 입력받아 MongoDB에서 데이터 조회
- 각 날짜별로 중복 제거 (url 기준, metaAnalyzeDt 최신 기준)
- CSV 파일로 저장 (날짜별)
- Excel 파일로 변환 (시트 이름은 날짜)

---

## 🔧 필수 패키지

```bash
pip install pandas openpyxl pymongo pytz
```

---

## 📝 사용법

### 방법 1: 스크립트 내에서 날짜 리스트 수정

```python
# export_contents_to_excel.py 파일 열기
# main() 함수에서 date_list 수정:

date_list = [
    "2025-11-22",
    "2025-11-23",
    "2025-11-24",
    "2025-11-25",
    "2025-11-26"
]
```

그리고 실행:
```bash
python export_contents_to_excel.py
```

### 방법 2: 명령줄 인자로 날짜 전달

```bash
python export_contents_to_excel.py 2025-11-22 2025-11-23 2025-11-26
```

### 방법 3: Python 코드에서 직접 호출

```python
from export_contents_to_excel import export_to_csv_and_excel

date_list = ["2025-11-22", "2025-11-23", "2025-11-26"]
export_to_csv_and_excel(date_list, output_dir="./my_exports")
```

---

## 📂 출력 파일

### CSV 파일
- 위치: `./exports/` (또는 지정한 디렉토리)
- 파일명: `contents_YYYY-MM-DD.csv`
- 예시: `contents_2025-11-22.csv`

### Excel 파일
- 위치: `./exports/` (또는 지정한 디렉토리)
- 파일명: `contents_export_YYYYMMDD_HHMMSS.xlsx`
- 예시: `contents_export_20250115_143022.xlsx`
- 시트: 각 날짜별로 시트 생성 (시트 이름 = 날짜)

---

## 🔍 쿼리 로직

1. **날짜 범위 필터링**: `pubDt`가 해당 날짜인 문서만 선택
2. **중복 제거**: `url` 기준으로 그룹화
3. **최신 선택**: `metaAnalyzeDt`가 최신인 문서만 선택
4. **정렬**: `pubDt` 오름차순, `metaAnalyzeDt` 내림차순

---

## 📊 출력 예시

```
📊 MongoDB 쿼리 시작...
📅 처리할 날짜: 2025-11-22, 2025-11-23, 2025-11-26
📁 출력 디렉토리: ./exports
📄 Excel 파일: ./exports/contents_export_20250115_143022.xlsx

🔍 [2025-11-22] 쿼리 실행 중...
   ✅ CSV 저장: ./exports/contents_2025-11-22.csv (150개 문서)
   ✅ Excel 시트 추가: 2025-11-22 (150개 문서)

🔍 [2025-11-23] 쿼리 실행 중...
   ✅ CSV 저장: ./exports/contents_2025-11-23.csv (200개 문서)
   ✅ Excel 시트 추가: 2025-11-23 (200개 문서)

🔍 [2025-11-26] 쿼리 실행 중...
   ✅ CSV 저장: ./exports/contents_2025-11-26.csv (180개 문서)
   ✅ Excel 시트 추가: 2025-11-26 (180개 문서)

✅ 완료!
📊 총 530개 문서 처리
📄 Excel 파일: ./exports/contents_export_20250115_143022.xlsx
📁 CSV 파일들: ./exports
```

---

## ⚙️ 설정

### 출력 디렉토리 변경

```python
export_to_csv_and_excel(date_list, output_dir="./my_custom_exports")
```

### MongoDB 연결 설정

기본적으로 `ksubscribe_share.config`의 설정을 사용합니다.
환경 변수로도 설정 가능:

```bash
export MONGO_IP=localhost
export MONGO_PORT=27017
export MONGO_DB_NAME=mycontents
```

---

## 🐛 문제 해결

### ImportError 발생 시

```bash
# PYTHONPATH 설정
export PYTHONPATH=/home/themiraclesoft/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src:$PYTHONPATH

# 또는 스크립트 실행 시
PYTHONPATH=/home/themiraclesoft/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src python export_contents_to_excel.py
```

### openpyxl 설치 필요

```bash
pip install openpyxl
```

### 날짜 형식 오류

날짜는 반드시 `YYYY-MM-DD` 형식이어야 합니다:
- ✅ 올바른 형식: `"2025-11-22"`
- ❌ 잘못된 형식: `"2025/11/22"`, `"11-22-2025"`

---

## 📝 예제 코드

### 여러 날짜 범위 처리

```python
from datetime import datetime, timedelta
from export_contents_to_excel import export_to_csv_and_excel

# 2025년 11월 전체 날짜 생성
start_date = datetime(2025, 11, 1)
end_date = datetime(2025, 11, 30)

date_list = []
current_date = start_date
while current_date <= end_date:
    date_list.append(current_date.strftime("%Y-%m-%d"))
    current_date += timedelta(days=1)

export_to_csv_and_excel(date_list)
```

### 특정 요일만 선택

```python
from datetime import datetime, timedelta
from export_contents_to_excel import export_to_csv_and_excel

# 2025년 11월의 월요일만 선택
start_date = datetime(2025, 11, 1)
end_date = datetime(2025, 11, 30)

date_list = []
current_date = start_date
while current_date <= end_date:
    if current_date.weekday() == 0:  # 월요일 = 0
        date_list.append(current_date.strftime("%Y-%m-%d"))
    current_date += timedelta(days=1)

export_to_csv_and_excel(date_list)
```

---

**문서 작성자**: AI Assistant  
**최종 수정일**: 2025-01-XX


