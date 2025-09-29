
from bson import ObjectId
import datetime
import traceback
from typing import List

import datetime

from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO, ContentsOrgCategory
from ksubscribe_share.db.dbmodelV2.contentsCollectHistoryVO import ContentsCollectDetail, ContentsCollect, ContentsCollectHistoryVO
from ksubscribe_share.db.dbmodelV2.contentsCollectErrorVO import ContentsCollectErrorVO
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService
import logging


#컨텐츠 수집 이력 
class ContentsCollectErrorService():
    
    mongoManager = MongoManager()  # MongoManager 싱글톤 인스턴스를 사용
    collectionName = "contents_collect_error" 
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ContentsCollectErrorService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        pass

    def insert_error(self,collect_dt, org_id,reg_dt,reg_id,edit_dt,edit_id,error_info,cate_id):
        """
        설명 
        Args:
            OOO : 설명 
        Returns:
            OOO: 설명 
        """           
        try:
            collection = self.mongoManager.getCollection(self.collectionName)
            insert_data = ContentsCollectErrorVO(
                collectDt  = collect_dt,  #수집일 
                orgId = org_id,            #구독기관ID  
                regDt= reg_dt,         #
                regId= reg_id,             #
                editDt= edit_dt,         #
                editId= edit_id,             #    
                errorInfo= error_info,
                cateId=cate_id
            )
            collection.insert_one(insert_data.to_mongo())
            pass 

        except Exception as e :
            print(e)
            pass 


 
    