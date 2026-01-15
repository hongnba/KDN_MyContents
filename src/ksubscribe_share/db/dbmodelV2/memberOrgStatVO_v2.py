from bson import ObjectId
from pymongo import MongoClient
import datetime
from typing import List, Dict
from typing import Tuple

from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodel.newsMeta import NewsMeta
from ksubscribe_share.db.dbmodel.newsContents import NewsContents
from ksubscribe_share.db.dbmodelV2.errorInfo import ErrorInfo
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO
from typing import TypeVar, Type, Dict
T = TypeVar("T", bound="BaseModel")  # BaseModel에 바인딩된 타입 변수


# 기관멤버 통계
# 용어 정리, mber_org_id : 내 기관 ID (commCode COM00A를 따름), sub_org_id : 구독 기관 ID (commCode COM00P를 따르도록 추가)
class MemberOrgStatVO(BaseMongoDocument):

    collectionName = "member_organization_statistics"

    def __init__(
        self,
        mber_org_id: str = None,
        yyyymmdd: int = None,
        OrgSubscribeCount: Dict[str, int] = None,  # 기관: 구독수
        PredKeywordCount: Dict[str, int] = None,  # 키워드: 구독수
        _id: ObjectId = None,
    ):
        super().__init__(_id)
        self.mber_org_id = mber_org_id
        self.yyyymmdd = yyyymmdd
        self.OrgSubscribeCount = OrgSubscribeCount
        self.PredKeywordCount = PredKeywordCount


    @classmethod
    def from_mongo(cls, document):
        """MongoDB 문서를 클래스로 변환"""
        return cls(
            _id=document.get("_id"),
            mber_org_id=document.get("mber_org_id"),
            yyyymmdd=document.get("yyyymmdd"),
            OrgSubscribeCount=document.get("OrgSubscribeCount", {}),
            PredKeywordCount=document.get("PredKeywordCount", {}),
        )
        
    def to_mongo(self):
        """클래스를 MongoDB 문서 형식으로 변환"""
        return {
            "_id": self._id,
            "mber_org_id": self.mber_org_id,
            "yyyymmdd": self.yyyymmdd,
            "OrgSubscribeCount": self.OrgSubscribeCount,
            "PredKeywordCount": self.PredKeywordCount,
        }

    @classmethod
    def find_all(cls):
        """지원 안함"""
        return []