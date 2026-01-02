# Ollama 분석 실행 가이드

## 📌 개요
이 가이드는 새로운 기사를 MongoDB에 추가하고 Ollama로 분석하는 전체 프로세스를 설명합니다.

---

## 🎯 방법 1: 이미 MongoDB에 저장된 기사 분석하기

### 필요한 정보
- **URL만 있으면 됩니다!**

### 실행 방법

```bash
# 컨테이너 내부에서 실행
docker exec python_new python3 /app/run_single_url_ollama.py "https://example.com/article"

# 또는 기본 URL 사용 (스크립트에 하드코딩된 URL)
docker exec python_new python3 /app/run_single_url_ollama.py
```

### 전제 조건
MongoDB의 `contents` 컬렉션에 다음 조건을 만족하는 문서가 있어야 합니다:
- ✅ `url` 필드에 해당 URL이 저장되어 있음
- ✅ `rawCollectSucYN: "Y"` (원문 수집 완료)
- ✅ `contentsRaw.contents`에 원문 텍스트가 있음
- ✅ `metaSucYN: "N"` (아직 Ollama 분석 안됨)

---

## 🎯 방법 2: 새로운 기사를 처음부터 추가하고 분석하기

### 1단계: 기사 정보 수집

다음 정보가 필요합니다:

#### 필수 정보
1. **URL**: 기사 웹페이지 주소
2. **원문 (contents)**: 기사 본문 텍스트
3. **제목 (title)**: 기사 제목
4. **기관 정보**:
   - `contentsOrgId`: 기관 코드 (예: "A0013" - 연합뉴스)
   - `contentsOrgName`: 기관명 (예: "연합뉴스")
5. **카테고리 정보**:
   - `categoryId`: 카테고리 코드 (예: "B0001" - 뉴스)
   - `categoryName`: 카테고리명 (예: "뉴스")

#### 선택 정보
- `pubDt`: 발행일시 (ISO 8601 형식)
- `originallink`: 원본 링크

### 2단계: MongoDB에 문서 추가

#### 방법 A: JSON 파일로 추가

```bash
# 1. JSON 파일 생성
cat > /tmp/new_article.json << 'EOF'
{
  "title": "기사 제목",
  "url": "https://example.com/article/123",
  "contentsOrgId": "A0013",
  "contentsOrgName": "연합뉴스",
  "categoryId": "B0001",
  "categoryName": "뉴스",
  "originallink": "https://example.com/article/123",
  "link": "https://example.com/article/123",
  "pubDt": "2025-11-13T10:00:00Z",
  "collectDt": null,
  "lookCount": 0,
  "likeCount": 0,
  "disLikeCount": 0,
  "lookIds": [],
  "likeIds": [],
  "disLikeIds": [],
  "rawCollectSucYN": "Y",
  "contentsRaw": {
    "title": "기사 제목",
    "contents": "여기에 기사 본문 전체 텍스트를 넣으세요...",
    "image": "",
    "errorInfo": null
  },
  "rawCollectDt": null,
  "metaSucYN": "N",
  "contentsMeta": null,
  "metaAnalyzeDt": null,
  "imageId": null,
  "v1ContentsIdx": null
}
EOF

# 2. MongoDB에 삽입
docker exec -i ksubscribe_mongodb mongo --quiet mycontents --eval \
  "db.contents.insertOne($(cat /tmp/new_article.json))"
```

#### 방법 B: Python 스크립트로 추가

```python
from pymongo import MongoClient
from datetime import datetime

client = MongoClient('mongodb://ksubscribe_mongodb:27017/')
db = client['mycontents']
collection = db['contents']

doc = {
    "title": "기사 제목",
    "url": "https://example.com/article/123",
    "contentsOrgId": "A0013",
    "contentsOrgName": "연합뉴스",
    "categoryId": "B0001",
    "categoryName": "뉴스",
    "rawCollectSucYN": "Y",
    "contentsRaw": {
        "title": "기사 제목",
        "contents": "기사 본문 전체...",
        "image": "",
        "errorInfo": None
    },
    "metaSucYN": "N",
    "lookCount": 0,
    "likeCount": 0,
    "disLikeCount": 0,
    "lookIds": [],
    "likeIds": [],
    "disLikeIds": []
}

result = collection.insert_one(doc)
print(f"문서 ID: {result.inserted_id}")
```

### 3단계: Ollama 분석 실행

```bash
docker exec python_new python3 /app/run_single_url_ollama.py "https://example.com/article/123"
```

---

## 📊 분석 결과 확인

### MongoDB에서 확인

```bash
docker exec -i ksubscribe_mongodb mongo --quiet mycontents --eval \
  'db.contents.findOne({"url": "YOUR_URL"}, {"metaSucYN": 1, "contentsMeta": 1})'
```

### 결과 예시

```json
{
  "metaSucYN": "Y",
  "contentsMeta": {
    "keywords": ["송전망", "재생에너지", "전력 수급"],
    "shortSummary": "한국전력의 송·변전설비 건설사업이 절반 이상 지연...",
    "longSummary": "박정 의원은 한전으로부터...",
    "predKeywords": {
      "에너지": 0.26,
      "전력": 0.17
    },
    "sentiments": [{
      "orgId": "A0013",
      "orgName": "한국남부발전(주)",
      "positiveRatio": 0.0,
      "negativeRatio": 90.0,
      "neutralRatio": 10.0,
      "reason": "기사 내용이 전반적으로 부정적...",
      "positiveKeywords": ["안정성"],
      "negativeKeywords": ["지연", "공사 지연"]
    }]
  }
}
```

---

## 🔧 자주 사용하는 기관/카테고리 코드

### 기관 코드 (contentsOrgId)
- `A0001`: 산업통상자원부
- `A0013`: 연합뉴스
- (더 많은 코드는 MongoDB의 `contents_org` 컬렉션 참조)

### 카테고리 코드 (categoryId)
- `B0001`: 뉴스
- `B0012`: 공고
- (더 많은 코드는 MongoDB의 `contents_org_category` 컬렉션 참조)

---

## ⚠️ 주의사항

1. **원문이 반드시 있어야 합니다**
   - `contentsRaw.contents`가 비어있으면 분석 불가

2. **timeout 설정**
   - 긴 문서는 120초까지 소요될 수 있습니다
   - `analysis_ollama_generate.py`의 timeout이 120초로 설정되어 있습니다

3. **MariaDB 연결 오류는 무시됩니다**
   - MongoDB 저장은 정상 작동합니다

4. **중복 실행 방지**
   - `metaSucYN="Y"`인 문서는 이미 분석 완료된 것입니다
   - 재분석하려면 `metaSucYN="N"`으로 변경 후 실행

---

## 🚀 빠른 시작 예제

```bash
# 1. 웹페이지에서 기사 내용 복사

# 2. JSON 파일 생성
cat > /tmp/article.json << 'EOF'
{
  "title": "기사 제목을 여기에",
  "url": "https://www.example.com/news/123",
  "contentsOrgId": "A0013",
  "contentsOrgName": "연합뉴스",
  "categoryId": "B0001",
  "categoryName": "뉴스",
  "rawCollectSucYN": "Y",
  "contentsRaw": {
    "contents": "기사 본문 전체를 여기에 복사..."
  },
  "metaSucYN": "N",
  "lookCount": 0,
  "likeIds": [],
  "disLikeIds": []
}
EOF

# 3. MongoDB 삽입
docker exec -i ksubscribe_mongodb mongo mycontents --eval \
  "db.contents.insertOne($(cat /tmp/article.json))"

# 4. Ollama 분석 실행
docker exec python_new timeout 300 python3 /app/run_single_url_ollama.py \
  "https://www.example.com/news/123"

# 5. 결과 확인
docker exec -i ksubscribe_mongodb mongo mycontents --eval \
  'db.contents.findOne({"url": "https://www.example.com/news/123"}).contentsMeta.shortSummary' | tail -1
```

---

## 📞 문제 해결

### "문서를 찾을 수 없습니다"
- MongoDB에서 URL 확인: `db.contents.findOne({"url": "YOUR_URL"})`
- URL이 정확한지 확인 (http/https, 끝 슬래시 등)

### "timeout 발생"
- Ollama 서버 상태 확인: `docker exec ksubscribe_ollama ollama list`
- timeout 값 증가: `analysis_ollama_generate.py`의 66번째 줄

### "원문이 없습니다"
- `contentsRaw.contents` 필드 확인
- 빈 문자열이나 null이 아닌지 확인
