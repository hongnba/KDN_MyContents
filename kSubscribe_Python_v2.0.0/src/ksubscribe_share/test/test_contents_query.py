#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from ksubscribe_share.db.mongoManager import MongoManager
from datetime import datetime, timedelta
import pytz

mongoManager = MongoManager()
collection = mongoManager.getCollection("contents")

kst = pytz.timezone('Asia/Seoul')

# 테스트: 2025-12-24 ~ 2025-12-30 (KST 기준)
start_date_kst = kst.localize(datetime(2025, 12, 24, 0, 0, 0))
end_date_kst = kst.localize(datetime(2025, 12, 30, 23, 59, 59, 999000))

# UTC로 변환
start_date_utc = start_date_kst.astimezone(pytz.utc)
end_date_utc = end_date_kst.astimezone(pytz.utc)

print("입력 날짜 (KST):")
print(f"  시작: {start_date_kst}")
print(f"  종료: {end_date_kst}")
print(f"\n변환된 날짜 (UTC):")
print(f"  시작: {start_date_utc}")
print(f"  종료: {end_date_utc}")

# 실제 contents 문서의 pubDt 확인
print("\n" + "="*50)
print("실제 contents 문서의 pubDt 확인 (샘플 5개)")
print("="*50)

sample_docs = list(collection.find({
    "contentsOrgId": "A0010",
    "pubDt": {
        "$gte": start_date_utc,
        "$lt": end_date_utc + timedelta(days=1)  # 하루 더 넓게
    },
    "metaSucYN": "Y"
}).limit(5))

print(f"총 {len(sample_docs)}개 문서 확인")
for i, doc in enumerate(sample_docs, 1):
    pub_dt = doc.get('pubDt')
    if pub_dt:
        pub_dt_kst = pub_dt.astimezone(kst) if pub_dt.tzinfo else pub_dt
        print(f"\n문서 {i}:")
        print(f"  pubDt (UTC): {pub_dt}")
        print(f"  pubDt (KST): {pub_dt_kst}")
        print(f"  pubDt 날짜만 (KST): {pub_dt_kst.strftime('%Y-%m-%d')}")

# 현재 쿼리로 조회
print("\n" + "="*50)
print("현재 쿼리로 조회")
print("="*50)
query = {
    "contentsOrgId": "A0010",
    "pubDt": {
        "$gte": start_date_utc,
        "$lt": end_date_utc + timedelta(days=1)  # end_date는 미포함이므로 하루 더
    },
    "metaSucYN": "Y"
}
print(f"쿼리 범위 (UTC):")
print(f"  $gte: {start_date_utc}")
print(f"  $lt: {end_date_utc + timedelta(days=1)}")

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


