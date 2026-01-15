
from bson import ObjectId
import datetime
from typing import List

import datetime
from pymongo.results import InsertOneResult, UpdateResult, DeleteResult

from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.memberPVActionVO import MemberPVActionVO
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.service.baseQueryService import BaseQueryService


#컨텐츠 수집 이력 
class memberPVActionService():
    
    mongoManager = MongoManager()           # MongoManager 싱글톤 인스턴스를 사용
    collectionName = "member_action_pv"
        
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(memberPVActionService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        pass 

                
    def insertPVAction(self, mberId:str, clientIp:str, pageUrl:str, actionDt:datetime): 
        
        try:
        
            memberPVActionVO = MemberPVActionVO()
            memberPVActionVO.mberId = mberId
            memberPVActionVO.actionType = "PAGEVIEW"
            memberPVActionVO.clientIp = clientIp
            memberPVActionVO.pageUrl = pageUrl
            memberPVActionVO.actionDt = actionDt
            
            result:InsertOneResult = BaseQueryService.insert_one(memberPVActionVO) 
            
            # 결과 출력
            if result.inserted_id:
                print(f"문서가 성공적으로 삽입되었습니다. 삽입된 문서의 ID: {result.inserted_id}")
            else:
                print(f"문서 삽입에 실패했습니다.")
                
            return result

        except Exception as e:
            print(f"An error occurred: {e}")
            
       