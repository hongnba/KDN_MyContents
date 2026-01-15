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
from datetime import datetime

class ContentsCollectErrorVO(BaseMongoDocument):

    collectionName = "contents_collect_error"

    def __init__(
        self,
        collectDt : datetime = None,  #수집일 
        orgId : str =None,            #구독기관ID 
        cateId : str =None,           #카테고리ID 
        regDt: datetime=None,         #
        regId: str =None,             #
        editDt: datetime=None,         #
        editId: str =None,             #
        errorInfo: str = None,
        _id: ObjectId = None,   
    ):

        super().__init__(_id)  # BaseDocument의 생성자를 호출
        self.collectDt = collectDt
        self.orgId = orgId
        self.cateId = cateId
        self.regDt = regDt
        self.regId = regId
        self.editDt = editDt
        self.editId = editId
        self.errorInfo = errorInfo





