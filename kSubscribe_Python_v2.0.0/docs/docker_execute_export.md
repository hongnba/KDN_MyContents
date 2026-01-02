# 도커 컨테이너에서 export_contents_to_excel.py 실행 가이드

> 작성일: 2025-01-XX  
> 목적: 도커 컨테이너 환경에서 날짜별 데이터를 Excel로 내보내기

---

## 📋 사전 확인

### 컨테이너 이름 확인
```bash
docker ps
```

예상 컨테이너 이름: `ksubscribe_python_unified`

---

## 🚀 실행 방법

### 방법 1: 명령줄 인자로 날짜 전달 (권장)

```bash
docker exec -it ksubscribe_python_unified python /app/export_contents_to_excel.py 2025-11-22 2025-11-23 2025-11-24 2025-11-25 2025-11-26
```

### 방법 2: 스크립트 내 날짜 수정 후 실행

먼저 컨테이너에 접속:
```bash
docker exec -it ksubscribe_python_unified bash
```

스크립트 수정:
```bash
vi /app/export_contents_to_excel.py
# 또는
nano /app/export_contents_to_excel.py
```

`main()` 함수에서 날짜 리스트 수정:
```python
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
python /app/export_contents_to_excel.py
```

---

## 📂 출력 파일 위치

### 컨테이너 내부
- CSV: `/app/exports/contents_YYYY-MM-DD.csv`
- Excel: `/app/exports/contents_export_YYYYMMDD_HHMMSS.xlsx`

### 호스트로 파일 복사

```bash
# Excel 파일 복사
docker cp ksubscribe_python_unified:/app/exports/contents_export_*.xlsx ./

# 모든 CSV 파일 복사
docker cp ksubscribe_python_unified:/app/exports/contents_2025-11-*.csv ./

# 전체 exports 디렉토리 복사
docker cp ksubscribe_python_unified:/app/exports ./exports_from_container
```

---

## 🔍 실행 예시

### 전체 명령어 (2025-11-22 ~ 2025-11-26)

```bash
# 1. 스크립트 실행
docker exec -it ksubscribe_python_unified python /app/export_contents_to_excel.py 2025-11-22 2025-11-23 2025-11-24 2025-11-25 2025-11-26

# 2. 결과 확인
docker exec -it ksubscribe_python_unified ls -lh /app/exports/

# 3. 파일 복사
docker cp ksubscribe_python_unified:/app/exports/contents_export_*.xlsx ./
docker cp ksubscribe_python_unified:/app/exports/contents_2025-11-*.csv ./
```

### 출력 예시

```
📊 MongoDB 쿼리 시작...
📅 처리할 날짜: 2025-11-22, 2025-11-23, 2025-11-24, 2025-11-25, 2025-11-26
📁 출력 디렉토리: /app/exports
📄 Excel 파일: /app/exports/contents_export_20250115_143022.xlsx

🔍 [2025-11-22] 쿼리 실행 중...
   ✅ CSV 저장: /app/exports/contents_2025-11-22.csv (150개 문서)
   ✅ Excel 시트 추가: 2025-11-22 (150개 문서)

🔍 [2025-11-23] 쿼리 실행 중...
   ✅ CSV 저장: /app/exports/contents_2025-11-23.csv (200개 문서)
   ✅ Excel 시트 추가: 2025-11-23 (200개 문서)

...

✅ 완료!
📊 총 850개 문서 처리
📄 Excel 파일: /app/exports/contents_export_20250115_143022.xlsx
📁 CSV 파일들: /app/exports
```

---

## 🐛 문제 해결

### 컨테이너 이름이 다른 경우

```bash
# 컨테이너 이름 확인
docker ps --format "table {{.Names}}\t{{.Image}}"

# 확인된 이름으로 변경
docker exec -it <실제_컨테이너_이름> python /app/export_contents_to_excel.py 2025-11-22 2025-11-26
```

### 스크립트가 없는 경우

스크립트를 컨테이너에 복사:
```bash
docker cp export_contents_to_excel.py ksubscribe_python_unified:/app/
```

### exports 디렉토리가 없는 경우

컨테이너 내에서 생성:
```bash
docker exec -it ksubscribe_python_unified mkdir -p /app/exports
```

---

## 📝 간단한 원라이너

```bash
# 2025-11-22 ~ 2025-11-26 실행 및 파일 복사
docker exec ksubscribe_python_unified python /app/export_contents_to_excel.py 2025-11-22 2025-11-23 2025-11-24 2025-11-25 2025-11-26 && \
docker cp ksubscribe_python_unified:/app/exports/contents_export_*.xlsx ./ && \
docker cp ksubscribe_python_unified:/app/exports/contents_2025-11-*.csv ./
```

---

**문서 작성자**: AI Assistant  
**최종 수정일**: 2025-01-XX


