from bson import ObjectId
from ksubscribe_share.db.dbmodel.sentimentInfo import SentimentInfo


class NewsMeta:
    def __init__(
        self,
        keywords ,#:list[str],
        shortSummary: str,
        longSummary: str,
        organization,#: list[str],
        sentiment: SentimentInfo,
    ):
        self.keywords = keywords
        self.shortSummary = shortSummary
        self.longSummary = longSummary
        self.organization = organization
        self.sentiment = sentiment

    @classmethod
    def from_mongo(cls, document):
        """MongoDB 문서를 클래스로 변환"""

        sentiment_data = document.get("sentiment", {})
        sentiment = SentimentInfo.from_mongo(sentiment_data) if sentiment_data else None

        return cls(
            keywords=document.get("keywords", []),
            shortSummary=document.get("shortSummary"),
            longSummary=document.get("longSummary"),
            organization=document.get("organization", []),
            sentiment=sentiment,
        )

    def to_mongo(self):
        """클래스를 MongoDB 문서 형식으로 변환"""
        return {
            "keywords": self.keywords,
            "shortSummary": self.shortSummary,
            "longSummary": self.longSummary,
            "organization": self.organization,
            "sentiment": self.sentiment,
        }

    def __repr__(self):
        return f"User(title={self.keywords}, shortSummary={self.shortSummary}, longSummary={self.longSummary})"
