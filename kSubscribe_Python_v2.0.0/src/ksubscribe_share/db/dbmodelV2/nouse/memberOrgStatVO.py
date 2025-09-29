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
        yyyymmdd:int = None,   # Date_YYMMDDHH
        mber_org_id: str = None,
        PredkeywordSubscribeCount: Dict[str, int] = None,           # 사전정의된 키워드 가입 순위, Date_YYMMDDHH, predkeyword, 가입자수
        OrgSubscribeCount: Dict[str, int] = None,                   # 구독기관 카운드, Date_YYMMDDHH, 구독기관id, 가입자수
        KeywordViewCount: Dict[str, int] = None,                    # 키워드 순위, Date_YYMMDDHH, keyword, viewCount
        PredkeywordViewCount: Dict[str, int] = None,                # 사전정의된 키워드 순위, Date_YYMMDDHH, predkeyword, viewCount
        OrgViewCount: Dict[str, int] = None,                        # 임직원이 본 기관 컨텐츠 조회 카운트, Date_YYMMDDHH, 기관id, viewcount
        ContentsViewCount: Dict[str, int]= None,                    # 컨텐츠 조회수, Date_YYMMDDHH, 뷰 컨텐츠 id, 조회수
        OurContentsViewCount: Dict[str, int] = None,                # 우리기업 컨텐츠 조회수, Date_YYMMDD, 뷰 컨텐츠 id, 조회수//우리기업과 관련 컨텐츠는 모두 넣음
        OurContentsReputation: List[float] = None,                  # 우리기업 컨텐츠 평판결과 종합, Date_YYMMDD, 뷰 컨텐츠 id, 평판결과 평귬//우리기업과 관련 컨텐츠는 모두 넣음
        OurContentsReputationDetail: Dict[str, List[float]] = None, # 우리기업 컨텐츠 평판결과 세부, Date_YYMMDD, 뷰 컨텐츠 id, 평판결과 세부//우리기업과 관련 컨텐츠는 모두 넣음
        _id: ObjectId = None,
    ):

        super().__init__(_id)  # BaseDocument의 생성자를 호출
        self.mber_org_id = mber_org_id
        self.PredkeywordSubscribeCount = (
            PredkeywordSubscribeCount if PredkeywordSubscribeCount is not None else {}
        )
        self.KeywordViewCount = KeywordViewCount if KeywordViewCount is not None else {}
        self.PredkeywordViewCount = (
            PredkeywordViewCount if PredkeywordViewCount is not None else {}
        )
        self.OrgSubscribeCont = OrgSubscribeCount if OrgSubscribeCount is not None else {}
        self.OrgViewCont = OrgViewCount if OrgViewCount is not None else {}
        self.ContentsViewCount = (
            ContentsViewCount if ContentsViewCount is not None else {}
        )
        self.OurContentsViewCount = (
            OurContentsViewCount if OurContentsViewCount is not None else {}
        )
        self.OurContentsReputation = (
            OurContentsReputation if OurContentsReputation is not None else {}
        )
        self.OurContentsReputationDetail = (
            OurContentsReputationDetail
            if OurContentsReputationDetail is not None
            else {}
        )
