from bson import ObjectId
from pymongo import MongoClient
import datetime
from typing import List

from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodel.newsMeta import NewsMeta
from ksubscribe_share.db.dbmodel.newsContents import NewsContents
from ksubscribe_share.db.dbmodelV2.errorInfo import ErrorInfo
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO
from typing import TypeVar, Type, Dict
T = TypeVar("T", bound="BaseModel")  # BaseModel에 바인딩된 타입 변수

# 사용자 인증번호 전송
# quotetype : SignIn - 로그인 휴대폰 인증, SingUp-회원가입 휴대폰 인증, OrgSingUp기업회원가입 이메일인증,
class MemberQuoteVO(BaseMongoDocument):

    collectionName = "member_quote"

    def __init__(
        self,
        mberId: str = None,
        quotenum: str = None,
        startDt: datetime = None,
        endDt: datetime = None,
        quotetype: str = None,
        _id: ObjectId = None,
    ):

        super().__init__(_id)  # BaseDocument의 생성자를 호출
        self.mberId = mberId
        self.quotenum = quotenum
        self.startDt = startDt
        self.endDt = endDt
        self.quotetype = quotetype
