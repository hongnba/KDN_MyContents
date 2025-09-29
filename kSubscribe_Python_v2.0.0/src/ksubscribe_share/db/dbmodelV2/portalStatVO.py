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

# 포털 통계
# 용어 정리, mber_org_id : 내 기관 ID (commCode COM00A를 따름), sub_org_id : 구독 기관 ID (commCode COM00P를 따르도록 추가)
class portalStatVO(BaseMongoDocument):

    collectionName = "portal_statistics"

    def __init__(
        self,
        yyyymmdd:int = None,   # Date_YYMMDDHH
        
        PredkeywordSubscribeCount:  Dict[str, int] = None,           # 사전정의된 키워드 가입 순위, Date_YYMMDDHH, predkeyword, 가입자수
        PredkeywordSubscribeCount_male: Dict[str, int] = None,       # 사전정의된 키워드 가입 순위, Date_YYMMDDHH, predkeyword, 가입자수
        PredkeywordSubscribeCount_female:  Dict[str, int] = None,    # 사전정의된 키워드 가입 순위, Date_YYMMDDHH, predkeyword, 가입자수
        KeywordViewCount: Dict[str, int] = None,                     # 키워드 순위, Date_YYMMDDHH, keyword, viewCount
        PredkeywordViewCount: Dict[str, int] = None,                 # 사전정의된 키워드 순위, Date_YYMMDDHH, predkeyword, viewCount
        OrgSubscribeCont: Dict[str, int] = None,                     # 구독기관 카운드, Date_YYMMDDHH, 구독기관id, 가입자수
        UserSubscribeCont: List[int, int, int] = None,              # 가입자 카운드, Date_YYMMDDHH, 가입자수, 여성가입자수, 남성가입자수
        UserAgeSubscribeCont: Dict[int, int] = None,                 # 가입자 카운드, Date_YYMMDDHH, 연령대별 가입가수, Key: 10,20,30,...
        ContentsViewCount: Dict[str, int] = None,                    # 컨텐츠 조회수, Date_YYMMDDHH, 뷰 컨텐츠 id, 조회수
        ContentsCollection: Dict[str, int] = None,                   # 오늘 수집컨텐츠, Date_YYMMDDHH, sub_org_id, 수집개수
        _id: ObjectId = None,
    ):

        super().__init__(_id)  # BaseDocument의 생성자를 호출
        self.PredkeywordSubscribeCount = (
            PredkeywordSubscribeCount if PredkeywordSubscribeCount is not None else {}
        )
        self.PredkeywordSubscribeCount_male = (
            PredkeywordSubscribeCount_male
            if PredkeywordSubscribeCount_male is not None
            else {}
        )
        self.PredkeywordSubscribeCount_female = (
            PredkeywordSubscribeCount_female
            if PredkeywordSubscribeCount_female is not None
            else {}
        )
        self.KeywordViewCount = KeywordViewCount if KeywordViewCount is not None else {}
        self.PredkeywordViewCount = (
            PredkeywordViewCount if PredkeywordViewCount is not None else {}
        )
        self.OrgSubscribeCont = OrgSubscribeCont if OrgSubscribeCont is not None else {}
        self.UserSubscribeCont = (
            UserSubscribeCont if UserSubscribeCont is not None else {}
        )
        self.UserAgeSubscribeCont = (
            UserAgeSubscribeCont if UserAgeSubscribeCont is not None else {}
        )
        self.ContentsViewCount = (
            ContentsViewCount if ContentsViewCount is not None else {}
        )
        self.ContentsCollection = (
            ContentsCollection if ContentsCollection is not None else {}
        )
