# MongoDB 쿼리: 중복 제거 (metaAnalyzeDt 최신 기준)

> 작성일: 2025-01-XX  
> 목적: pubDt가 2025-11-22 ~ 2025-11-26인 문서 중, 중복 제거 (metaAnalyzeDt 최신 기준)

---

## 📋 요구사항

- `pubDt`: 2025년 11월 22일 ~ 2025년 11월 26일
- 중복 제거: `url` 기준으로 중복 제거
- 선택 기준: `metaAnalyzeDt`가 최신인 것만 선택

---

## 1. MongoDB Aggregation Pipeline (권장)

### 방법 1: Aggregation Pipeline 사용

```javascript
db.contents.aggregate([
  // 1단계: 날짜 범위 필터링
  {
    $match: {
      pubDt: {
        $gte: ISODate("2025-11-22T00:00:00.000Z"),
        $lte: ISODate("2025-11-26T23:59:59.999Z")
      }
    }
  },
  // 2단계: metaAnalyzeDt 내림차순 정렬 (최신이 먼저)
  {
    $sort: {
      metaAnalyzeDt: -1  // -1: 내림차순 (최신이 먼저)
    }
  },
  // 3단계: url 기준으로 그룹화하고 첫 번째 문서만 선택
  {
    $group: {
      _id: "$url",  // url을 기준으로 그룹화
      doc: { $first: "$$ROOT" }  // 첫 번째 문서 (가장 최신 metaAnalyzeDt)
    }
  },
  // 4단계: doc 필드를 루트로 복원
  {
    $replaceRoot: {
      newRoot: "$doc"
    }
  },
  // 5단계: 최종 정렬 (선택사항)
  {
    $sort: {
      pubDt: 1,
      metaAnalyzeDt: -1
    }
  }
])
```

### 방법 2: metaAnalyzeDt가 null인 경우 처리

`metaAnalyzeDt`가 null인 경우를 고려한 버전:

```javascript
db.contents.aggregate([
  // 1단계: 날짜 범위 필터링
  {
    $match: {
      pubDt: {
        $gte: ISODate("2025-11-22T00:00:00.000Z"),
        $lte: ISODate("2025-11-26T23:59:59.999Z")
      }
    }
  },
  // 2단계: metaAnalyzeDt가 null인 경우를 처리하기 위해 임시 필드 추가
  {
    $addFields: {
      sortDate: {
        $ifNull: ["$metaAnalyzeDt", ISODate("1970-01-01T00:00:00.000Z")]
      }
    }
  },
  // 3단계: sortDate 내림차순 정렬
  {
    $sort: {
      sortDate: -1
    }
  },
  // 4단계: url 기준으로 그룹화
  {
    $group: {
      _id: "$url",
      doc: { $first: "$$ROOT" }
    }
  },
  // 5단계: doc 필드를 루트로 복원
  {
    $replaceRoot: {
      newRoot: "$doc"
    }
  },
  // 6단계: 임시 필드 제거
  {
    $unset: "sortDate"
  },
  // 7단계: 최종 정렬
  {
    $sort: {
      pubDt: 1,
      metaAnalyzeDt: -1
    }
  }
])
```

---

## 2. Python 코드 (MongoDB Driver 사용)

### 방법 1: Aggregation Pipeline 사용

```python
from datetime import datetime
import pytz
from pymongo import MongoClient

# MongoDB 연결
client = MongoClient('mongodb://localhost:27017/')
db = client['mycontents']
collection = db['contents']

# 날짜 범위 설정
start_date = datetime(2025, 11, 22, 0, 0, 0, tzinfo=pytz.UTC)
end_date = datetime(2025, 11, 26, 23, 59, 59, 999999, tzinfo=pytz.UTC)

# Aggregation Pipeline
pipeline = [
    # 1단계: 날짜 범위 필터링
    {
        "$match": {
            "pubDt": {
                "$gte": start_date,
                "$lte": end_date
            }
        }
    },
    # 2단계: metaAnalyzeDt 내림차순 정렬
    {
        "$sort": {
            "metaAnalyzeDt": -1  # -1: 내림차순 (최신이 먼저)
        }
    },
    # 3단계: url 기준으로 그룹화
    {
        "$group": {
            "_id": "$url",
            "doc": {"$first": "$$ROOT"}  # 첫 번째 문서만 선택
        }
    },
    # 4단계: doc 필드를 루트로 복원
    {
        "$replaceRoot": {
            "newRoot": "$doc"
        }
    },
    # 5단계: 최종 정렬
    {
        "$sort": {
            "pubDt": 1,
            "metaAnalyzeDt": -1
        }
    }
]

# 쿼리 실행
results = list(collection.aggregate(pipeline))

print(f"총 {len(results)}개 문서 (중복 제거 후)")
for doc in results:
    print(f"URL: {doc.get('url')}, metaAnalyzeDt: {doc.get('metaAnalyzeDt')}")
```

### 방법 2: Python에서 직접 처리

```python
from datetime import datetime
import pytz
from pymongo import MongoClient
from collections import defaultdict

# MongoDB 연결
client = MongoClient('mongodb://localhost:27017/')
db = client['mycontents']
collection = db['contents']

# 날짜 범위 설정
start_date = datetime(2025, 11, 22, 0, 0, 0, tzinfo=pytz.UTC)
end_date = datetime(2025, 11, 26, 23, 59, 59, 999999, tzinfo=pytz.UTC)

# 쿼리 실행
query = {
    "pubDt": {
        "$gte": start_date,
        "$lte": end_date
    }
}

# metaAnalyzeDt 내림차순으로 정렬하여 조회
cursor = collection.find(query).sort("metaAnalyzeDt", -1)

# url을 키로 하여 최신 문서만 저장
url_to_doc = {}
for doc in cursor:
    url = doc.get('url')
    if url and url not in url_to_doc:
        url_to_doc[url] = doc

# 결과 리스트로 변환
results = list(url_to_doc.values())

# pubDt로 정렬
results.sort(key=lambda x: x.get('pubDt', datetime.min))

print(f"총 {len(results)}개 문서 (중복 제거 후)")
for doc in results:
    print(f"URL: {doc.get('url')}, metaAnalyzeDt: {doc.get('metaAnalyzeDt')}")
```

---

## 3. MongoDB Shell에서 직접 실행

### 간단한 버전

```javascript
// MongoDB shell에서 실행
use mycontents

db.contents.aggregate([
  {
    $match: {
      pubDt: {
        $gte: ISODate("2025-11-22T00:00:00.000Z"),
        $lte: ISODate("2025-11-26T23:59:59.999Z")
      }
    }
  },
  {
    $sort: { metaAnalyzeDt: -1 }
  },
  {
    $group: {
      _id: "$url",
      doc: { $first: "$$ROOT" }
    }
  },
  {
    $replaceRoot: { newRoot: "$doc" }
  },
  {
    $sort: { pubDt: 1, metaAnalyzeDt: -1 }
  }
])
```

### 결과 개수 확인

```javascript
db.contents.aggregate([
  {
    $match: {
      pubDt: {
        $gte: ISODate("2025-11-22T00:00:00.000Z"),
        $lte: ISODate("2025-11-26T23:59:59.999Z")
      }
    }
  },
  {
    $sort: { metaAnalyzeDt: -1 }
  },
  {
    $group: {
      _id: "$url",
      doc: { $first: "$$ROOT" }
    }
  },
  {
    $count: "total"
  }
])
```

---

## 4. Docker 컨테이너에서 실행

```bash
# MongoDB 컨테이너에 접속
docker exec -it ksubscribe_mongodb mongo mycontents

# 쿼리 실행
db.contents.aggregate([
  {
    $match: {
      pubDt: {
        $gte: ISODate("2025-11-22T00:00:00.000Z"),
        $lte: ISODate("2025-11-26T23:59:59.999Z")
      }
    }
  },
  {
    $sort: { metaAnalyzeDt: -1 }
  },
  {
    $group: {
      _id: "$url",
      doc: { $first: "$$ROOT" }
    }
  },
  {
    $replaceRoot: { newRoot: "$doc" }
  },
  {
    $sort: { pubDt: 1, metaAnalyzeDt: -1 }
  }
])
```

---

## 5. 중복 기준 변경

만약 `url`이 아닌 다른 필드를 기준으로 중복을 판단하려면:

### title 기준

```javascript
{
  $group: {
    _id: "$title",  // title을 기준으로 변경
    doc: { $first: "$$ROOT" }
  }
}
```

### url + contentsOrgId 조합 기준

```javascript
{
  $group: {
    _id: {
      url: "$url",
      orgId: "$contentsOrgId"
    },
    doc: { $first: "$$ROOT" }
  }
}
```

---

## 6. 성능 최적화

인덱스가 있다면 성능이 향상됩니다:

```javascript
// 인덱스 생성 (한 번만 실행)
db.contents.createIndex({ "pubDt": 1, "metaAnalyzeDt": -1 })
db.contents.createIndex({ "url": 1 })
```

---

## 7. 예상 결과

- **입력**: pubDt가 2025-11-22 ~ 2025-11-26인 모든 문서
- **출력**: url 기준으로 중복 제거된 문서 (metaAnalyzeDt가 최신인 것만)
- **정렬**: pubDt 오름차순, metaAnalyzeDt 내림차순

---

**문서 작성자**: AI Assistant  
**최종 수정일**: 2025-01-XX


