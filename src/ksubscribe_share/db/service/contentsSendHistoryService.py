
from bson import ObjectId
from datetime import datetime, timezone, timedelta
from typing import List
import logging

from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO, ContentsOrgCategory
from ksubscribe_share.db.dbmodelV2.contentsCollectHistoryVO import ContentsCollectDetail, ContentsCollect, ContentsCollectHistoryVO
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService
from ksubscribe_share.db.dbmodelV2.contentsSendHistoryVO import ContentsSendHistoryVO


#컨텐츠 수집 이력 
class ContentsSendHistoryService():
    
    mongoManager = MongoManager()  # MongoManager 싱글톤 인스턴스를 사용
    collectionName = "contents_send_history" 
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ContentsSendHistoryService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        pass

    def upsert_contents_send_history(self, history: ContentsSendHistoryVO):
        collection = self.mongoManager.getCollection(self.collectionName)
        
        # 현재 시간 (KST 기준)
        now_kst = datetime.now(timezone(timedelta(hours=9)))

        # 당일 00:00 ~ 23:59 KST 시간 범위를 UTC로 변환
        start_of_day_kst = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day_kst = start_of_day_kst + timedelta(days=1)

        start_of_day_utc = start_of_day_kst.astimezone(timezone.utc)
        end_of_day_utc = end_of_day_kst.astimezone(timezone.utc)

        # 필터 조건 (KST 기준 당일 범위와 userName)
        filter_query = {
            "date": {"$gte": start_of_day_utc, "$lt": end_of_day_utc},
            "mberId": history.mberId
        }

        # Upsert 실행
        result = collection.update_one(filter_query, history.to_update_query(), upsert=True)
        
    def find_send_history_by_user_and_date(self, user_id: str, send_dt: datetime):
        # MongoDB 쿼리 (yyyy-MM-dd 동일한 문서 찾기)
        query = {
            "sendDt": {
                "$gte": datetime(send_dt.year, send_dt.month, send_dt.day),
                "$lt": datetime(send_dt.year, send_dt.month, send_dt.day) + timedelta(days=1)
            },
            "mberId": user_id,
        }
        
        collection = self.mongoManager.getCollection(self.collectionName)
        document = collection.find_one(query)
        result = ContentsSendHistoryVO.from_mongo(document)
        
        return result
        
