
from bson import ObjectId
import datetime
from typing import List
import datetime
import pytz

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
    
    def find_by_pub_dates(self, pub_dates: List[str]):
        """
        여러 pubDt 날짜의 데이터를 한 번에 조회
        
        Args:
            pub_dates: pubDt 필터링할 날짜 리스트 (예: ["2025-11-22", "2025-11-26"])
        
        Returns:
            ContentsQueueVO 리스트
        """
        try: 
            collection = self.mongoManager.getCollection(self.collectionName)
            
            # 날짜 문자열을 datetime 객체로 변환
            date_objects = []
            for date_str in pub_dates:
                try:
                    # "2025-11-22" 형식을 datetime으로 변환
                    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                    # UTC timezone 추가 (MongoDB는 UTC 사용)
                    dt_utc = pytz.utc.localize(dt)
                    date_objects.append(dt_utc)
                except ValueError:
                    # 다른 형식 시도: "20251122" 형식
                    try:
                        dt = datetime.datetime.strptime(date_str, "%Y%m%d")
                        dt_utc = pytz.utc.localize(dt)
                        date_objects.append(dt_utc)
                    except ValueError:
                        print(f"Invalid date format: {date_str}, skipping...")
                        continue
            
            if not date_objects:
                print("No valid dates provided")
                return []
            
            # $in 연산자로 여러 날짜 한 번에 조회
            # pubDt가 datetime 객체인 경우와 문자열인 경우 모두 처리
            filter_query = {
                "$or": [
                    {"pubDt": {"$in": date_objects}},  # datetime 객체인 경우
                    {"pubDt": {"$in": pub_dates}}      # 문자열인 경우
                ]
            }
            
            cursor = collection.find(filter_query)
            result_list = [ContentsQueueVO.from_mongo(item) for item in cursor] 
            return result_list 
        except Exception as e:
            print(f"An error occurred in find_by_pub_dates: {e}")
            return []
      
    
if __name__=="__main__":
    ContentsQueueService().removeDuplicateUrl()