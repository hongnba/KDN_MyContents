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


# 사전정의된 키워드 목록
class PredefineKeywordRelationVO(BaseMongoDocument):

    collectionName = "predefine_keyword_relation"

    def __init__(
        self, 
        keyword1 : str = None,
        keyword2 : str  = None,
        count : int  = None,
        type : int = None,     #Subscribe : 0, Unsubscribe : 1
        _id: ObjectId = None
    ):

        super().__init__(_id)  # BaseDocument의 생성자를 호출
        self.keyword1 = keyword1
        self.keyword2 = keyword2
        self.count = count
        self.type = type
        
        