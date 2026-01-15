
from bson import ObjectId
import datetime
from typing import List
import pytz
import datetime
from datetime import datetime, timedelta
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO, ContentsOrgCategory
from ksubscribe_share.db.dbmodelV2.contentsCollectHistoryVO import ContentsCollectDetail, ContentsCollect, ContentsCollectHistoryVO
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO


#컨텐츠 수집 이력 
class ContentsQueueTest():

    mongoManager = MongoManager()  # MongoManager 싱글톤 인스턴스를 사용
    
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ContentsQueueTest, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        pass
    
    def case1_duplicate_url_test(self  ):

        collection = self.mongoManager.getCollection(ContentsQueueVO.collectionName)

        # 오늘 날짜 계산 
        today_start_utc = datetime.now().replace(hour=0,minute=0,second=0,microsecond=0).replace(tzinfo=pytz.timezone('Asia/Seoul') )
        today_end_utc = today_start_utc + timedelta(days=1)
        today_start_utc = today_start_utc.astimezone(pytz.utc)
        today_end_utc = today_end_utc.astimezone(pytz.utc)

        # MongoDB 쿼리 작성
        pipeline = [
            {
                "$match": {
                    "collectDt": { "$lt": today_end_utc}#"$gte": today_start_utc,
                }
            },
            {
                "$group": {
                    "_id": "$url",  # url별로 그룹화
                    "count": {"$sum": 1}  # 동일 url의 개수 계산
                }
            },
            {
                "$match": {
                    "count": {"$gt": 1}  # 중복된 url만 필터링
                }
            }
        ]

        # 쿼리 실행
        result = list(collection.aggregate(pipeline))

        # 결과 출력
        for doc in result:
            print(f"URL: {doc['_id']}, Count: {doc['count']}")

        # 2. dupli in contents 
        contents_collection = self.mongoManager.getCollection(ContentsVO.collectionName)
        contents_pipeline = [ 
            {
                "$match": {
                    "collectDt": {"$gte": today_start_utc, "$lt": today_end_utc}
                }
            },
            {
                "$group": {
                    "_id": "$url",  # url별로 그룹화
                    "count": {"$sum": 1}  # 동일 url의 개수 계산
                }
            },
            {
                "$match": {
                    "count": {"$gt": 1}  # 중복된 url만 필터링
                }
            }]
        
        contents_result = contents_collection.aggregate(contents_pipeline)
        
        for doc in contents_result:
            print(f"URL: {doc['_id']}, Count: {doc['count']}")

        
        
    def case2_select_url_test(self  ):

        collection = self.mongoManager.getCollection(ContentsQueueVO.collectionName)

        # 오늘 날짜 계산
        today = datetime.now()
        start_of_day = datetime(today.year, today.month, today.day)
        end_of_day = start_of_day + timedelta(days=1)

        # MongoDB 쿼리 작성
        pipeline = [
            {
                "$match": {
                    "collectDt": {"$gte": start_of_day, "$lt": end_of_day}
                }
            }        ]

        # 쿼리 실행
        result = list(collection.aggregate(pipeline))

        # 결과 출력
        index = 0
        for doc in result:
            index+=1
            print(f"idx : {index}, ID: {doc['_id']},URL : {doc['url']}")
           
    def case3_queue_history_match_test(self):
        # 1. queue 데이터 (오늘 하루동안)
        queue_collection = self.mongoManager.getCollection(ContentsQueueVO.collectionName)
        # start_of_day = datetime.utcnow().replace(tzinfo=pytz.utc) - timedelta(days=1)
        # end_of_day = start_of_day + timedelta(days=1)

        today_start_utc = datetime.now().replace(hour=0,minute=0,second=0,microsecond=0).replace(tzinfo=pytz.timezone('Asia/Seoul') )
        today_end_utc = today_start_utc + timedelta(days=1)
        today_start_utc = today_start_utc.astimezone(pytz.utc)
        today_end_utc = today_end_utc.astimezone(pytz.utc)



        queue_pipeline =            [ {"$match": {
                    "collectDt": {"$gte": today_start_utc, "$lt": today_end_utc}
                }
            }]
    
        queue_list =[ ContentsQueueVO.from_mongo(item) for item in queue_collection.aggregate(queue_pipeline)]


        # 2. history 데이터
        history_collection = self.mongoManager.getCollection(ContentsCollectHistoryVO.collectionName)
        history_pipeline =[ {"$match": {
                    "collectDt": {"$gte": today_start_utc, "$lt": today_end_utc}
                }
            }]
        #result = history_collection.aggregate(history_pipeline)
        history_list = list(history_collection.aggregate(history_pipeline))#list(result)#[ContentsCollectHistoryVO.from_mongo(item)  for item in result]
        contents_detail_list = self.generate_contents_detail_list(history_list)
        if len(contents_detail_list) != len(queue_list):
            print("queue의 길이와 contents_collect_history의 길이가 다릅니다.")
            return False
        
        for contents_detail in contents_detail_list:
            pass 
 
    def case3_duplicate_url_in_queue(self):
        collection = self.mongoManager.getCollection(ContentsQueueVO.collectionName)
        pipeline = [
                        {
                            "$group": {
                                "_id": "$url",  # category 값이 같은 항목끼리 그룹화
                                "count": {"$sum": 1}  # 그룹별 문서 개수 계산
                            }
                        }
                    ]

        results = collection.aggregate(pipeline)
        total_cnt = 0
        for result in results:
            total_cnt += result["count"]

            if result["count"] > 1:
                print(result)
        print(f"total Count = {total_cnt}")

    def generate_contents_detail_list(self,history_list):
        result_list = []
        for history in history_list:
            for collection in history['contentCollectList']:
                result_list.append(collection)
        return result_list

    def generate_contents_collect_hisotry(self):
        collection  = self.mongoManager.getCollection(ContentsCollectHistoryVO.collectionName)
        result = list(collection.find({ "collectDt": { "$type": "string" } }))
        print(len(result))
        pass 
    # collect 
    


if __name__ == "__main__":
    
    
    tester = ContentsQueueTest()
    tester.case3_duplicate_url_in_queue()
    #tester.case2_select_url_test()
    #tester.generate_contents_collect_hisotry()
    
    pass 

def main():
    pass 
        
        