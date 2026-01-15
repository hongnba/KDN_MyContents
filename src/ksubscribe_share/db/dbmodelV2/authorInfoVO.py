from bson import ObjectId
from pymongo import MongoClient
import datetime
from typing import List
from typing import Tuple

from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodel.newsMeta import NewsMeta
from ksubscribe_share.db.dbmodel.newsContents import NewsContents
from ksubscribe_share.db.dbmodelV2.errorInfo import ErrorInfo
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO
from typing import TypeVar, Type, Dict
T = TypeVar("T", bound="BaseModel")  # BaseModel에 바인딩된 타입 변수


class AuthorInfoVO(BaseMongoDocument):

    collectionName = "auth_info"

    def __init__(
        self,
        authorCode: str = None,
        authorName: str =None,
        authorDesc: str =None,
        authorCreate: str =None,
        _id: ObjectId = None
    ):

        super().__init__(_id)  # BaseDocument의 생성자를 호출

        # 필드 초기화
        self.authorCode = authorCode
        self.authorName = authorName
        self.authorDesc = authorDesc
        self.authorCreate = authorCreate
        



