from datetime import datetime, timedelta
from bson import ObjectId
from ksubscribe_share.db.dbmodel.newsMeta import NewsMeta
from ksubscribe_share.db.mongoManager import MongoManager
from pymongo import MongoClient
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument


class Category(BaseMongoDocument):

    collectionName = "category_v1"
    lastDate_format = "%Y-%m-%d %H:%M:%S"

    def __init__(
        self, name: str, description: str, lastDate: datetime, _id: ObjectId = None
    ):

        super().__init__(_id)  # BaseDocument의 생성자를 호출
        self.name = name
        self.description = description
        self.lastDate = lastDate

    @classmethod
    def from_mongo(cls, document):
        """MongoDB 문서를 클래스로 변환"""

        lastDate_value = document.get("lastDate")
        if lastDate_value == None:
            yesterday = datetime.now() - timedelta(days=1)
            lastDate = yesterday
            # 수정된 lastDate를 저장하는 메서드 호출
            cls.update_lastDate(document["_id"], lastDate)
        else:
            lastDate = (
                lastDate_value  # datetime.strptime(lastDate_value, cls.lastDate_format)
            )

        return cls(
            name=document.get("name"),
            description=document.get("description"),
            lastDate=lastDate,
            _id=document.get("_id"),
        )

    def to_mongo(self):
        """클래스를 MongoDB 문서 형식으로 변환"""

        lastDate_value = self.lastDate.strftime(self.lastDate_format)
        return {
            # "_id": self._id,
            "name": self.name,
            "description": self.description,
        }

    @classmethod
    def update_lastDate(cls, document_id, lastDate):
        collection = cls.mongoManager.getCollection(cls.collectionName)
        collection.update_one(
            {"_id": document_id},
            {"$set": {"lastDate": lastDate}},  # lastDate 필드 업데이트
        )

    def __repr__(self):
        return f"User(_id={self._id}, name={self.name}, lastDate={self.lastDate}, description={self.description})"
