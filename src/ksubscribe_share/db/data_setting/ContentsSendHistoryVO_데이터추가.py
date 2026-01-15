from ksubscribe_share.db.dbmodelV2.contentsSendHistoryVO import (
    contentsSendHistoryVO,
    sendContentDetail,
)
from ksubscribe_share.db.mongoManager import MongoClient, MongoManager

# 1. 기관 데이터 가져오기
import mariadb
from itertools import groupby

coll = MongoManager().getCollection("contents_send_history")
coll.delete_many({})

conn = mariadb.connect(
    user="3way", password="3waysoft", host="192.168.1.200", port=3306, database="cds"
)
cursor = conn.cursor()

cursor.execute("select * from csa_send_history")
result = cursor.fetchall()
docs = []

# group_key 기준으로 정렬
result.sort(key=lambda x: x.mberId)

# groupby로 그룹핑
grouped_dict = {
    key: list(group) for key, group in groupby(result, key=lambda x: x[0])
}

# key로 반복문
for key in grouped_dict:
    send_history = contentsSendHistoryVO(
        mberId=key,
        sendContentIds=[]
    )
    
    # 실제 DB 에 데이터가 없어서 디버깅 해봐야 함.
    for item in grouped_dict[key]:
        send_history.sendContentIds.append(sendContentDetail(sendDt=item[6], contentId=item[1]))
        
    send_history.insert_one()

conn.close()