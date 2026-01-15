from bson import ObjectId
from datetime import datetime
from typing import List, Dict, Optional
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.keywordStatVO import KeywordStatVO
from typing import TypeVar, Type

T = TypeVar("T", bound="BaseModel")

class DailyStatsVO(BaseMongoDocument):
    """일별 기관 평판 통계"""
    
    collectionName = "daily_stats"

    def __init__(
        self,
        orgId: str = None,
        last_calculate_date: datetime = None,

        start_date: datetime = None,
        end_date: datetime = None,
        
        totalPositiveKeywordList: List[str] = None,
        totalNegativeKeywordList: List[str] = None,
        
        # Content counts and ratios
        totalContentsCounts: int = 0,
        pastTotalContentsCounts: int = 0,

        averageNegativeRatio: float = 0.0,
        averageNeutralRatio: float = 0.0,
        averagePositiveRatio: float = 0.0,
        pastAveragePositiveRatio: float = 0.0,

        totalPositiveContentsCount: int = 0,
        totalNegativeContentsCount: int = 0,
        totalNeutralContentsCount: int = 0,
        
        # Sentiment sorted maps (article-specific evaluation data)
        positiveSortedMap: List[Dict] = None,
        negativeSortedMap: List[Dict] = None,
        
        # Keyword maps (for Word Cloud)
        positiveKeywordMap: Dict[str, int] = None,
        negativeKeywordMap: Dict[str, int] = None,
        
        # Reputation change reason and results
        ollamaReputationChangeReason: str = None,
        negativeResult: Dict[str, float] = None,
        positiveResult: Dict[str, float] = None,
        neutralResult: Dict[str, float] = None,
        
        _id: ObjectId = None
    ):
        super().__init__(_id)
        self.orgId = orgId
        self.last_calculate_date = last_calculate_date
        self.start_date = start_date
        self.end_date = end_date
        
        # Query period and keyword lists
        self.startDate = start_date
        self.endDate = end_date
        self.totalPositiveKeywordList = totalPositiveKeywordList if totalPositiveKeywordList is not None else []
        self.totalNegativeKeywordList = totalNegativeKeywordList if totalNegativeKeywordList is not None else []
        
        # Content counts and ratios
        self.totalContentsCounts = totalContentsCounts
        self.pastTotalContentsCounts = pastTotalContentsCounts
        self.averageNegativeRatio = averageNegativeRatio
        self.averageNeutralRatio = averageNeutralRatio
        self.averagePositiveRatio = averagePositiveRatio
        self.pastAveragePositiveRatio = pastAveragePositiveRatio
        self.totalPositiveContentsCount = totalPositiveContentsCount
        self.totalNegativeContentsCount = totalNegativeContentsCount
        self.totalNeutralContentsCount = totalNeutralContentsCount
        
        # Sentiment sorted maps
        self.positiveSortedMap = positiveSortedMap if positiveSortedMap is not None else []
        self.negativeSortedMap = negativeSortedMap if negativeSortedMap is not None else []
        
        # Keyword maps
        self.positiveKeywordMap = positiveKeywordMap if positiveKeywordMap is not None else {}
        self.negativeKeywordMap = negativeKeywordMap if negativeKeywordMap is not None else {}
        
        # Reputation change reason and results
        self.ollamaReputationChangeReason = ollamaReputationChangeReason
        self.negativeResult = negativeResult if negativeResult is not None else {}
        self.positiveResult = positiveResult if positiveResult is not None else {}
        self.neutralResult = neutralResult if neutralResult is not None else {}

    def to_mongo(self):
        """클래스를 MongoDB 문서 형식으로 변환"""
        return super().to_mongo()

    @classmethod
    def from_mongo(cls: Type[T], mongo_data) -> T:
        """MongoDB 문서를 클래스로 변환"""
        return super().from_mongo(mongo_data)
