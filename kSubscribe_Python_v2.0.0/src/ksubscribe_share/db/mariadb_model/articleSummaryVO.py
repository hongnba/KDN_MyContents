from datetime import datetime
from typing import Optional

class ArticlesSummaryVO:
    collectionName = "articles_summary"

    def __init__(
        self,
        orgId: str = "",
        long_summary: str = "",
        short_summary: str = "",
        success: Optional[bool] = None,
        url: str = "",
        created_at: Optional[datetime] = None
    ):
        self.orgId = orgId
        self.long_summary = long_summary
        self.short_summary = short_summary
        self.success = success
        self.url = url
        self.created_at = created_at or datetime.now()

    def to_dict(self):
        """Convert to dict for service insertion"""
        return {
            "orgId": self.orgId,
            "long_summary": self.long_summary,
            "short_summary": self.short_summary,
            "success": self.success,
            "url": self.url,
            "created_at": self.created_at
        }