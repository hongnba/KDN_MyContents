
from bson import ObjectId
import datetime
from typing import List
import datetime

from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.originalContentsVO import OriginalContentsVO
from ksubscribe_share.db.mongoManager import MongoManager


#컨텐츠 수집 이력 
class OriginalContentsService():

    mongoManager = MongoManager()  # MongoManager 싱글톤 인스턴스를 사용
    collectionName = "original_contents"
    
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(OriginalContentsService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        pass

    
    def insertOne(self, originalContents: OriginalContentsVO, collectYMD, keyword:str = None,session = None):
        collection = self.mongoManager.getCollection(self.collectionName)
        return collection.insert_one(originalContents.to_mongo()) 
        
      
    
if __name__=="__main__":
    pass