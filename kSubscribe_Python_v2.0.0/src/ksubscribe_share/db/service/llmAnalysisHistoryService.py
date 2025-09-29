
from bson import ObjectId
import datetime
from typing import List
import datetime

from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO, ContentsOrgCategory
from ksubscribe_share.db.dbmodelV2.contentsCollectHistoryVO import ContentsCollectDetail, ContentsCollect, ContentsCollectHistoryVO
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.dbmodelV2.commCodeVO import CommCodeVO
from ksubscribe_share.db.dbmodelV2.llmAnalysisMeta import LLMAnalysisVO
from ksubscribe_share.db.service.baseQueryService import BaseQueryService


#컨텐츠 수집 이력 
class llmAnalysisHistoryService():

    mongoManager = MongoManager()  # MongoManager 싱글톤 인스턴스를 사용
    
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(llmAnalysisHistoryService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        pass
    
    def insert_daily_history(self, llmAnalysisVO:LLMAnalysisVO):
        try:
            result = BaseQueryService.insert_one(llmAnalysisVO)            
            return result 
        except Exception as e :
            print(e)
            return None
    