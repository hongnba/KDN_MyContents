#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from ksubscribe_share.db.mongoManager import MongoManager
from datetime import datetime, timedelta
import pytz

mongoManager = MongoManager()
collection = mongoManager.getCollection("daily_stats")

kst = pytz.timezone('Asia/Seoul')
target_date = kst.localize(datetime(2025, 12, 30, 0, 0, 0))

# 날짜만 추출
target_date_only = target_date.date()

# UTC 날짜 기준으로 범위 생성
target_date_start_utc = pytz.utc.localize(datetime.combine(target_date_only, datetime.min.time()))
target_date_end_utc = target_date_start_utc + timedelta(days=1)

print(f"조회 날짜 (KST): {target_date.strftime('%Y-%m-%d')}")
print(f"UTC 범위: {target_date_start_utc} ~ {target_date_end_utc}")

# 실제 daily_stats 문서 확인
docs = list(collection.find({"orgId": "A0010"}).sort("last_calculate_date", -1).limit(5))

print(f"\n총 {len(docs)}개의 daily_stats 문서 확인")
for i, doc in enumerate(docs, 1):
    last_calc = doc.get('last_calculate_date')
    if last_calc:
        last_calc_kst = last_calc.astimezone(kst) if last_calc.tzinfo else last_calc
        print(f"\n문서 {i}:")
        print(f"  last_calculate_date (UTC): {last_calc}")
        print(f"  last_calculate_date (KST): {last_calc_kst}")
        print(f"  날짜만 (KST): {last_calc_kst.strftime('%Y-%m-%d')}")
        
        # 쿼리 범위에 포함되는지 확인
        if target_date_start_utc <= last_calc < target_date_end_utc:
            print("  >>> 쿼리 범위에 포함됩니다!")

# 쿼리 실행
query = {
    "orgId": "A0010",
    "last_calculate_date": {
        "$gte": target_date_start_utc,
        "$lt": target_date_end_utc
    }
}

print(f"\n쿼리: {query}")
result = collection.find_one(query, sort=[("last_calculate_date", -1)])

if result:
    print(f"\n>>> 문서를 찾았습니다!")
    print(f"last_calculate_date (UTC): {result.get('last_calculate_date')}")
else:
    print(f"\n>>> 문서를 찾지 못했습니다.")


