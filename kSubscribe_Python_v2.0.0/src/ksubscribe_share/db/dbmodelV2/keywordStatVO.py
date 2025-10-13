from typing import List
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseModel
from typing import TypeVar, Type

T = TypeVar("T", bound="BaseModel")

class KeywordStatVO(BaseModel):
    """키워드 통계 정보 - 모든 통계 엔티티에서 공통 사용"""
    
    def __init__(
        self,
        keyword: str = None,
        count: int = 0,
        related_articles: List[str] = None  # Contents collection의 _id 리스트
    ):
        self.keyword = keyword
        self.count = count
        self.related_articles = related_articles if related_articles is not None else []

    def to_mongo(self):
        """MongoDB 문서 형식으로 변환"""
        return super().to_mongo()

    @classmethod
    def from_mongo(cls: Type[T], mongo_data) -> T:
        """MongoDB 문서를 클래스로 변환"""
        return super().from_mongo(mongo_data)
