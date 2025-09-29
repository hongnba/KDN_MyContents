from bson import ObjectId
from pymongo import MongoClient
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument
from ksubscribe_share.db.dbmodel.newsMeta import NewsMeta
from ksubscribe_share.db.dbmodel.newsContents import NewsContents
from ksubscribe_share.db.dbmodel.errorInfo import ErrorInfo
from ksubscribe_share.db.dbmodel.orgCagegory import OrgCagegory
import datetime
from typing import List


class UserSubMaster(BaseMongoDocument):

    collectionName = "userSubMaster"

    def __init__(
        self,
        mber_id: str,
        subGroupIdList: List[str] = None,
        orgList: List[OrgCagegory] = None,
        predKeywordList: List[str] = None,
        editDt: str = None,
        _id: ObjectId = None,
    ):

        super().__init__(_id)  # BaseDocument의 생성자를 호출
        self.mber_id = mber_id
        # self.description = description
        self.subGroupIdList = subGroupIdList if subGroupIdList is not None else []
        self.orgList = orgList if orgList is not None else []
        self.predKeywordList = predKeywordList if predKeywordList is not None else []
        self.editDt = editDt

    @classmethod
    def from_mongo(cls, document):
        """MongoDB 문서를 클래스로 변환"""

        return cls(
            _id=document.get("_id"),
            mber_id=document.get("mber_id"),
            subGroupIdList=document.get("subGroupIdList", []),
            orgList=document.get("orgList", []),
            predKeywordList=document.get("predKeywordList", []),
            editDt=document.get("editDt"),
        )

    def to_mongo(self):
        """클래스를 MongoDB 문서 형식으로 변환"""
        return {
            # "_id": self._id,
            "mber_id": self.mber_id,
            # "description": self.description,
            "subGroupIdList": self.subGroupIdList,
            "orgList": self.orgList,
            "predKeywordList": self.predKeywordList,
            "editDt": self.editDt,
        }

    @classmethod
    def find_all(cls):
        """지원 안함"""
        list_result = []
        return list_result

    def __repr__(self):
        return f"User(_id={self._id}, mber_id={self.mber_id}, subGroupIdList={self.subGroupIdList}, orgIdList={self.orgIdList}, predKeywordList={self.predKeywordList}, editDt={self.editDt}"
