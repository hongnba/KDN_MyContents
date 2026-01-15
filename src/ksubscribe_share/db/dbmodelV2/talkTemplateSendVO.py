from bson import ObjectId
from typing import List
import datetime
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from typing import List
from typing import TypeVar, Type, Dict
T = TypeVar("T", bound="BaseModel")  # BaseModel에 바인딩된 타입 변수


class talkTemplateSendVO(BaseMongoDocument):
    
    collectionName = "talk_template_send"
    
    def __init__(
        self,
        mberId: str = None,                    #요청자 
        orgId: str = None,                     #기관ID
        allOrgMberSendYN : bool = None,        #전제 기관 멤버 전송 여부 
        mberTelnoList : List[str] = None,      #전화번호 목록 
        templateCode: str = None,              
        template: str = None,
        templateMsg : map[str, str] = None,
        reservedSendYN: bool = None,
        reservedDt: datetime = None,           #YYYYmmDD HHMM
        regDt: datetime = None,
        regId: str = None,
        sendSuccessYN : bool = None,
        _id: ObjectId = None,
    ):

        super().__init__(_id)  # BaseDocument의 생성자를 호출

        # 필드 초기화
        self.mberId = mberId
        self.orgId = orgId
        self.allOrgMberSendYN = allOrgMberSendYN
        self.mberTelnoList = mberTelnoList
        self.templateCode = templateCode
        self.template = template
        self.templateMsg  = templateMsg
        self.reservedSendYN = reservedSendYN
        self.reservedDt = reservedDt
        self.regDt = regDt
        self.regId = regId
        self.sendSuccessYN = sendSuccessYN
        
        
        
