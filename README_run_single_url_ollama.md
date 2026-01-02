# run_single_url_ollama.py 사용법

## 🎯 목적
MongoDB에 저장된 기사 1건에 대해 Ollama 5가지 분석을 실행합니다.

## 📋 필요한 정보

### 최소 정보 (이미 MongoDB에 저장된 경우)
- **URL만 있으면 됩니다!**

### 새로운 기사를 추가하는 경우
MongoDB에 먼저 다음 정보를 저장해야 합니다:

| 필드 | 설명 | 예시 | 필수 |
|------|------|------|------|
| `url` | 기사 URL | `https://www.yna.co.kr/view/AKR20251021023400003` | ✅ |
| `title` | 기사 제목 | `"한전 송전망 건설사업 절반이 '지연'..."` | ✅ |
| `contentsRaw.contents` | 기사 본문 | `"박정 의원 자료..."` | ✅ |
| `contentsOrgId` | 기관 코드 | `"A0013"` | ✅ |
| `contentsOrgName` | 기관명 | `"연합뉴스"` | ✅ |
| `categoryId` | 카테고리 코드 | `"B0001"` | ✅ |
| `categoryName` | 카테고리명 | `"뉴스"` | ✅ |
| `rawCollectSucYN` | 원문 수집 완료 여부 | `"Y"` | ✅ |
| `metaSucYN` | Ollama 분석 완료 여부 | `"N"` | ✅ |
| `pubDt` | 발행일시 | `"2025-10-21T08:37:00Z"` | ⭕ |

## 🚀 사용 방법

### 기본 사용 (이미 저장된 기사)

```bash
# 특정 URL 분석
docker exec python_new python3 /app/run_single_url_ollama.py \
  "https://www.yna.co.kr/view/AKR20251021023400003"

# 기본 URL 사용 (스크립트에 하드코딩된 URL)
docker exec python_new python3 /app/run_single_url_ollama.py
```

### 새로운 기사 추가 후 분석

```bash
# 1. JSON 파일 생성 (템플릿)
cat > /tmp/my_article.json << 'EOF'
{
  "title": "여기에 기사 제목",
  "url": "https://example.com/article/123",
  "contentsOrgId": "A0013",
  "contentsOrgName": "연합뉴스",
  "categoryId": "B0001",
  "categoryName": "뉴스",
  "rawCollectSucYN": "Y",
  "contentsRaw": {
    "title": "여기에 기사 제목",
    "contents": "여기에 기사 본문 전체 텍스트...",
    "image": "",
    "errorInfo": null
  },
  "metaSucYN": "N",
  "lookCount": 0,
  "likeCount": 0,
  "disLikeCount": 0,
  "lookIds": [],
  "likeIds": [],
  "disLikeIds": []
}
EOF

# 2. MongoDB에 삽입
docker exec -i ksubscribe_mongodb mongo mycontents --eval \
  "db.contents.insertOne($(cat /tmp/my_article.json))"

# 3. Ollama 분석 실행
docker exec python_new timeout 300 python3 /app/run_single_url_ollama.py \
  "https://example.com/article/123"
```

## 📊 출력 예시

```
================================================================================
🔍 단일 URL Ollama 분석
URL: https://www.yna.co.kr/view/AKR20251021023400003
================================================================================

✅ 문서 발견!
   제목: 한전 송전망 건설사업 절반이 '지연'…"전력공급 차질 우려"
   rawCollectSucYN: Y
   metaSucYN: N

📝 Ollama 5가지 분석 시작...

📋 키워드 리스트 로딩 중...
   - 키워드 148개 로드됨
   - 기관명 477개 로드됨
⏳ Ollama 분석 중... (최대 60초 소요)

✅ Ollama 분석 성공!

💾 MongoDB 업데이트 중...
✅ 저장 완료! (매칭: 1, 수정: 1)

🎉 Ollama 5가지 분석이 성공적으로 완료되었습니다!
   - 검증 완료
   - 요약 완료 (keywords: 3개)
   - 감성분석 완료 (sentiments: 1개)
   - MongoDB contents 컬렉션 업데이트 완료
```

## 🔍 분석 결과 확인

```bash
# MongoDB에서 결과 조회
docker exec -i ksubscribe_mongodb mongo mycontents --eval '
  db.contents.findOne(
    {"url": "https://www.yna.co.kr/view/AKR20251021023400003"},
    {"contentsMeta": 1, "metaSucYN": 1}
  )
' | tail -20
```

## ⚙️ Ollama 5가지 분석 항목

1. **검증 (question_verify)**: 문서가 DB 키워드와 관련 있는지 확인
2. **요약 (question_summary)**: 
   - `shortSummary`: 1줄 요약
   - `longSummary`: 5줄 이상 상세 요약
   - `keywords`: 핵심 키워드 추출
3. **감성 비율 (question_sentiment_ratio)**: 긍정/부정/중립 비율
4. **감성 이유 (sentiment_reason)**: 비율 판단 근거
5. **감성 키워드 (sentiment_keywords)**: 긍정/부정 키워드 추출

## ⏱️ 소요 시간
- 검증: 약 15-20초
- 요약: 약 25-30초
- 감성분석: 약 15-25초
- **총 약 60-80초**

## ⚠️ 주의사항

### 1. MongoDB에 문서가 있어야 함
스크립트는 MongoDB에서 URL로 문서를 찾습니다. 없으면:
```
❌ URL에 해당하는 문서를 찾을 수 없습니다
```

### 2. 원문이 있어야 함
`contentsRaw.contents`가 비어있으면 분석 불가

### 3. 중복 분석 방지
`metaSucYN="Y"`인 문서는 이미 분석 완료됨. 재분석하려면:
```bash
# metaSucYN을 N으로 변경
docker exec -i ksubscribe_mongodb mongo mycontents --eval '
  db.contents.updateOne(
    {"url": "YOUR_URL"},
    {$set: {"metaSucYN": "N"}}
  )
'
```

### 4. Timeout
- 기본 120초로 설정됨
- 매우 긴 문서는 timeout 발생 가능

## 🛠️ 문제 해결

### "timed out" 오류
```bash
# timeout 증가 (analysis_ollama_generate.py 수정)
# 66번째 줄: self.chat_ollama.client_kwargs["timeout"] = 180
```

### MariaDB 연결 오류 (무시 가능)
```
Failed to insert ArticleKeywords to MariaDB: Can't connect to local server
```
→ MongoDB 저장은 정상 작동하므로 무시해도 됩니다.

## 📚 더 자세한 정보
`/home/mycontents/KDN_MyContents/OLLAMA_분석_사용법.md` 참조
