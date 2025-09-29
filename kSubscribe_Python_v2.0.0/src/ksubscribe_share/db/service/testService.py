 
from bson import ObjectId
import datetime
from typing import List

import datetime

from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel 
from ksubscribe_share.db.dbmodelV2.predefineKeywordVO import PredefineKeywordVO
from ksubscribe_share.db.mongoManager import MongoManager

from pymongo import MongoClient

# MongoDB 서버 연결 설정
source_client = MongoClient("mongodb://192.168.1.200:27017/?directConnection=true")
target_client = MongoClient("mongodb://192.168.1.41:27017/")

# 소스 및 타겟 데이터베이스 및 컬렉션
source_db = source_client["mycontents"]
source_collection = source_db["contents_org"]

target_db = target_client["mycontents"]
target_collection = target_db["contents_org"]

# 소스에서 데이터를 읽어와 타겟에 업데이트
def sync_subscriber_ids():
    try:
        # 200번 서버에서 데이터 읽기
        cursor = source_collection.find({}, {"orgId": 1, "subscriberIds": 1})
        
        for doc in cursor:
            # 읽어온 데이터
            orgId = doc["orgId"]
            subscriber_ids = doc.get("subscriberIds", [])
            
            # 중복 제거
            unique_subscriber_ids = list(set(subscriber_ids))
            
            # 41번 서버에 업데이트
            result = target_collection.update_one(
                {"orgId": orgId},
                {"$set": {"subscriberIds": unique_subscriber_ids}},
                upsert=True  # 문서가 없으면 새로 생성
            )
            
            # 결과 로그
            if result.matched_count > 0:
                print(f"Updated subscriberIds for orgId: {orgId}")
            elif result.upserted_id:
                print(f"Inserted new document with orgId: {orgId}")
            else:
                print(f"No changes for orgId: {orgId}")

    except Exception as e:
        print(f"An error occurred: {e}")

# 동기화 실행
#sync_subscriber_ids()
