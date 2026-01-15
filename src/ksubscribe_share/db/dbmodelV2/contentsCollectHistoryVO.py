
from bson import ObjectId
import datetime
from typing import List
import datetime
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from typing import TypeVar, Type, Dict
T = TypeVar("T", bound="BaseModel")  # BaseModel에 바인딩된 타입 변수

#최근 컨텐츠 수집 이력  
# - 여기에 쌓인 데이터를 하나씩 꺼내서 컨텐츠 스크롤링->요약,분석,평판분석 등등등 해서 Contents Collection에 넣음. 
# - Contents 에 넣어지면 여기는 삭제됨. 
class ContentsCollectDetail(BaseModel):
    
    def __init__(self, 
                 title: str =None, 
                 url: str =None, 
                 shortUrl:str =None, 
                 pubDt: datetime = None, 
                 sucYN:bool = None,
                 naverUrl: str =None,
                 collectDt : datetime = None,
                 collectKeyword : List[str] = None):
        self.title = title        
        self.url = url  # 원래 url
        self.shortUrl= shortUrl
        self.pubDt = pubDt
        self.sucYN = sucYN 
        self.naverUrl = naverUrl    # 네이버에서 한번 warpping 한 url
        self.collectDt = collectDt
        self.collectKeyword = collectKeyword if collectKeyword is not None else []
        

#컨텐츠 수집 이력 
class ContentsCollect(BaseModel):
    
    def __init__(self, 
                 contentOrgId: str =None, 
                 categoryId: str =None, 
                 collectionDetailList : List[ContentsCollectDetail]=None):
        # 필드 초기화
        self.contentOrgId = contentOrgId
        self.categoryId = categoryId
        self.collectionDetailList = collectionDetailList if collectionDetailList is not None else []        
   
    def to_mongo(self):
        """클래스를 MongoDB 문서 형식으로 변환"""
        # 상위 클래스의 to_mongo 호출
        mongo_data = super().to_mongo()

        # 사용자 정의 객체를 변환
        if self.collectionDetailList:
            mongo_data["collectionDetailList"] = [item.to_mongo() for item in self.collectionDetailList]

        return mongo_data
    
    @classmethod
    def from_mongo(cls: Type[T], mongo_data) : 
        """
        MongoDB 문서 데이터를 Python 객체로 변환
        """
        # 상위 클래스의 from_mongo 호출
        instance = super().from_mongo(mongo_data)

        # 요청 카테고리 변환
        instance.collectionDetailList = [
            ContentsCollectDetail().from_mongo(collectionDetail)  # OrgCategory의 from_mongo 호출
            for collectionDetail in mongo_data.get("collectionDetailList", [])
        ]    
                


#컨텐츠 수집 이력 
class ContentsCollectHistoryVO(BaseMongoDocument):
    
    collectionName = 'contents_collect_history'    

    def __init__(self, 
                 collectDt: str = None,                                                     
                 contentOrgId: str =None, 
                 contentCollectList: List[ContentsCollect] = None, 
                 _id: ObjectId = None):
        

        super().__init__(_id)  # BaseDocument의 생성자를 호출
        
        # 필드 초기화
        # self._id = ObjectId()
        self.collectDt = collectDt
        self.contentOrgId = contentOrgId
        self.contentCollectList = contentCollectList if contentCollectList is not None else []

   
    def to_mongo(self):
        """클래스를 MongoDB 문서 형식으로 변환"""
        # 상위 클래스의 to_mongo 호출
        mongo_data = super().to_mongo()

        # 사용자 정의 객체를 변환
        if self.contentCollectList:
            mongo_data["contentCollectList"] = [item.to_mongo() for item in self.contentCollectList]

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
        instance.contentCollectList = [
            ContentsCollect().from_mongo(contentCollect)  # OrgCategory의 from_mongo 호출
            for contentCollect in mongo_data.get("contentCollectList", [])
        ]    
        
        
            
    
    