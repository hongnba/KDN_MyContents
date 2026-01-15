
from bson import ObjectId
import datetime
from typing import List
import datetime

from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO, ContentsOrgCategory
from ksubscribe_share.db.dbmodelV2.contentsCollectHistoryVO import ContentsCollectDetail, ContentsCollect, ContentsCollectHistoryVO
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
from ksubscribe_share.db.mongoManager import MongoManager


#컨텐츠 수집 이력 
class ContentsQueueService():

    mongoManager = MongoManager()  # MongoManager 싱글톤 인스턴스를 사용
    collectionName = "contents_queue"
    
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ContentsQueueService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        pass

    def removeDuplicateUrl(self):
        collection = self.mongoManager.getCollection(ContentsQueueVO.collectionName)
        pipeline = [
                {
                    "$group": {
                        "_id": "$url",  # 중복 확인할 필드
                        "count": {"$sum": 1},
                        "docs": {"$push": "$_id"}  # 중복된 문서들의 _id 목록
                    }
                },
                {
                    "$match": {
                        "count": {"$gt": 1}  # 중복된 항목만 필터링
                    }
                }
            ]
 
        duplicates = list(collection.aggregate(pipeline))
        for entry in duplicates:
            ids_to_delete = entry["docs"][:-1]  # 첫 번째 문서를 제외하고 삭제
            collection.delete_many({"_id": {"$in": ids_to_delete}})


    def isExistQueue(self, url):
        # contents 에서 
        result = self.findByURL(url)
        if result:
            return True
        return False

    def findByURL(self,url):
        collection = self.mongoManager.getCollection(ContentsQueueVO.collectionName)
        filter = {"url": url}
        return  collection.find_one(filter)
        
    def deleteQueue(self, _id:ObjectId):
        collection = self.mongoManager.getCollection(ContentsQueueVO.collectionName)
        result = collection.delete_one({"_id": _id})
        
    #contentsOrg.orgId, category.cateId, collectDetail, collectYMD, session=session
    def insertQueue(self, orgId:str, cateId:str, collectionDetail:ContentsCollectDetail, collectYMD, keyword:str = None,session = None):
        queueVO = ContentsQueueVO.from_collect_detail(orgId, cateId, collectionDetail, collectYMD,collectKeyword=keyword)
        # 1. 중복 체크  
        collection = self.mongoManager.getCollection(ContentsQueueVO.collectionName)
        #data = {queueVO.to_mongo() }
        return collection.insert_one(queueVO.to_mongo()) 
        
    def find_all(self):
        try: 
            collection = self.mongoManager.getCollection(self.collectionName) 
            cursor = collection.find()
            result_list = [ContentsQueueVO.from_mongo(item) for item in cursor] 
            return result_list 
        
        except Exception as e:
            print(f"An error occurred: {e}")
            return None     #
      
    
if __name__=="__main__":
    ContentsQueueService().removeDuplicateUrl()