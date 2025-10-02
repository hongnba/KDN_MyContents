from datetime import datetime
from typing import List, Optional
import json

class ArticleKeywordsVO:
    collectionName = "article_keywords"

    def __init__(
        self,
        orgId: str = "",
        keywords: Optional[List[str]] = None,
        ai_keywords: Optional[List[str]] = None,
        success: Optional[bool] = None,
        url: str = "",
        created_at: Optional[datetime] = None,
    ):
        self.orgId = orgId
        self.keywords = keywords or []
        self.ai_keywords = ai_keywords or []
        self.success = success
        self.url = url
        self.created_at = created_at or datetime.now()

    def to_dict(self):
        """Convert to dict for service insertion"""
        return {
            "orgId": self.orgId,
            "keywords": json.dumps(self.keywords),
            "ai_keywords": json.dumps(self.ai_keywords),
            "success": self.success,
            "url": self.url,
            "created_at": self.created_at,
        }