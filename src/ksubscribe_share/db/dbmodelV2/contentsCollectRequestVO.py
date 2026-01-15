
from bson import ObjectId
from typing import List, Dict
import datetime 
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO
from typing import TypeVar, Type, Dict
T = TypeVar("T", bound="BaseModel")  # BaseModel에 바인딩된 타입 변수


class OrgCategory(BaseModel): 
    
    def __init__(self,     
                 orgId:str =None,
                 orgName:str =None,
                 cateId:str =None,
                 cateName:str =None,
                 url:str =None): 
        self.orgId = orgId
        self.orgName = orgName
        self.cateId = cateId
        self.cateName = cateName
        self.url = url

#컨텐츠 수집 이력 
class ContentsCollectRequestVO (BaseMongoDocument):
    
    collectionName = 'cotents_collect_request'  
      
    def __init__(self, 
                 mberId: str =None,                                                     #요청자 ID
                 mberName: str =None,                                                   #요청자 이름 
                 mberOrgId : str =None,                                                 #요청자 기관 
                 requestTitle: str =None,                                               #요청 제목 
                 requestUrl: str =None,                                            #요청자 내용 
                 approveStatus: str =None,                                              #승인여부 
                 approveDt: datetime=None,                                             #요청자 일자
                 denyReason: str =None,                                                 #반려사유 
                 orgId : str =None,     
                 orgName : str =None,                                                   #구독기관 
                 regDt: datetime=None,                                                 #
                 regId: str =None,                                                      #
                 editDt: datetime =None,                                                #
                 editId: str=None,                                                     #
                 requestCategory : List[OrgCategory] = None,   
                 contentsOrgVO : ContentsOrgVO = None,    
                 _id: ObjectId = None):
        
        super().__init__(_id)  #BaseDocument의 생성자를 호출

        # 필드 초기화
        self.mberId = mberId
        self.mberName = mberName
        self.mberOrgId = mberOrgId
        self.requestTitle = requestTitle
        self.requestUrl = requestUrl
        self.approveStatus = approveStatus
        self.approveDt = approveDt
        self.denyReason = denyReason
        self.orgId = orgId
        self.orgName = orgName
        self.regDt = regDt
        self.regId = regId
        self.editDt = editDt
        self.editId = editId
        self.requestCategory = requestCategory if requestCategory is not None else []
        self.contentsOrgVO = contentsOrgVO
        
    def to_mongo(self):
        """클래스를 MongoDB 문서 형식으로 변환"""
        # 상위 클래스의 to_mongo 호출
        mongo_data = super().to_mongo()

        # 사용자 정의 객체를 변환
        if self.requestCategory:
            mongo_data["requestCategory"] = [item.to_mongo() for item in self.requestCategory]
        # 사용자 정의 객체를 변환
        mongo_data["contentsOrgVO"] = self.contentsOrgVO.to_mongo() 

        return mongo_data     
    
    @classmethod
    def from_mongo(cls: Type[T], mongo_data) : 
        """
        MongoDB 문서 데이터를 Python 객체로 변환
        """
        # 상위 클래스의 from_mongo 호출
                # 상위 클래스의 from_mongo 호출
        instance = super().from_mongo(mongo_data)

        # 요청 카테고리 변환
        instance.requestCategory = [
            OrgCategory().from_mongo(category)  # OrgCategory의 from_mongo 호출
            for category in mongo_data.get("requestCategory", [])
        ]    
        instance.contentsOrgVO = ContentsOrgVO.from_mongo(mongo_data.get("contentsOrgVO")) 
        
        
        
        
        
