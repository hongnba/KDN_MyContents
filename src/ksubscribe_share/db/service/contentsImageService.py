
from bson import ObjectId
import datetime
from typing import List
import datetime

from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.contentsImageVO import ContentsImageVO
from ksubscribe_share.db.dbmodelV2.contentsCollectHistoryVO import ContentsCollectDetail, ContentsCollect, ContentsCollectHistoryVO
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
from ksubscribe_share.db.mongoManager import MongoManager


#컨텐츠 수집 이력 
class ContentsImageService():

    mongoManager = MongoManager()  # MongoManager 싱글톤 인스턴스를 사용
    collectionName = "contents_image"
        
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ContentsImageService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        pass
    
    
    def recommendKeywordImage(self, predefineKeyword): 

        try: 
            collection = self.mongoManager.getCollection(ContentsImageVO.collectionName) 
            # MongoDB Aggregation 파이프라인
            pipeline = [
                {"$match": {"keyword": predefineKeyword}},  # keyword가 일치하는 문서 필터링
                {"$sample": {"size": 1}},  # 랜덤하게 하나의 문서를 샘플링
                {"$project": {"_id": 1}}  # _id 필드만 반환
            ]

            # Aggregation 실행
            result = list(collection.aggregate(pipeline))
            return str(result[0]["_id"]) if result else None
        
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
                 
    def recommendImage(self): 

        try: 
            collection = self.mongoManager.getCollection(ContentsImageVO.collectionName) 
            # MongoDB Aggregation 파이프라인
            pipeline = [
                {"$sample": {"size": 1}},  # 랜덤하게 하나의 문서를 샘플링
                {"$project": {"_id": 1}}  # _id 필드만 반환
            ]
            # Aggregation 실행
            result = list(collection.aggregate(pipeline))
            return str(result[0]["_id"]) if result else None
        
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
                 
    def get_contentsImage_by_id(self, imageId:str): 
        try:
            collection = self.mongoManager.getCollection(self.collectionName)

            filter_query = {
                "_id": ObjectId(imageId),
            }

            # 조건을 만족하는 첫 번째 문서 반환
            result = collection.find_one(filter_query)
            return ContentsImageVO.from_mongo(result)
        
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
    
    