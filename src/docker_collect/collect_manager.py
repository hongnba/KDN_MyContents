
from bson import ObjectId
import datetime
from typing import List, Dict

import datetime

from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO, ContentsOrgCategory
from ksubscribe_share.db.dbmodelV2.contentsCollectHistoryVO import ContentsCollectDetail, ContentsCollect, ContentsCollectHistoryVO
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
from ksubscribe_share.db.mongoManager import MongoManager


#컨텐츠 수집 이력 
class CollectManager():
    
    _instance = None
    category_lastYMD: Dict[str, int] = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(CollectManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        pass

        
        
        
        
        


    
    
    