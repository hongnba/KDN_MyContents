#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from ksubscribe_share.db.mongoManager import MongoManager
from datetime import datetime, timedelta
import pytz

mongoManager = MongoManager()
collection = mongoManager.getCollection("contents")

kst = pytz.timezone('Asia/Seoul')

# 테스트: 2025-12-24 ~ 2025-12-30 (KST 기준 날짜)
start_date_kst = kst.localize(datetime(2025, 12, 24, 0, 0, 0))
end_date_kst = kst.localize(datetime(2025, 12, 30, 0, 0, 0))

# 날짜만 추출
start_date_only = start_date_kst.date()
end_date_only = end_date_kst.date()

# UTC 날짜 기준으로 범위 생성
start_date_utc = pytz.utc.localize(datetime.combine(start_date_only, datetime.min.time()))
end_date_utc = pytz.utc.localize(datetime.combine(end_date_only, datetime.min.time())) + timedelta(days=1)

print("입력 날짜 (KST):")
print(f"  시작: {start_date_kst.strftime('%Y-%m-%d')}")
print(f"  종료: {end_date_kst.strftime('%Y-%m-%d')} (미포함)")

print(f"\n변환된 날짜 (UTC):")
print(f"  시작: {start_date_utc}")
print(f"  종료: {end_date_utc} (미포함)")

# 수정된 쿼리
query = {
    "contentsOrgId": "A0010",
    "pubDt": {
        "$gte": start_date_utc,
        "$lt": end_date_utc
    },
    "metaSucYN": "Y"
}

print(f"\n쿼리: {query}")

count = collection.count_documents(query)
print(f"\n>>> 조회된 문서 수: {count}개")

# 날짜별로 그룹화해서 확인
print("\n" + "="*50)
print("날짜별 문서 수 (KST 기준)")
print("="*50)
pipeline = [
    {
        "$match": query
    },
    {
        "$project": {
            "pubDt": 1,
            "pubDt_kst": {
                "$dateToString": {
                    "format": "%Y-%m-%d",
                    "date": "$pubDt",
                    "timezone": "Asia/Seoul"
                }
            }
        }
    },
    {
        "$group": {
            "_id": "$pubDt_kst",
            "count": {"$sum": 1}
        }
    },
    {
        "$sort": {"_id": 1}
    }
]

date_counts = list(collection.aggregate(pipeline))
for item in date_counts:
    print(f"  {item['_id']}: {item['count']}개")


