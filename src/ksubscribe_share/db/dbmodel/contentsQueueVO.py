from bson import ObjectId
from pymongo import MongoClient

from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument

import datetime


class ContentsQueue(BaseMongoDocument):

    collectionName = "contents_queue"

    def __init__(
        self,
        orgName: str,
        categoryName: str,
        title: str,
        url: str,
        collectionDate: str,
        _id: ObjectId = None,
    ):

        super().__init__(_id)  # BaseDocument의 생성자를 호출
        self.orgName = orgName
        self.categoryName = categoryName
        self.title = title
        self.url = url
        self.collectionDate = collectionDate

    @classmethod
    def from_mongo(cls, document):
        """MongoDB 문서를 클래스로 변환"""

        return cls(
            _id=document.get("_id"),
            orgName=document.get("ORG_NM"),
            categoryName=document.get("CATE_NM"),
            title=document.get("TITLE"),
            url=document.get("URL"),
            collectionDate=document.get("COL_DT"),
        )

    def to_mongo(self):
        """클래스를 MongoDB 문서 형식으로 변환"""
        return {
            # "_id": self._id,
            "ORG_NM": self.orgName,
            "CATE_NM": self.categoryName,
            "TITLE": self.title,
            "URL": self.url,
            "COL_DT": self.collectionDate,
        }

    def __repr__(self):
        return f"User(_id={self._id}, orgName={self.orgName}, categoryName={self.categoryName}, title={self.title}, url={self.url}, collectionDate={self.collectionDate})"
