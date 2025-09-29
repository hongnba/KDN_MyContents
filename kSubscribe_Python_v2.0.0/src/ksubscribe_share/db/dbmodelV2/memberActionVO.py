from bson import ObjectId
from typing import List
import datetime
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from typing import TypeVar, Type, Dict
T = TypeVar("T", bound="BaseModel")  # BaseModel에 바인딩된 타입 변수


#actionType 종류
	    #LOGIN,          //로그인,          (mberId, actionType, signIp, sucYN, actionDt)
	    #LOGOUT,         //로그아웃,        (mberId,actionType,  signIp, sucYN, actionDt)
	    #CHANGEPWD,      //비밀번호 변경    (mberId,actionType,  signIp, sucYN, actionDt)
	    #SIGNUP,         //회원가입,        (mberId,actionType,  signMethod, signIp, actionDt)
	    #SUBORG,         //기관 구독,       (mberId,actionType,  orgId, sucYN, actionDt)
	    #UNSUBORG,       //기관 구독 탈퇴,  (mberId,actionType, orgId, sucYN, actionDt)   
	    #SUBCATEGORY,    //카테고리 구독,   (mberId,actionType, orgId, cateId, sucYN, actionDt)  
	    #UNSUBCATEGORY,  //카테고리 구독 탈퇴, (mberId,actionType, orgId, cateId, sucYN, actionDt)
	    #SUBKEYWORD,     //키워드 구독,     (mberId,actionType, keyword, subscribeYN , sucYN, actionDt)
	    #UNSUBKEYWORD,   //키워드 구독 탈퇴, (mberId,actionType, keyword, subscribeYN , sucYN, actionDt)
	    #REGISTERORG, 	 //신규 기관 등록,  (mberId,actionType, orgId , sucYN, actionDt)
	    #VIEWCONTENTS,   //컨텐츠 조회,     (mberId,actionType, contentsId, sucYN, actionDt)
	    #LIKEFEEDBACK;   //컨텐츠 피드백 (좋아요, 싫어요) , (mberId, actionType, feedback, contentsId, sucYN, actionDt)
class MemberActionVO(BaseMongoDocument):
    
    collectionName = "member_action"
    
    def __init__(
        self, 
        mberId: str = None, actionType: str = None, 
        orgId:str = None, cateId:str = None, 
        keyword:str = None, contentsId:str = None, 
        subscribeYN:str = None, feedback:str = None,
        signMethod:str = None, signIp:str = None, 
        sucYN: str = None, failReason: str = None, 
        actionDt: datetime = None,_id: ObjectId = None,
    ):
        super().__init__(_id)  
        self.mberId = mberId
        self.actionType = actionType  
        self.orgId = orgId
        self.cateId = cateId
        self.keyword = keyword
        self.feedback = feedback        # like, dislike, none
        self.contentsId = contentsId
        self.subscribeYN = subscribeYN  #Y:가입, N:해지 
        self.signMethod = signMethod    #NORMAL, KAKAO, NAVER, GOOGLE
        self.signIp = signIp
        self.sucYN = sucYN
        self.failReason = failReason
        self.actionDt = actionDt        
        
        
        
        
        
        

