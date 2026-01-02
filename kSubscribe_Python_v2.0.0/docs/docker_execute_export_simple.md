# 도커 컨테이너에서 export_contents_to_excel.py 실행 (간단 버전)

## 🚀 실행 명령어 (2025-11-22, 2025-11-26)

```bash
docker exec ksubscribe_python_unified python /app/export_contents_to_excel.py 2025-11-22 2025-11-26 && docker exec ksubscribe_python_unified ls -lh /app/exports/ && docker cp ksubscribe_python_unified:/app/exports/contents_export_*.xlsx ./ && docker cp ksubscribe_python_unified:/app/exports/contents_2025-11-22.csv ./ && docker cp ksubscribe_python_unified:/app/exports/contents_2025-11-26.csv ./
```

## 📋 단계별 설명

1. **실행**: `docker exec ksubscribe_python_unified python /app/export_contents_to_excel.py 2025-11-22 2025-11-26`
2. **결과 확인**: `docker exec ksubscribe_python_unified ls -lh /app/exports/`
3. **파일 복사**: Excel과 CSV 파일들을 현재 디렉토리로 복사

## 📂 출력 파일

- Excel: `contents_export_YYYYMMDD_HHMMSS.xlsx` (시트: "2025-11-22", "2025-11-26")
- CSV: `contents_2025-11-22.csv`, `contents_2025-11-26.csv`


