from bson import ObjectId
from pymongo import MongoClient
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument


class Subscribe(BaseMongoDocument):

    collectionName = "userSubscribe"

    def __init__(
        self, user: str, subscribeInfo: bytearray, len: int, _id: ObjectId = None
    ):

        super().__init__(_id)  # BaseDocument의 생성자를 호출
        self.user = user
        self.subscribeInfo = subscribeInfo
        self.len = len

    @classmethod
    def from_mongo(cls, document):
        """MongoDB 문서를 클래스로 변환"""

        return cls(
            user=document.get("user"),
            subscribeInfo=document.get("subscribeInfo"),
            len=document.get("len"),
            _id=document.get("_id"),
        )

    def to_mongo(self):
        """클래스를 MongoDB 문서 형식으로 변환"""
        return {
            # "_id": self._id,
            "user": self.user,
            "subscribeInfo": self.subscribeInfo,
            "len": self.len,
        }

    @classmethod
    def find_all(cls):
        """지원 안함"""
        list_result = []
        return list_result

    def __repr__(self):
        return f"User(_id={self._id}, user={self.user}, subscribeInfo={self.subscribeInfo}), len={self.len}"
