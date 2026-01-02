from bson import ObjectId
from pymongo import MongoClient
from datetime import datetime
from typing import List, Dict
import re
from pydantic import BaseModel, Field

from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.errorInfo import ErrorInfo
from typing import TypeVar, Type, Dict, List
from ksubscribe_share.db.dbmodelV2.llmAnalysisMeta import LLMAnalysisMeta

T = TypeVar("T", bound="BaseModel")  # BaseModel에 바인딩된 타입 변수

# 컨텐츠 정보
# - 요약,분석,평판분석 저장

class SentimentInfo(BaseModel):
    def __init__(self, 
                 orgId: str = None, 
                 orgName: str = None, 
                 positiveRatio: float = None, 
                 negativeRatio: float = None, 
                 neutralRatio: float = None, 
                 reason:str = None, # 2025.12.15: 통합 프롬프트(CoT)의 '종합 판단 근거' 저장
                 positiveReason:str = None,
                 negativeReason: str = None, 
                 neutralReason: str = None, # 20251209 추가: 중립 비율 판단 근거
                 positiveKeywords:List[str] = None, 
                 negativeKeywords:List[str] = None,
                 neutralKeywords:List[str] = None
                 ):  
        self.orgId = orgId                    
        self.orgName = orgName
        self.positiveRatio = self._convert_to_float(positiveRatio)
        self.negativeRatio = self._convert_to_float(negativeRatio)
        self.neutralRatio = self._convert_to_float(neutralRatio)
        self.reason = reason
        self.positiveReason = positiveReason
        self.negativeReason = negativeReason
        self.neutralReason = neutralReason # 20251209 추가: 중립 비율 판단 근거
        self.positiveKeywords = positiveKeywords if positiveKeywords is not None else []
        self.negativeKeywords = negativeKeywords if negativeKeywords is not None else []
        self.neutralKeywords = neutralKeywords if neutralKeywords is not None else []  # 20251203 추가: 중립 키워드 필드

        
    def _convert_to_float(self, value):
        """
        값을 float으로 변환, 변환이 불가능한 경우 None 반환
        """
        try:
            if value is not None:
                return float(value)
        except (ValueError, TypeError):
            return 0
        return None        

class ContentsMeta(BaseModel):
    def __init__(
        self,
        keywords: list = None,#[str]
        predKeywords: Dict[str, float] = None,  # {키워드: 점수}
        shortSummary: str = None,
        longSummary: str = None,
        longDetailSummaryFormat1: str = None,
        longDetailSummaryFormat2: str = None,
        longDetailSummaryFormat3: str = None,
        longDetailSummaryFormat4: str = None,
        longDetailSummaryFormat5: str = None,
        sentiments: List[SentimentInfo] = None,
        errorInfo: ErrorInfo = None,
        llmSummaryMeta : LLMAnalysisMeta = None,  
        llmSentimentMeta : LLMAnalysisMeta = None,
        method:str = None   #ollama, gpt4o
    ):
        self.keywords = keywords
        self.shortSummary = shortSummary
        self.longSummary = longSummary
        self.longDetailSummaryFormat1 = longDetailSummaryFormat1
        self.longDetailSummaryFormat2 = longDetailSummaryFormat2
        self.longDetailSummaryFormat3 = longDetailSummaryFormat3
        self.longDetailSummaryFormat4 = longDetailSummaryFormat4
        self.longDetailSummaryFormat5 = longDetailSummaryFormat5
        self.predKeywords = predKeywords if predKeywords is not None else {}
        self.sentiments = sentiments if sentiments is not None else []
        self.errorInfo = errorInfo
        self.llmSummaryMeta = llmSummaryMeta
        self.llmSentimentMeta = llmSentimentMeta
        self.method = method
    
    def to_mongo(self):
        """클래스를 MongoDB 문서 형식으로 변환"""
        # 상위 클래스의 to_mongo 호출
        mongo_data = super().to_mongo()

        # 사용자 정의 객체를 변환
        if hasattr(self, "sentiments") and self.sentiments:
            mongo_data["sentiments"] = [item.to_mongo() for item in self.sentiments]
            
        if hasattr(self, "errorInfo") and  self.errorInfo:
            mongo_data["errorInfo"] = self.errorInfo.to_mongo()
            
        if hasattr(self, "llmSummaryMeta") and  self.llmSummaryMeta:
            mongo_data["llmSummaryMeta"] = self.llmSummaryMeta.to_mongo()

        if hasattr(self, "llmSentimentMeta") and  self.llmSentimentMeta:
            mongo_data["llmSentimentMeta"] = self.llmSentimentMeta.to_mongo()

        return mongo_data
            
    @classmethod
    def from_mongo(cls: Type[T], mongo_data) : 
        """
        MongoDB 문서 데이터를 Python 객체로 변환
        """
        # 상위 클래스의 from_mongo 호출
        instance = super().from_mongo(mongo_data)

        # 요청 카테고리 변환
        if "errorInfo" in mongo_data and  mongo_data.get("errorInfo"):
            instance.errorInfo = ErrorInfo.from_mongo(mongo_data.get("errorInfo")) 
        else:
            instance.errorInfo = None  # 기본값 설정
            
        if "sentiments" in mongo_data and  mongo_data.get("sentiments"):
            # 요청 카테고리 변환
            instance.sentiments = [
                SentimentInfo.from_mongo(sentimentalInfo)  # OrgCategory의 from_mongo 호출
                for sentimentalInfo in mongo_data.get("sentiments", [])
            ]        
        else:
            instance.sentiments = None  # 기본값 설정
            
        if "llmSummaryMeta" in mongo_data and  mongo_data.get("llmSummaryMeta"):
            instance.llmSummaryMeta = LLMAnalysisMeta.from_mongo(mongo_data.get("llmSummaryMeta")) 
        else:
            instance.llmSummaryMeta = None  # 기본값 설정
        
        if "llmSentimentMeta" in mongo_data and  mongo_data.get("llmSentimentMeta"):
            instance.llmSentimentMeta = LLMAnalysisMeta.from_mongo(mongo_data.get("llmSentimentMeta")) 
        else:
            instance.llmSentimentMeta = None  # 기본값 설정
                
        return instance

class ContentsRaw(BaseModel):
    def __init__(
        self, 
        title: str = None, 
        contents: str = None, 
        image: str = None, 
        errorInfo: ErrorInfo = None
    ):
        self.title = title
        self.contents = contents
        self.image = image
        self.errorInfo = errorInfo
        
    def to_mongo(self):
        """클래스를 MongoDB 문서 형식으로 변환"""
        # 상위 클래스의 to_mongo 호출
        mongo_data = super().to_mongo()

        # 사용자 정의 객체를 변환
        if self.errorInfo:
            mongo_data["errorInfo"] = self.errorInfo.to_mongo()

        return mongo_data
    
    @classmethod
    def from_mongo(cls: Type[T], mongo_data) : 
        """
        MongoDB 문서 데이터를 Python 객체로 변환
        """
        # 상위 클래스의 from_mongo 호출
        instance = super().from_mongo(mongo_data)

        # 요청 카테고리 변환
        if mongo_data.get("errorInfo"):
            instance.errorInfo = ErrorInfo.from_mongo(mongo_data.get("errorInfo")) 
            
        return instance
        
class ContentsVO(BaseMongoDocument):

    collectionName = "contents"

    def __init__(
        self,
        title: str = None, 
        url:str = None, 
        contentsOrgId: str = None,      #컨텐츠 제공 기관 ID 
        categoryId: str = None,        
        originallink: str = None,
        link: str = None,
        pubDt: datetime = None,           #기사 발행일 
        collectDt : datetime = None,      #docker_collect(KDN) 날짜 
        collectKeyword : str = None,      #collect 수집 근거 키워드 

        lookCount: int = None,
        likeCount: int = None,
        disLikeCount: int = None,
        lookIds: List[str] = None,
        likeIds: List[str] = None,
        disLikeIds: List[str] = None,
        
        rawCollectSucYN: str = None,      #raw 데이터 수집 성공 여부  
        contentsRaw: ContentsRaw = None,   #raw 데이터 객체 
        rawCollectDt : datetime = None,    #raw 데이터 수집일 
        metaSucYN: str = None,            #데이터 분석 성공 YN 
        contentsMeta: ContentsMeta = None, #데이터 분석 결과 
        metaAnalyzeDt : datetime = None,   #데이터 분석일 
        imageId:str = None,
        _id: ObjectId = None,
        v1ContentsIdx : str = None,        #version1에서 사용한 contents SEQ 
        
        # 데이터 전송시 사용목적 (mongodb에는 저장하지 않음)
        contentsOrgName: str =  Field(exclude=True),
        categoryName: str =  Field(exclude=True),
    ):

        super().__init__(_id)  # BaseDocument의 생성자를 호출
        self.title = title
        self.url = url
        self.contentsOrgId = contentsOrgId
        self.contentsOrgName = contentsOrgName
        self.categoryId = categoryId
        self.categoryName = categoryName
        self.originallink = originallink
        self.link = link
        self.pubDt = pubDt
        self.collectDt = collectDt
        self.collectKeyword = collectKeyword
        self.lookCount = lookCount
        self.likeCount = likeCount
        self.disLikeCount = disLikeCount
        self.lookIds = lookIds if lookIds is not None else []
        self.likeIds = likeIds if likeIds is not None else []
        self.disLikeIds = disLikeIds if disLikeIds is not None else []
        self.rawCollectSucYN = rawCollectSucYN
        self.contentsRaw = contentsRaw
        self.rawCollectDt = rawCollectDt
        self.metaSucYN = metaSucYN
        self.contentsMeta = contentsMeta
        self.metaAnalyzeDt = metaAnalyzeDt
        self.imageId = imageId
        self.v1ContentsIdx = v1ContentsIdx
        
    def to_mongo(self):
        """클래스를 MongoDB 문서 형식으로 변환"""
        # 상위 클래스의 to_mongo 호출
        mongo_data = super().to_mongo()

        # 사용자 정의 객체를 변환
        if self.contentsRaw:
            mongo_data["contentsRaw"] = self.contentsRaw.to_mongo()
        if self.contentsMeta:
            mongo_data["contentsMeta"] = self.contentsMeta.to_mongo()

        return mongo_data
    
    @classmethod
    def from_mongo(cls: Type[T], mongo_data) -> T:
        """
        MongoDB 문서 데이터를 Python 객체로 변환
        """
        # 상위 클래스의 from_mongo 호출
        instance = super().from_mongo(mongo_data)

        # 요청 카테고리 변환
        if mongo_data.get("contentsRaw"):
            instance.contentsRaw = ContentsRaw.from_mongo(mongo_data.get("contentsRaw")) 
        if mongo_data.get("contentsMeta"):
            instance.contentsMeta = ContentsMeta.from_mongo(mongo_data.get("contentsMeta"))
                                    
        return instance
        # instance.contentsMeta = ContentsMeta.from_mongo(mongo_data.get("contentsMeta")) 
