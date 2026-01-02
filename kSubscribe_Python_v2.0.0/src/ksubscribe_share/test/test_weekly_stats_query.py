#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from ksubscribe_share.db.mongoManager import MongoManager
from datetime import datetime, timedelta
from bson import ObjectId
import pytz

mongoManager = MongoManager()
collection = mongoManager.getCollection("weekly_stats")

kst = pytz.timezone('Asia/Seoul')
target_oid = "6954d5e4b517fd14744ef57d"

# 기간: 2025-12-24 ~ 2025-12-30 (KST)
start_date_kst = kst.localize(datetime(2025, 12, 24, 0, 0, 0))
end_date_kst = kst.localize(datetime(2025, 12, 30, 23, 59, 59, 999000))

# UTC로 변환
start_date_utc = start_date_kst.astimezone(pytz.utc)
end_date_utc = end_date_kst.astimezone(pytz.utc)

print("조회 기간 (KST):")
print(f"  시작: {start_date_kst}")
print(f"  종료: {end_date_kst}")
print(f"\n조회 기간 (UTC):")
print(f"  시작: {start_date_utc}")
print(f"  종료: {end_date_utc}")

# 방법 1: end_date가 기간에 포함되는 경우
print("\n" + "="*50)
print("방법 1: end_date가 기간에 포함되는 경우")
print("="*50)
query1 = {
    "orgId": "A0010",
    "end_date": {
        "$gte": start_date_utc,
        "$lte": end_date_utc
    }
}
print(f"쿼리: {query1}")
result1 = collection.find_one(query1, sort=[("last_calculate_date", -1)])
if result1:
    result_oid = str(result1.get('_id'))
    print(f">>> 조회된 문서 OID: {result_oid}")
    if result_oid == target_oid:
        print(">>> ✅ 올바른 문서가 조회되었습니다!")
    else:
        print(f">>> ❌ 다른 문서가 조회되었습니다.")
else:
    print(">>> ❌ 문서를 찾지 못했습니다.")

# 방법 2: 기간이 weekly_stats의 start_date와 end_date 범위에 포함되는 경우
print("\n" + "="*50)
print("방법 2: 기간이 weekly_stats 범위에 포함되는 경우")
print("="*50)
query2 = {
    "orgId": "A0010",
    "start_date": {"$lte": end_date_utc},
    "end_date": {"$gte": start_date_utc}
}
print(f"쿼리: {query2}")
result2 = collection.find_one(query2, sort=[("last_calculate_date", -1)])
if result2:
    result_oid = str(result2.get('_id'))
    print(f">>> 조회된 문서 OID: {result_oid}")
    if result_oid == target_oid:
        print(">>> ✅ 올바른 문서가 조회되었습니다!")
    else:
        print(f">>> ❌ 다른 문서가 조회되었습니다.")
else:
    print(">>> ❌ 문서를 찾지 못했습니다.")

# 방법 3: end_date의 날짜만 비교 (현재 사용 중인 방법)
print("\n" + "="*50)
print("방법 3: end_date의 날짜만 비교 (현재 방법)")
print("="*50)
end_date_only = end_date_kst.date()
end_date_start_utc = pytz.utc.localize(datetime.combine(end_date_only, datetime.min.time()))
end_date_end_utc = end_date_start_utc + timedelta(days=1)
query3 = {
    "orgId": "A0010",
    "end_date": {
        "$gte": end_date_start_utc,
        "$lt": end_date_end_utc
    }
}
print(f"쿼리: {query3}")
print(f"UTC 범위: {end_date_start_utc} ~ {end_date_end_utc}")
result3 = collection.find_one(query3, sort=[("last_calculate_date", -1)])
if result3:
    result_oid = str(result3.get('_id'))
    print(f">>> 조회된 문서 OID: {result_oid}")
    if result_oid == target_oid:
        print(">>> ✅ 올바른 문서가 조회되었습니다!")
    else:
        print(f">>> ❌ 다른 문서가 조회되었습니다.")
else:
    print(">>> ❌ 문서를 찾지 못했습니다.")


