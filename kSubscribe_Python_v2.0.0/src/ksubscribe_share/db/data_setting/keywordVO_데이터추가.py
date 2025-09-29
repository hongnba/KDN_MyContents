from ksubscribe_share.db.dbmodelV2.contentsOrgVO import (
    ContentsOrgVO,
    ContentsOrgCategory,
)
from ksubscribe_share.db.dbmodelV2.predefineKeywordVO import PredefinedKeywordVO
from ksubscribe_share.db.mongoManager import MongoClient, MongoManager

# 1. 기관 데이터 가져오기
import mariadb
import datetime

coll = MongoManager().getCollection("keywords")

# conn = mariadb.connect(
#     user="3way", password="3waysoft", host="192.168.1.200", port=3306, database="cds"
# )
# cursor = conn.cursor()

keywords = [
    "인공지능",
    "전력",
    "전기",
    "플랫폼",
    "데이터",
    "디지털",
    "정보보호",
    "에너지",
    "에너지",
]
for key in keywords:
    doc = PredefinedKeywordVO(
        name=key,
        editDt=datetime.datetime.now(),
        editId="",
        regDt=datetime.datetime.now(),
        regId="",
    ).insert_one()

# conn.close()
