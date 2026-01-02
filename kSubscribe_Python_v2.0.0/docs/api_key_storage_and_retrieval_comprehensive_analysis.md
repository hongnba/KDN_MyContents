# APIKEY1, APIKEY2 저장 및 조회 종합 분석

> 작성일: 2025-12-23  
> 분석 목적: APIKEY1, APIKEY2의 저장 위치, 조회 방법, 설정 방법에 대한 완전한 이해

---

## 📋 목차

1. [핵심 답변](#1-핵심-답변)
2. [APIKEY1, APIKEY2 조회 방법](#2-apikey1-apikey2-조회-방법)
3. [APIKEY1, APIKEY2 저장 방법](#3-apikey1-apikey2-저장-방법)
4. [APIKEY1, APIKEY2 업데이트 방법](#4-apikey1-apikey2-업데이트-방법)
5. [전체 데이터 흐름](#5-전체-데이터-흐름)
6. [실제 코드 예시](#6-실제-코드-예시)
7. [결론 및 권장사항](#7-결론-및-권장사항)

---

## 1. 핵심 답변

### 1.1 사용자의 질문

**Q1**: APIKEY1과 APIKEY2 정보를 가져오는 방법은 오직 `contents_org` collection에서 조회하는 방법밖에 없는가?  
**A1**: ✅ **예, 맞습니다.** 오직 `contents_org` collection에서만 조회합니다.

**Q2**: `contents_org` collection에 문서를 만들 때 처음부터 APIKEY1과 APIKEY2 정보를 입력해야 하는가?  
**A2**: ✅ **예, 맞습니다.** 문서 생성 시점에 APIKEY1, APIKEY2를 포함해야 합니다.

### 1.2 핵심 요약

| 항목 | 답변 |
|------|------|
| **조회 방법** | ✅ 오직 `contents_org` collection에서만 조회 |
| **저장 위치** | ✅ MongoDB `contents_org` collection의 `categoryList[].APIKEY1`, `APIKEY2` |
| **설정 시점** | ✅ 문서 생성 시점에 반드시 포함해야 함 |
| **업데이트 방법** | ⚠️ **코드베이스에 업데이트 메서드 없음** (직접 MongoDB 쿼리 필요) |
| **다른 저장소** | ❌ `.env` 파일 없음, `config.py`에 하드코딩 없음 |

---

## 2. APIKEY1, APIKEY2 조회 방법

### 2.1 조회 경로 (단일 경로)

**오직 하나의 경로만 존재**: MongoDB `contents_org` collection에서 조회

```
MongoDB (contents_org)
    ↓
ContentsOrgService.find_all() / findOrgAndCategory() / findOrg()
    ↓
ContentsOrgVO.from_mongo()
    ↓
ContentsOrgCategory.from_mongo()
    ↓
BaseModel.from_mongo() → 동적 필드 할당
    ↓
category.APIKEY1, category.APIKEY2
```

### 2.2 조회 코드 위치

**파일**: `src/ksubscribe_share/db/service/contentsOrgService.py`

#### A. 전체 기관 조회

```python
# Line 71-94
def find_all(self):
    collection = self.mongoManager.getCollection(self.collectionName)  # "contents_org"
    cursor = collection.find({"IS_USE": True})
    result_list = [ContentsOrgVO.from_mongo(item) for item in cursor]
    return result_list
```

#### B. 특정 기관 조회

```python
# Line 185-202
def findOrg(self, orgId:str):
    collection = self.mongoManager.getCollection(self.collectionName)  # "contents_org"
    query = {"orgId": orgId}
    result = collection.find_one(query)
    contentsOrgVO = ContentsOrgVO.from_mongo(result)
    return contentsOrgVO
```

#### C. 기관 및 카테고리 조회

```python
# Line 145-167
def findOrgAndCategory(self, orgId:str, cateId:str):
    collection = self.mongoManager.getCollection(self.collectionName)  # "contents_org"
    query = {"orgId": orgId}
    result = collection.find_one(query)
    contentsOrgVO = ContentsOrgVO.from_mongo(result)
    
    for category in contentsOrgVO.categoryList:
        if category.cateId == cateId:
            return contentsOrgVO, category
    return contentsOrgVO, None
```

### 2.3 조회 결과 사용

**파일**: `src/docker_collect/openapi_collector.py`

```python
# 나라장터 API Key 사용 (Line 59)
service_key = category.APIKEY1

# 네이버 뉴스 API Key 사용 (Line 213-214)
request.add_header('X-Naver-Client-Id', category.APIKEY1)
request.add_header('X-Naver-Client-Secret', category.APIKEY2)
```

---

## 3. APIKEY1, APIKEY2 저장 방법

### 3.1 저장 위치

**MongoDB 컬렉션**: `contents_org`  
**필드 경로**: `categoryList[].APIKEY1`, `categoryList[].APIKEY2`

**데이터 구조**:
```json
{
  "_id": ObjectId("..."),
  "orgId": "A0004",
  "orgName": "나라장터",
  "categoryList": [
    {
      "cateId": "B0005",
      "cateName": "입찰공고",
      "APIKEY1": "efdW9bR%2FAKR6XOI%2F...",
      "APIKEY2": null,
      "COL_METHOD": "C0002",
      // ... 기타 필드들
    }
  ]
}
```

### 3.2 문서 생성 시 APIKEY1, APIKEY2 설정

**중요**: 문서 생성 시점에 반드시 APIKEY1, APIKEY2를 포함해야 합니다.

#### A. 데이터 마이그레이션 스크립트

**파일**: `src/ksubscribe_share/db/data_migration/data_csa_organization.py`

**Line 97-98**: MariaDB에서 APIKEY1, APIKEY2 읽기
```python
APIKEY1 = category_row[7]  # MariaDB csa_organization_detail 테이블의 7번째 컬럼
APIKEY2 = category_row[8]  # MariaDB csa_organization_detail 테이블의 8번째 컬럼
```

**Line 150-151**: ContentsOrgCategory 객체에 할당
```python
contentsOrgCategory.APIKEY1 = APIKEY1
contentsOrgCategory.APIKEY2 = APIKEY2
```

**Line 175**: MongoDB에 삽입
```python
result = BaseQueryService.insert_one(contentsOrgVO)
```

**전체 흐름**:
```python
# 1. MariaDB에서 데이터 읽기
category_cursor.execute(
    f"SELECT * FROM csa_organization_detail WHERE org_id = '{contentsOrgVO.orgId}'"
)
category_result = category_cursor.fetchall()

# 2. 각 카테고리 처리
for category_row in category_result:
    APIKEY1 = category_row[7]
    APIKEY2 = category_row[8]
    
    contentsOrgCategory = ContentsOrgCategory()
    contentsOrgCategory.APIKEY1 = APIKEY1  # ✅ 문서 생성 시 설정
    contentsOrgCategory.APIKEY2 = APIKEY2  # ✅ 문서 생성 시 설정
    # ... 기타 필드 설정
    
    contentsOrgVO.categoryList.append(contentsOrgCategory)

# 3. MongoDB에 삽입
BaseQueryService.insert_one(contentsOrgVO)  # APIKEY1, APIKEY2 포함하여 저장
```

#### B. 데이터 추가 스크립트

**파일**: `src/ksubscribe_share/db/data_setting/ContentsOrgVO_데이터추가.py`

**Line 49-50**: APIKEY1, APIKEY2 설정
```python
ContentsOrgCategory(
    # ... 기타 필드들
    APIKEY1=cate[7],  # ✅ 문서 생성 시 설정
    APIKEY2=cate[8],  # ✅ 문서 생성 시 설정
    # ... 기타 필드들
)
```

### 3.3 다른 저장소 확인 결과

#### ❌ .env 파일
- 프로젝트에 `.env` 파일 없음
- 환경 변수로 API Key 관리하지 않음

#### ❌ config.py
- `config.py` 및 관련 설정 파일에 API Key 하드코딩 없음
- `config.py`, `config_linux.py`, `config_window.py` 등 모두 확인 결과 APIKEY1, APIKEY2 정의 없음

#### ✅ MongoDB만 사용
- **오직 MongoDB `contents_org` collection에만 저장됨**

---

## 4. APIKEY1, APIKEY2 업데이트 방법

### 4.1 코드베이스 분석 결과

**⚠️ 중요 발견**: 코드베이스에 APIKEY1, APIKEY2를 업데이트하는 메서드가 **없습니다**.

#### A. ContentsOrgService의 update 메서드들

**파일**: `src/ksubscribe_share/db/service/contentsOrgService.py`

다음 update 메서드들이 존재하지만, **APIKEY1, APIKEY2 업데이트 메서드는 없음**:

1. `updateCategorySucYMD()` (Line 298-327)
   - `sucYN`, `lastSucYMD`만 업데이트
   - APIKEY1, APIKEY2 업데이트 없음

2. `updateSubscribers()` (Line 330-349)
   - `subscriberIds`만 업데이트
   - APIKEY1, APIKEY2 업데이트 없음

3. `updateCollectInfo()` (Line 353-379)
   - `collectMethod`, `tagElement`, `tagAttr`, `tagAttrValue`만 업데이트
   - APIKEY1, APIKEY2 업데이트 없음

4. `updateOrgNameSynonym()` (Line 381-403)
   - `orgNameSynonymList`만 업데이트
   - APIKEY1, APIKEY2 업데이트 없음

5. `updateImageInfo()` (Line 405-424)
   - `orgCIWidth`, `orgCIHeight`만 업데이트
   - APIKEY1, APIKEY2 업데이트 없음

#### B. 검색 결과

```bash
# APIKEY1, APIKEY2 업데이트 관련 코드 검색
grep -r "update.*APIKEY\|set.*APIKEY\|APIKEY.*=" src/
```

**결과**: APIKEY1, APIKEY2를 업데이트하는 코드 없음

### 4.2 업데이트 방법 (직접 MongoDB 쿼리)

**⚠️ 현재는 직접 MongoDB 쿼리를 사용해야 합니다.**

#### A. MongoDB 쿼리 예시

```javascript
// 특정 기관의 특정 카테고리 APIKEY1, APIKEY2 업데이트
db.contents_org.updateOne(
  {
    "orgId": "A0004",
    "categoryList.cateId": "B0005"
  },
  {
    "$set": {
      "categoryList.$.APIKEY1": "new_api_key_1",
      "categoryList.$.APIKEY2": "new_api_key_2"
    }
  }
)
```

#### B. Python 스크립트 예시

```python
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share import config as Conf

mongoManager = MongoManager()
collection = mongoManager.getCollection("contents_org")

# APIKEY1, APIKEY2 업데이트
result = collection.update_one(
    {
        "orgId": "A0004",
        "categoryList.cateId": "B0005"
    },
    {
        "$set": {
            "categoryList.$.APIKEY1": "new_api_key_1",
            "categoryList.$.APIKEY2": "new_api_key_2"
        }
    }
)

if result.modified_count > 0:
    print("API Key 업데이트 성공")
else:
    print("API Key 업데이트 실패 (매칭되는 문서 없음)")
```

### 4.3 권장사항: 업데이트 메서드 추가

**현재 문제점**: APIKEY1, APIKEY2를 업데이트하는 메서드가 없어서 직접 MongoDB 쿼리를 사용해야 함

**권장 해결책**: `ContentsOrgService`에 업데이트 메서드 추가

```python
# ContentsOrgService에 추가 권장
def updateApiKeys(self, org_id: str, category_id: str, api_key1: str = None, api_key2: str = None):
    """
    특정 기관의 특정 카테고리 APIKEY1, APIKEY2 업데이트
    
    Args:
        org_id: 기관 ID
        category_id: 카테고리 ID
        api_key1: APIKEY1 값 (None이면 업데이트 안 함)
        api_key2: APIKEY2 값 (None이면 업데이트 안 함)
    """
    try:
        collection = self.mongoManager.getCollection(self.collectionName)
        update_fields = {}
        
        if api_key1 is not None:
            update_fields["categoryList.$.APIKEY1"] = api_key1
        if api_key2 is not None:
            update_fields["categoryList.$.APIKEY2"] = api_key2
        
        if not update_fields:
            return False
        
        result = collection.update_one(
            {"orgId": org_id, "categoryList.cateId": category_id},
            {"$set": update_fields}
        )
        
        return result.modified_count > 0
    except Exception as e:
        print(f"An error occurred: {e}")
        return False
```

---

## 5. 전체 데이터 흐름

### 5.1 저장 흐름 (초기 설정)

```
MariaDB (csa_organization_detail)
    ↓
data_csa_organization.py
    ↓
APIKEY1 = category_row[7]
APIKEY2 = category_row[8]
    ↓
contentsOrgCategory.APIKEY1 = APIKEY1
contentsOrgCategory.APIKEY2 = APIKEY2
    ↓
contentsOrgVO.categoryList.append(contentsOrgCategory)
    ↓
BaseQueryService.insert_one(contentsOrgVO)
    ↓
MongoDB (contents_org) 저장 ✅
```

### 5.2 조회 흐름 (사용)

```
MongoDB (contents_org)
    ↓
ContentsOrgService.find_all() / findOrgAndCategory()
    ↓
collection.find() / collection.find_one()
    ↓
ContentsOrgVO.from_mongo(result)
    ↓
ContentsOrgCategory.from_mongo(category)
    ↓
BaseModel.from_mongo(category_doc)
    ↓
setattr(instance, "APIKEY1", value)
setattr(instance, "APIKEY2", value)
    ↓
category.APIKEY1, category.APIKEY2 접근 가능 ✅
    ↓
openapi_collector.py에서 사용
```

### 5.3 업데이트 흐름 (현재 없음)

```
⚠️ 코드베이스에 업데이트 메서드 없음
    ↓
직접 MongoDB 쿼리 필요
    ↓
db.contents_org.updateOne(...)
    또는
collection.update_one(...)
```

---

## 6. 실제 코드 예시

### 6.1 문서 생성 시 APIKEY1, APIKEY2 설정

**파일**: `src/ksubscribe_share/db/data_migration/data_csa_organization.py`

```python
# MariaDB에서 데이터 읽기
category_cursor.execute(
    f"SELECT * FROM csa_organization_detail WHERE org_id = '{contentsOrgVO.orgId}'"
)
category_result = category_cursor.fetchall()

# 각 카테고리 처리
for category_row in category_result:
    # APIKEY1, APIKEY2 추출
    APIKEY1 = category_row[7]
    APIKEY2 = category_row[8]
    
    # ContentsOrgCategory 객체 생성
    contentsOrgCategory = ContentsOrgCategory()
    contentsOrgCategory.orgId = ORG_ID
    contentsOrgCategory.cateId = CATE_ID
    # ... 기타 필드 설정
    
    # ✅ APIKEY1, APIKEY2 설정 (문서 생성 시 필수)
    contentsOrgCategory.APIKEY1 = APIKEY1
    contentsOrgCategory.APIKEY2 = APIKEY2
    
    # categoryList에 추가
    contentsOrgVO.categoryList.append(contentsOrgCategory)

# MongoDB에 삽입
BaseQueryService.insert_one(contentsOrgVO)  # APIKEY1, APIKEY2 포함하여 저장
```

### 6.2 조회 및 사용

**파일**: `src/docker_collect/openapi_collector.py`

```python
# ContentsOrgService에서 조회
contentsOrgList = ContentsOrgService().find_all()

for contentsOrg in contentsOrgList:
    for category in contentsOrg.categoryList:
        # ✅ APIKEY1, APIKEY2 접근
        if category.cateId == "B0005":  # 나라장터
            service_key = category.APIKEY1
            # API 호출에 사용
        
        if category.cateId == "B0010":  # 네이버 뉴스
            client_id = category.APIKEY1
            client_secret = category.APIKEY2
            # API 호출에 사용
```

### 6.3 업데이트 (직접 MongoDB 쿼리)

```python
from ksubscribe_share.db.mongoManager import MongoManager

mongoManager = MongoManager()
collection = mongoManager.getCollection("contents_org")

# APIKEY1, APIKEY2 업데이트
result = collection.update_one(
    {
        "orgId": "A0004",
        "categoryList.cateId": "B0005"
    },
    {
        "$set": {
            "categoryList.$.APIKEY1": "new_api_key_1",
            "categoryList.$.APIKEY2": "new_api_key_2"
        }
    }
)

if result.modified_count > 0:
    print("✅ API Key 업데이트 성공")
else:
    print("❌ API Key 업데이트 실패")
```

---

## 7. 결론 및 권장사항

### 7.1 핵심 답변 요약

| 질문 | 답변 |
|------|------|
| **APIKEY1, APIKEY2를 가져오는 방법은 오직 `contents_org` collection에서 조회하는 방법뿐인가?** | ✅ **예, 맞습니다.** |
| **`contents_org` collection에 문서를 만들 때 처음부터 APIKEY1, APIKEY2를 입력해야 하는가?** | ✅ **예, 맞습니다.** |

### 7.2 확인된 사실

1. **저장 위치**: 오직 MongoDB `contents_org` collection에만 저장됨
2. **조회 방법**: 오직 `ContentsOrgService`를 통한 MongoDB 조회만 가능
3. **설정 시점**: 문서 생성 시점에 반드시 포함해야 함
4. **업데이트 방법**: 코드베이스에 업데이트 메서드 없음 (직접 MongoDB 쿼리 필요)

### 7.3 권장사항

#### A. 즉시 적용 가능

1. **문서 생성 시 APIKEY1, APIKEY2 포함**
   - `data_csa_organization.py`에서 이미 구현되어 있음
   - 새로운 문서 생성 시 반드시 포함해야 함

2. **업데이트 시 직접 MongoDB 쿼리 사용**
   - 현재는 직접 MongoDB 쿼리를 사용해야 함
   - Python 스크립트 또는 MongoDB 쿼리 도구 사용

#### B. 개선 권장사항

1. **업데이트 메서드 추가**
   - `ContentsOrgService`에 `updateApiKeys()` 메서드 추가
   - 코드 일관성 및 유지보수성 향상

2. **API Key 관리 UI 추가**
   - 웹 인터페이스에서 API Key 관리 기능 추가
   - 보안을 고려한 암호화 저장 고려

3. **환경 변수 지원 검토**
   - 민감한 정보이므로 환경 변수로 관리하는 방법 검토
   - 현재는 MongoDB에 평문 저장 (보안 강화 필요)

---

## 8. 참고 파일 위치

### 8.1 조회 관련

- **서비스**: `src/ksubscribe_share/db/service/contentsOrgService.py`
- **모델**: `src/ksubscribe_share/db/dbmodelV2/contentsOrgVO.py`
- **베이스**: `src/ksubscribe_share/db/dbmodelV2/baseDocument.py`
- **사용**: `src/docker_collect/openapi_collector.py`

### 8.2 저장 관련

- **마이그레이션**: `src/ksubscribe_share/db/data_migration/data_csa_organization.py`
- **데이터 추가**: `src/ksubscribe_share/db/data_setting/ContentsOrgVO_데이터추가.py`

### 8.3 업데이트 관련

- **현재**: 업데이트 메서드 없음
- **권장**: `ContentsOrgService`에 `updateApiKeys()` 메서드 추가

---

## 9. 최종 확인 사항

### ✅ 확인 완료

1. ✅ APIKEY1, APIKEY2는 오직 `contents_org` collection에서만 조회됨
2. ✅ 문서 생성 시점에 APIKEY1, APIKEY2를 포함해야 함
3. ✅ 코드베이스에 업데이트 메서드 없음
4. ✅ `.env` 파일, `config.py`에 API Key 정의 없음

### ⚠️ 주의사항

1. ⚠️ APIKEY1, APIKEY2 업데이트 시 직접 MongoDB 쿼리 필요
2. ⚠️ 보안: 현재 MongoDB에 평문 저장 (암호화 고려 필요)
3. ⚠️ 유지보수: 업데이트 메서드 추가 권장

---

**작성 완료일**: 2025-12-23  
**분석 범위**: 전체 코드베이스  
**확인 방법**: grep, codebase_search, 파일 읽기



