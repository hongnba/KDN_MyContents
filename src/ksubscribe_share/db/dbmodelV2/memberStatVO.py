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


# 개인멤버 통계
class memberStatVO(BaseMongoDocument):

    collectionName = "member_statistics"

    def __init__(
        self,
        yyyymmdd: int = None,
        org_id: str = None,        
        mber_id: str = None,
        mber_type: str = None,
        authority: str = None,
        KeywordViewCount: Dict[str, int] = {},      # {keyword: viewCount}
        PredkeywordViewCount: Dict[str, int] = {},  # {전력: 10}
        OrgViewCont: Dict[str, int] = {},           # {기관id: viewcount}
        ViewContents: Dict[str, int] = {},          # {컨텐츠 id: 본 횟수}
        _id: ObjectId = None,
    ):
        
        super().__init__(_id)  # BaseDocument의 생성자를 호출
        self.mber_id = mber_id
        self.mber_type = mber_type
        self.authority = authority
        self.org_id = org_id

        # 초기화 시 기본값 설정
        self.KeywordViewCount = KeywordViewCount if KeywordViewCount is not None else {}
        self.PredkeywordViewCount = (
            PredkeywordViewCount if PredkeywordViewCount is not None else {}
        )
        self.OrgViewCont = OrgViewCont if OrgViewCont is not None else {}
        #self.RecvContents = RecvContents if RecvContents is not None else {}
        self.ViewContents = ViewContents if ViewContents is not None else {}
        
        
