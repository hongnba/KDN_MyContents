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


class CommCodeVO(BaseMongoDocument):

    collectionName = "common_code"

    def __init__(
        self,
        codeId: str = None,
        code: str =None,
        codeName: str =None,
        codeDc: str =None,
        codeDesc: str =None,
        useYN: str =None,
        imgPath: str =None,
        regDt: datetime = None,
        regId: str =None,
        editDt: datetime = None,
        editId: str =None,
        imageSource: bytearray = None,
        domain: str =None,
        _id: ObjectId = None,
    ):

        super().__init__(_id)  # BaseDocument의 생성자를 호출

        # 필드 초기화
        self.codeId = codeId
        self.code = code
        self.codeName = codeName
        self.codeDc = codeDc
        self.codeDesc = codeDesc
        self.useYN = useYN
        self.imgPath = imgPath
        self.regDt = regDt
        self.regId = regId
        self.editDt = editDt
        self.editId = editId
        self.imageSource = imageSource
        self.domain = domain



