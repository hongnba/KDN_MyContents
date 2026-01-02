#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from ksubscribe_share.db.mongoManager import MongoManager
from datetime import datetime, timedelta
import pytz

mongoManager = MongoManager()
collection = mongoManager.getCollection("weekly_stats")

kst = pytz.timezone('Asia/Seoul')

# 2025-12-30 KST의 시작과 끝 시간
target_date_kst = kst.localize(datetime(2025, 12, 30, 0, 0, 0))
target_date_start_kst = target_date_kst.replace(hour=0, minute=0, second=0, microsecond=0)
target_date_end_kst = target_date_start_kst + timedelta(days=1)

# UTC로 변환 (MongoDB는 UTC로 저장)
target_date_start_utc = target_date_start_kst.astimezone(pytz.utc)
target_date_end_utc = target_date_end_kst.astimezone(pytz.utc)

print(f"KST 기준 2025-12-30 범위:")
print(f"  시작: {target_date_start_kst}")
print(f"  종료: {target_date_end_kst}")
print(f"\nUTC 기준 범위 (쿼리용):")
print(f"  시작: {target_date_start_utc}")
print(f"  종료: {target_date_end_utc}")

# 쿼리 실행
query = {
    "orgId": "A0010",
    "end_date": {
        "$gte": target_date_start_utc,
        "$lt": target_date_end_utc
    }
}

print(f"\n쿼리: {query}")
document = collection.find_one(query, sort=[("last_calculate_date", -1)])

if document:
    print(f"\n>>> 문서를 찾았습니다!")
    end_date_utc = document.get('end_date')
    if end_date_utc:
        end_date_kst = end_date_utc.astimezone(kst) if end_date_utc.tzinfo else end_date_utc
        print(f"end_date (UTC): {end_date_utc}")
        print(f"end_date (KST): {end_date_kst}")
else:
    print(f"\n>>> 문서를 찾지 못했습니다.")
    # 모든 문서 확인
    docs = list(collection.find({"orgId": "A0010"}).sort("last_calculate_date", -1).limit(3))
    print(f"\n가장 최근 3개 문서:")
    for i, doc in enumerate(docs, 1):
        end_date_utc = doc.get('end_date')
        if end_date_utc:
            end_date_kst = end_date_utc.astimezone(kst) if end_date_utc.tzinfo else end_date_utc
            print(f"\n문서 {i}:")
            print(f"  end_date (UTC): {end_date_utc}")
            print(f"  end_date (KST): {end_date_kst}")


