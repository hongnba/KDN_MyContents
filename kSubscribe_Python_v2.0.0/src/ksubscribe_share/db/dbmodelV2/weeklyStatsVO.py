from bson import ObjectId
from datetime import datetime
from typing import List, Dict, Optional
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.keywordStatVO import KeywordStatVO
from typing import TypeVar, Type

T = TypeVar("T", bound="BaseModel")

class WeeklyStatsVO(BaseMongoDocument):
    """주별 기관 평판 통계"""
    
    collectionName = "weekly_stats"

    def __init__(
        self,
        orgId: str = None,
        positive_keywords: List[KeywordStatVO] = None,
        negative_keywords: List[KeywordStatVO] = None,
        articles_no: int = 0,
        positive_rate: float = 0.0,
        negative_rate: float = 0.0,
        last_calculate_date: datetime = None,
        daily_breakdown: Dict[str, Dict] = None,  # 일별 세부 데이터 {"2024-01-15": {"articles_no": 5, "positive_rate": 60.0, ...}}
        _id: ObjectId = None
    ):
        super().__init__(_id)
        self.orgId = orgId
        self.positive_keywords = positive_keywords if positive_keywords is not None else []
        self.negative_keywords = negative_keywords if negative_keywords is not None else []
        self.articles_no = articles_no
        self.positive_rate = positive_rate
        self.negative_rate = negative_rate
        self.last_calculate_date = last_calculate_date
        self.daily_breakdown = daily_breakdown if daily_breakdown is not None else {}

    def to_mongo(self):
        """클래스를 MongoDB 문서 형식으로 변환"""
        mongo_data = super().to_mongo()
        
        # 키워드 통계 변환
        if self.positive_keywords:
            mongo_data["positive_keywords"] = [kw.to_mongo() for kw in self.positive_keywords]
        if self.negative_keywords:
            mongo_data["negative_keywords"] = [kw.to_mongo() for kw in self.negative_keywords]
            
        return mongo_data

    @classmethod
    def from_mongo(cls: Type[T], mongo_data) -> T:
        """MongoDB 문서를 클래스로 변환"""
        instance = super().from_mongo(mongo_data)
        
        # 키워드 통계 변환
        if mongo_data.get("positive_keywords"):
            instance.positive_keywords = [
                KeywordStatVO.from_mongo(kw) for kw in mongo_data.get("positive_keywords", [])
            ]
        else:
            instance.positive_keywords = []
            
        if mongo_data.get("negative_keywords"):
            instance.negative_keywords = [
                KeywordStatVO.from_mongo(kw) for kw in mongo_data.get("negative_keywords", [])
            ]
        else:
            instance.negative_keywords = []
            
        return instance
