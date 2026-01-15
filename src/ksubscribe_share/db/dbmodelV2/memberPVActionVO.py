from bson import ObjectId
from typing import List
import datetime
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from typing import TypeVar, Type, Dict
T = TypeVar("T", bound="BaseModel")  # BaseModel에 바인딩된 타입 변수

#actionType 종류
	    #PV,             //페이지뷰,        
     
class MemberPVActionVO(BaseMongoDocument):
    
    collectionName = "member_action_pv"
    
    def __init__(
        self, mberId: str = None, 
        actionType: str = None, 
        clientIp:str = None, 
        pageUrl:str = None, 
        actionDt: datetime = None,
        v1AplyId:int = None,
        orgName:str = None,
        mberName:str = None,
        _id: ObjectId = None,
    ):
        super().__init__(_id)  # BaseDocument의 생성자를 호출
        self.mberId = mberId
        self.actionType = actionType  
        self.clientIp = clientIp
        self.pageUrl = pageUrl   
        self.actionDt = actionDt        
        self.v1AplyId = v1AplyId
        self.orgName = orgName
        self.mberName = mberName
        
        
        
        
        
        

