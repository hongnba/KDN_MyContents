# export_contents_to_excel.sh 사용 설명서

## 📋 개요

`export_contents_to_excel.sh`는 MongoDB의 `contents` 컬렉션에서 날짜별로 데이터를 조회하여 Excel 파일로 내보내는 스크립트입니다.

### 주요 기능
- MongoDB `contents` 컬렉션에서 날짜별 데이터 조회
- `contentsOrgId`가 `A0010`인 문서만 필터링
- URL 기준 중복 제거 (최신 `metaAnalyzeDt` 기준)
- 중첩된 JSON 구조를 최종 단계까지 펼쳐서 저장
- 각 날짜를 별도 Excel 시트로 저장
- 데이터를 세로 방향(행=필드명, 열=값)으로 저장

---

## 🚀 사용법

### 기본 명령어 형식

```bash
./export_contents_to_excel.sh <날짜1> <날짜2> ...
```

### 실행 예시

#### 1. 단일 날짜 조회
```bash
./export_contents_to_excel.sh 2025-11-22
```

#### 2. 여러 날짜 조회
```bash
./export_contents_to_excel.sh 2025-11-22 2025-11-26
```

#### 3. 여러 날짜 조회 (3개 이상)
```bash
./export_contents_to_excel.sh 2025-11-22 2025-11-23 2025-11-24 2025-11-25 2025-11-26
```

#### 4. 절대 경로로 실행
```bash
/home/themiraclesoft/mycontents/export_contents_to_excel.sh 2025-11-22 2025-11-26
```

---

## 📁 출력 파일 위치

### 저장 경로
```
/home/themiraclesoft/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src/ksubscribe_share/test/daily_summary/
```

### 파일명 형식
```
contents_export_YYYYMMDD_HHMMSS.xlsx
```

예시: `contents_export_20251226_101233.xlsx`

---

## 📊 Excel 파일 구조

### 시트 구조
- 각 날짜가 별도의 Excel 시트로 생성됩니다
- 시트 이름: 날짜 (예: `2025-11-22`, `2025-11-26`)

### 데이터 구조
- **세로 방향 저장**: 필드명이 행(row)으로, 값이 열(column)로 저장됩니다
- **중첩 구조 펼치기**: 중첩된 JSON 구조가 최종 단계까지 펼쳐집니다

#### 예시: 중첩 구조 펼치기
```
원본 구조:
{
  "contentsRaw": {
    "title": "제목",
    "contents": "내용"
  },
  "contentsMeta": {
    "sentiments": [
      {
        "positiveRatio": 0.5,
        "positiveKeywords": ["키워드1", "키워드2"]
      }
    ]
  }
}

펼쳐진 구조 (Excel 컬럼):
- contentsRaw.title
- contentsRaw.contents
- contentsMeta.sentiments.0.positiveRatio
- contentsMeta.sentiments.0.positiveKeywords.0
- contentsMeta.sentiments.0.positiveKeywords.1
```

---

## ⚙️ 필터 조건

### 자동 적용 필터
1. **날짜 필터**: `pubDt`가 지정한 날짜 범위 내
   - 시작: 해당 날짜 00:00:00 (UTC)
   - 종료: 해당 날짜 23:59:59 (UTC)

2. **기관 필터**: `contentsOrgId = "A0010"` (한국전력)

3. **중복 제거**: 동일한 `url`을 가진 문서 중 `metaAnalyzeDt`가 최신인 것만 선택

---

## 🔧 사전 요구사항

### 1. Docker 컨테이너
- 컨테이너 이름: `ksubscribe_python_unified`
- 컨테이너가 실행 중이어야 합니다

### 2. 실행 권한
```bash
chmod +x export_contents_to_excel.sh
```

### 3. Python 스크립트
- Python 스크립트 경로: `/home/themiraclesoft/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src/export_contents_to_excel.py`
- 스크립트가 존재해야 합니다

### 4. MongoDB 연결
- MongoDB가 정상적으로 연결되어 있어야 합니다
- `contents` 컬렉션에 데이터가 있어야 합니다

---

## 📝 실행 과정

### 1단계: 스크립트 파일 복사
```bash
docker cp <Python 스크립트 경로> ksubscribe_python_unified:/app/
```

### 2단계: MongoDB 쿼리 실행
```bash
docker exec ksubscribe_python_unified python /app/export_contents_to_excel.py <날짜들>
```

### 3단계: Excel 파일 생성
- 컨테이너 내부: `/app/ksubscribe_share/test/daily_summary/`
- 각 날짜별로 시트 생성
- 중첩 구조 펼치기 및 세로 방향 저장

### 4단계: 파일 복사
```bash
docker cp ksubscribe_python_unified:/app/ksubscribe_share/test/daily_summary/<파일명> <호스트 경로>
```

---

## 📤 실행 결과 예시

```bash
$ ./export_contents_to_excel.sh 2025-11-22 2025-11-26

🚀 Excel 내보내기 시작...
📅 날짜: 2025-11-22 2025-11-26

📊 MongoDB 쿼리 실행 중...
📅 명령줄 인자로 받은 날짜: ['2025-11-22', '2025-11-26']
📊 MongoDB 쿼리 시작...
📅 처리할 날짜: 2025-11-22, 2025-11-26
📄 Excel 파일: /app/ksubscribe_share/test/daily_summary/contents_export_20251226_101233.xlsx

🔍 [2025-11-22] 쿼리 실행 중...
   ✅ Excel 시트 추가: 2025-11-22 (2개 문서, 세로 방향)

🔍 [2025-11-26] 쿼리 실행 중...
   ✅ Excel 시트 추가: 2025-11-26 (3개 문서, 세로 방향)

✅ 완료!
📊 총 5개 문서 처리
📄 Excel 파일 저장 경로: /app/ksubscribe_share/test/daily_summary/contents_export_20251226_101233.xlsx
📁 절대 경로: /app/ksubscribe_share/test/daily_summary/contents_export_20251226_101233.xlsx

📁 파일 복사 중...
✅ 파일 복사 완료: contents_export_20251226_101233.xlsx
📄 저장 경로: /home/themiraclesoft/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src/ksubscribe_share/test/daily_summary/contents_export_20251226_101233.xlsx
📁 절대 경로: /home/themiraclesoft/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src/ksubscribe_share/test/daily_summary/contents_export_20251226_101233.xlsx

✅ 완료!
```

---

## ⚠️ 오류 처리

### 오류 1: 날짜 인자 없음
```bash
$ ./export_contents_to_excel.sh
❌ 사용법: ./export_contents_to_excel.sh <날짜1> <날짜2> ...
예시: ./export_contents_to_excel.sh 2025-11-22 2025-11-26
```

### 오류 2: 컨테이너 없음
```bash
❌ 실행 실패 (종료 코드: 1)
```
- 해결: Docker 컨테이너가 실행 중인지 확인
```bash
docker ps | grep ksubscribe_python_unified
```

### 오류 3: Excel 파일 없음
```bash
❌ Excel 파일을 찾을 수 없습니다.
디버깅: 컨테이너 내부 파일 목록:
  /app/ksubscribe_share/test/daily_summary에 xlsx 파일 없음
```
- 해결: MongoDB 쿼리 결과가 없거나, 날짜 범위에 데이터가 없는지 확인

---

## 🔍 디버깅

### 1. 컨테이너 상태 확인
```bash
docker ps -a | grep ksubscribe_python_unified
```

### 2. 컨테이너 내부 파일 확인
```bash
docker exec ksubscribe_python_unified ls -la /app/ksubscribe_share/test/daily_summary/
```

### 3. Python 스크립트 직접 실행 (디버깅)
```bash
docker exec ksubscribe_python_unified python /app/export_contents_to_excel.py 2025-11-22
```

### 4. MongoDB 데이터 확인
```bash
docker exec ksubscribe_mongodb mongo mycontents --eval "db.contents.find({contentsOrgId: 'A0010', pubDt: ISODate('2025-11-22')}).count()"
```

---

## 📌 주요 특징

### 1. 위치 독립성
- 스크립트를 어느 위치에서 실행해도 동일한 경로에 저장됩니다
- 출력 경로는 절대 경로로 고정되어 있습니다

### 2. 중복 제거
- 동일한 `url`을 가진 문서는 `metaAnalyzeDt`가 최신인 것만 선택됩니다
- MongoDB aggregation pipeline을 사용하여 효율적으로 처리합니다

### 3. 데이터 구조 보존
- 중첩된 JSON 구조를 최종 단계까지 펼쳐서 모든 필드를 개별 컬럼으로 저장합니다
- 리스트 인덱스도 포함하여 저장됩니다 (예: `sentiments.0.positiveRatio`)

### 4. 세로 방향 저장
- 필드명이 행(row)으로, 값이 열(column)로 저장됩니다
- 여러 문서를 비교하기 쉽습니다

---

## 📚 관련 파일

- **Python 스크립트**: `/home/themiraclesoft/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src/export_contents_to_excel.py`
- **출력 디렉토리**: `/home/themiraclesoft/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src/ksubscribe_share/test/daily_summary/`
- **Docker 컨테이너**: `ksubscribe_python_unified`
- **MongoDB 컬렉션**: `contents`

---

## 🆘 문제 해결

### Q: "executable file not found" 오류
**A**: 실행 권한이 없습니다.
```bash
chmod +x export_contents_to_excel.sh
```

### Q: "No such file or directory" 오류
**A**: Python 스크립트 경로를 확인하세요.
```bash
ls -la /home/themiraclesoft/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src/export_contents_to_excel.py
```

### Q: 데이터가 조회되지 않음
**A**: 다음을 확인하세요:
1. 날짜 형식이 올바른지 (`YYYY-MM-DD`)
2. `contentsOrgId`가 `A0010`인 데이터가 있는지
3. 해당 날짜에 `pubDt`가 있는지

### Q: Excel 파일이 생성되지 않음
**A**: 컨테이너 내부 디렉토리 권한을 확인하세요.
```bash
docker exec ksubscribe_python_unified ls -la /app/ksubscribe_share/test/daily_summary/
```

---

## 📅 버전 정보

- **작성일**: 2025-12-26
- **스크립트 버전**: 1.0
- **Python 버전**: Python 3.x
- **필요 패키지**: pandas, openpyxl, pymongo

---

## 📞 문의

문제가 발생하거나 개선 사항이 있으면 개발팀에 문의하세요.

