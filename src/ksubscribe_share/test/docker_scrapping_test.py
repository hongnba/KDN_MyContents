
from bson import ObjectId
import datetime
from typing import List

import datetime
from docker_scraping.contents_scraping import ContentsScraping
from datetime import datetime, timedelta
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO, ContentsOrgCategory
from ksubscribe_share.db.dbmodelV2.contentsCollectHistoryVO import ContentsCollectDetail, ContentsCollect, ContentsCollectHistoryVO
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO
import pytz 

mongoManager = MongoManager()


class ContentsScrappingTest():

    mongoManager = MongoManager()  # MongoManager 싱글톤 인스턴스를 사용
    
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ContentsScrappingTest, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        pass
    
 
 
    def find_image_in_contents(self):
        contents_collection = self.mongoManager.getCollection(ContentsVO.collectionName) 

        today_start_utc = datetime.now().replace(hour=0,minute=0,second=0,microsecond=0).replace(tzinfo=pytz.timezone('Asia/Seoul') )
        today_end_utc = today_start_utc + timedelta(days=1)
        today_start_utc = today_start_utc.astimezone(pytz.utc)
        today_end_utc = today_end_utc.astimezone(pytz.utc) 

        contents_pipeline =            [ {"$match": {
                    "collectDt": {"$gte": today_start_utc, "$lt": today_end_utc}
                }
            }]
    
        contents_list =list(contents_collection.aggregate(contents_pipeline))#[ ContentsVO.from_mongo(item) for item in ]
        
        for contents in contents_list:
            print(f"image id : {contents['imageId']}")
            if contents['imageId'] is None :
                print(f"image id 가 존재하지 않습니다. : {contents['_id']}")
    def find_empty_errorInfo(self):
        today_start_utc = datetime.now().replace(hour=0,minute=0,second=0,microsecond=0).replace(tzinfo=pytz.timezone('Asia/Seoul') )
        today_end_utc = today_start_utc + timedelta(days=1)
        today_start_utc = today_start_utc.astimezone(pytz.utc)
        today_end_utc = today_end_utc.astimezone(pytz.utc) 

        contents_collection = self.mongoManager.getCollection(ContentsVO.collectionName) 
        filter = {"contentsMeta.errorInfo":{
             '$type': "string"
        }}
        result = list(contents_collection.find(filter))
        print(len(result)) 
        
    def update_image_id(self):
        contents_collection = self.mongoManager.getCollection(ContentsVO.collectionName) 
        result  = list(contents_collection.find({"imageId":None}))
        scrapper = ContentsScraping()
        for c in result: 
            vo = ContentsVO.from_mongo(c)
            vo = scrapper.generate_imageId(vo)
            contents_collection.update_one({"_id":vo._id},
                                           {"$set":{"imageId":vo.imageId}})
    

    def find_sentiment_score(self):
        today_start_utc = datetime.now().replace(hour=0,minute=0,second=0,microsecond=0).replace(tzinfo=pytz.timezone('Asia/Seoul') )
        today_end_utc = today_start_utc + timedelta(days=1)
        today_start_utc = today_start_utc.astimezone(pytz.utc)
        today_end_utc = today_end_utc.astimezone(pytz.utc) 

        contents_collection = self.mongoManager.getCollection(ContentsVO.collectionName) 
        filter = {"contentsMeta.sentiments.positiveRatio":{
             '$type': "string"
        }}
        
        resultList = list(contents_collection.find(filter))
        
        for result in resultList:
            contentsVO = ContentsVO.from_mongo(result)
            print(contentsVO.contentsMeta.sentiments)
        
        print(len(result))     

    def find_wrong_type_data(self):
        contents_collection = self.mongoManager.getCollection(ContentsVO.collectionName) 
        filter = { "contentsMeta.sentiments.positiveRatio": { "$type": "string" } }
        #db.collection.find({ fieldName: { $type: "string" } })
        result = list(contents_collection.find(filter))
        # 1. type



        pass 









ContentsScrappingTest().find_wrong_type_data()

