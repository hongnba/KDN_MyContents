from __future__ import annotations  # Forward Reference 사용을 위한 선언

from bson import ObjectId
from pymongo import MongoClient
import datetime
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.contentsCollectHistoryVO import ContentsCollectDetail
from typing import TypeVar, Type, Dict
T = TypeVar("T", bound="BaseModel")  # BaseModel에 바인딩된 타입 변수


class OriginalContentsVO(BaseMongoDocument):

    collectionName = "original_contents"
    


    def __init__(
        self,
        contentOrgId: str = None,
        cateId: str = None,
        title: str = None,
        contents: str = None,
        url: str = None,
        pubDt: datetime = None,
        collectDt: datetime = None, 
        succeeded: bool = None,
        _id: ObjectId = None,
    ):

        super().__init__(_id)  # BaseDocument의 생성자를 호출
        self.contentOrgId = contentOrgId
        self.cateId = cateId
        self.title = title
        self.contents = contents
        self.url = url
        self.pubDt = pubDt
        self.collectDt = collectDt
        self.succeeded = succeeded

      def to_mongo(self):
        """Convert object to dict for MongoDB insertion."""
        return {
            "_id": self._id or ObjectId(),
            "contentOrgId": self.contentOrgId or "",
            "cateId": self.cateId or "",
            "title": self.title or "",
            "contents": self.contents or "",
            "url": self.url or "",
            "pubDt": self.pubDt or None,
            "collectDt": self.collectDt or datetime.utcnow(),
            "succeeded": self.succeeded if self.succeeded is not None else False,
        }