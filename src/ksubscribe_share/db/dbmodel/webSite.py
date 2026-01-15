from bson import ObjectId
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument
from ksubscribe_share.db.mongoManager import MongoManager


class WebSite(BaseMongoDocument):

    collectionName = "website_v1"

    def __init__(self, tld_url: str, selector: str, _id: ObjectId = None):
        super().__init__(_id)
        self.tld_url = tld_url
        self.selector = selector

    @classmethod
    def from_mongo(cls, document):
        """MongoDB 문서를 클래스로 변환"""

        return cls(
            tld_url=document.get("tld_url"),
            selector=document.get("selector"),
        )

    def to_mongo(self):
        """클래스를 MongoDB 문서 형식으로 변환"""
        return {"tld_url": self.tld_url, "selector": self.selector}

    def __repr__(self):
        return f"User(tld_url={self.tld_url}, selector={self.selector})"
