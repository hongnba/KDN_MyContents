from ksubscribe_share.db.dbmodelV2.contentsOrgVO import (
    ContentsOrgVO,
    ContentsOrgCategory,
)
from ksubscribe_share.db.dbmodelV2.commCodeVO import commCodeVO
from ksubscribe_share.db.dbmodelV2.memberOrgStatVO_v2 import MemberOrgStatVO
from ksubscribe_share.db.mongoManager import MongoClient, MongoManager

MemberOrgStatVO(
    mber_org_id="A0001",
    yyyymmdd=20241218,
    OrgSubscribeCount={"과학기술정보통신부": 23, "개인정보보호위원회": 21},
    PredKeywordCount={
        "전력": 54,
        "데이터": 32,
        "인공지능": 27,
    },
).insert_one()
