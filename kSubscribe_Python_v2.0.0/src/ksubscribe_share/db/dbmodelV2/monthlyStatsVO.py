from bson import ObjectId
from datetime import datetime
from typing import List, Dict, Optional
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.keywordStatVO import KeywordStatVO
from typing import TypeVar, Type

T = TypeVar("T", bound="BaseModel")

class MonthlyStatsVO(BaseMongoDocument):
    """월별 기관 평판 통계"""
    
    collectionName = "monthly_stats"

    def __init__(
        self,
        orgId: str = None,
        positive_keywords: List[KeywordStatVO] = None,
        negative_keywords: List[KeywordStatVO] = None,
        articles_no: int = 0,
        positive_rate: float = 0.0,
        negative_rate: float = 0.0,
        neutral_rate: float = 0.0,
        last_calculate_date: datetime = None,
        start_date: datetime = None,
        end_date: datetime = None,
        period: str = "한달",
        
        # Article counts and percentages
        total_positive_contents_count: int = 0,
        total_positive_contents_percent: float = 0.0,
        total_negative_contents_count: int = 0,
        total_negative_contents_percent: float = 0.0,
        total_neutral_contents_count: int = 0,
        total_neutral_contents_percent: float = 0.0,
        total_unknown_contents_count: int = 0,
        total_unknown_contents_percent: float = 0.0,
        
        # Keyword lists (top keywords)
        total_positive_keyword_list: List[str] = None,
        total_negative_keyword_list: List[str] = None,
        total_most_frequent_keyword_list: List[str] = None,
        
        # Summary lists (top article summaries)
        total_positive_summary_list: List[str] = None,
        total_negative_summary_list: List[str] = None,
        total_neutral_summary_list: List[str] = None,
        
        # Weekly breakdown data
        weekly_breakdown: Dict[str, Dict] = None,  # 주별 세부 데이터 {"2024-W03": {"articles_no": 15, "positive_rate": 65.0, ...}}
        weekly_contents_count_map: Dict[str, int] = None,  # {"1주차": 17, "2주차": 7, ...}
        weekly_positive_ratio_map: Dict[str, float] = None,  # {"1주차": 63.824, "2주차": 60.714, ...}
        weekly_negative_ratio_map: Dict[str, float] = None,  # {"1주차": 29.706, "2주차": 35.0, ...}
        weekly_positive_keyword_rank_map: Dict[str, List[str]] = None,  # {"1주차": ["키워드1", "키워드2"], ...}
        weekly_negative_keyword_rank_map: Dict[str, List[str]] = None,  # {"1주차": ["키워드1", "키워드2"], ...}
        weekly_most_frequent_keyword_rank_map: Dict[str, List[str]] = None,  # {"1주차": ["키워드1", "키워드2"], ...}
        
        _id: ObjectId = None
    ):
        super().__init__(_id)
        self.orgId = orgId
        self.positive_keywords = positive_keywords if positive_keywords is not None else []
        self.negative_keywords = negative_keywords if negative_keywords is not None else []
        self.articles_no = articles_no
        self.positive_rate = positive_rate
        self.negative_rate = negative_rate
        self.neutral_rate = neutral_rate
        self.last_calculate_date = last_calculate_date
        self.start_date = start_date
        self.end_date = end_date
        self.period = period
        
        # Article counts and percentages
        self.total_positive_contents_count = total_positive_contents_count
        self.total_positive_contents_percent = total_positive_contents_percent
        self.total_negative_contents_count = total_negative_contents_count
        self.total_negative_contents_percent = total_negative_contents_percent
        self.total_neutral_contents_count = total_neutral_contents_count
        self.total_neutral_contents_percent = total_neutral_contents_percent
        self.total_unknown_contents_count = total_unknown_contents_count
        self.total_unknown_contents_percent = total_unknown_contents_percent
        
        # Keyword lists
        self.total_positive_keyword_list = total_positive_keyword_list if total_positive_keyword_list is not None else []
        self.total_negative_keyword_list = total_negative_keyword_list if total_negative_keyword_list is not None else []
        self.total_most_frequent_keyword_list = total_most_frequent_keyword_list if total_most_frequent_keyword_list is not None else []
        
        # Summary lists
        self.total_positive_summary_list = total_positive_summary_list if total_positive_summary_list is not None else []
        self.total_negative_summary_list = total_negative_summary_list if total_negative_summary_list is not None else []
        self.total_neutral_summary_list = total_neutral_summary_list if total_neutral_summary_list is not None else []
        
        # Weekly breakdown data
        self.weekly_breakdown = weekly_breakdown if weekly_breakdown is not None else {}
        self.weekly_contents_count_map = weekly_contents_count_map if weekly_contents_count_map is not None else {}
        self.weekly_positive_ratio_map = weekly_positive_ratio_map if weekly_positive_ratio_map is not None else {}
        self.weekly_negative_ratio_map = weekly_negative_ratio_map if weekly_negative_ratio_map is not None else {}
        self.weekly_positive_keyword_rank_map = weekly_positive_keyword_rank_map if weekly_positive_keyword_rank_map is not None else {}
        self.weekly_negative_keyword_rank_map = weekly_negative_keyword_rank_map if weekly_negative_keyword_rank_map is not None else {}
        self.weekly_most_frequent_keyword_rank_map = weekly_most_frequent_keyword_rank_map if weekly_most_frequent_keyword_rank_map is not None else {}

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
