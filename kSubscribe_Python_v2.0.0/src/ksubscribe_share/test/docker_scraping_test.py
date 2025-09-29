
from bson import ObjectId
import datetime
from typing import List

import datetime
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO
from datetime import datetime, timedelta
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO, ContentsOrgCategory
from ksubscribe_share.db.dbmodelV2.contentsCollectHistoryVO import ContentsCollectDetail, ContentsCollect, ContentsCollectHistoryVO
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
from ksubscribe_share.db.mongoManager import MongoManager


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
    
    def case1_duplicate_url_test(self, _id:ObjectId):

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
        
    def generate_test_contents(self):
        collection = self.mongoManager.getCollection(ContentsVO.collectionName)
        copy_targ = collection.find_one({'_id': ObjectId('67a2bc9d81e0251925805c78')})
        copy_targ['_id'] = None
        copy_targ['collectDt'] = "테스트용 날짜"
        result = collection.insert_one(copy_targ)

    def rename_field(self):

        collection = self.mongoManager.getCollection(ContentsVO.collectionName)
    
        # result =  collection.update_one(
        #     {"collectDt":"테스트용 날짜"},  # 테스트용 데이터만  변경
        #     {
        #         '$rename':{"contentsMeta.sentiments.positiveRatio":"positiveRatio"}
        #     }
        # )
        contents:List[ContentsVO] = list(collection.find())
        for c in contents:
            if c['contentsMeta']:
                if c['contentsMeta']['sentiments']:
                    reuslt = collection.update_one(
                    {'_id':c['_id']},
                    [{
                        "$set": {
                        "contentsMeta.sentiments": {
                            "$map": {
                            "input": "$contentsMeta.sentiments",
                            "as": "sentiments",
                            "in": {"$mergeObjects":[
                                "$$sentiments",
                                {"positiveRatio": "$$sentiments.positiveRatio"}
                                ]}   
                            }
                        }
                        }
                    }]
                    )
                    result_2 = collection.update_one({'_id':c['_id']}, {"$unset": {"contentsMeta.sentiments.$[].positiveRatio": 1}})
                                                                                                                
        pass 
         
#ContentsQueueTest().rename_field()