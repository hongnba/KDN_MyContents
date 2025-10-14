import json
from datetime import datetime
from typing import Optional, List, Any


class ArticleSentimentVO:
    collectionName = "ARTICLE_SENTIMENT"

    def __init__(
        self,
        orgId: str = "",
        url: str = "",
        positive_ratio: Optional[float] = None,
        positive_reason: str = "",
        negative_ratio: Optional[float] = None,
        negative_reason: str = "",
        neutral_ratio: Optional[float] = None,
        positive_keywords: Optional[List[str]] = None,
        negative_keywords: Optional[List[str]] = None,
        success: Optional[bool] = None,
        created_at: Optional[datetime] = None,
    ):
        self.orgId = orgId
        self.url = url
        self.positive_ratio = positive_ratio
        self.positive_reason = positive_reason
        self.negative_ratio = negative_ratio
        self.negative_reason = negative_reason
        self.neutral_ratio = neutral_ratio
        self.positive_keywords = positive_keywords or []
        self.negative_keywords = negative_keywords or []
        self.success = success
        self.created_at = created_at or datetime.now()

    def to_dict(self):
        """Convert VO into dict for DB insertion"""
        return {
            "orgId": self.orgId,
            "url": self.url,
            "positive_ratio": self.positive_ratio,
            "positive_reason": self.positive_reason,
            "negative_ratio": self.negative_ratio,
            "negative_reason": self.negative_reason,
            "neutral_ratio": self.neutral_ratio,
            "positive_keywords": json.dumps(self.positive_keywords),
            "negative_keywords": json.dumps(self.negative_keywords),
            "success": self.success,
            "created_at": self.created_at,
        }