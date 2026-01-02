#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from ksubscribe_share.db.mongoManager import MongoManager
from datetime import datetime, timedelta
from bson import ObjectId
import pytz

mongoManager = MongoManager()
collection = mongoManager.getCollection("weekly_stats")

# 특정 oid 문서 확인
target_oid = "6954d5e4b517fd14744ef57d"
doc = collection.find_one({"_id": ObjectId(target_oid)})

if doc:
    print(f"=== OID {target_oid} 문서 정보 ===")
    print(f"orgId: {doc.get('orgId')}")
    print(f"start_date (UTC): {doc.get('start_date')}")
    print(f"end_date (UTC): {doc.get('end_date')}")
    print(f"last_calculate_date (UTC): {doc.get('last_calculate_date')}")
    
    kst = pytz.timezone('Asia/Seoul')
    if doc.get('start_date'):
        start_date_kst = doc.get('start_date').astimezone(kst)
        print(f"start_date (KST): {start_date_kst}")
    if doc.get('end_date'):
        end_date_kst = doc.get('end_date').astimezone(kst)
        print(f"end_date (KST): {end_date_kst}")
        print(f"end_date 날짜만 (KST): {end_date_kst.strftime('%Y-%m-%d')}")
else:
    print(f"OID {target_oid} 문서를 찾을 수 없습니다.")
    exit(1)

print("\n" + "="*50)
print("현재 쿼리 로직 테스트")
print("="*50)

# 현재 쿼리 로직 (2025-12-30 기준으로 조회)
kst = pytz.timezone('Asia/Seoul')
target_date = kst.localize(datetime(2025, 12, 30, 0, 0, 0))
target_date_only = target_date.date()

# UTC 날짜 기준으로 범위 생성
target_date_start_utc = pytz.utc.localize(datetime.combine(target_date_only, datetime.min.time()))
target_date_end_utc = target_date_start_utc + timedelta(days=1)

print(f"\n조회 기준 날짜: 2025-12-30 (KST)")
print(f"UTC 범위: {target_date_start_utc} ~ {target_date_end_utc}")

query = {
    "orgId": "A0010",
    "end_date": {
        "$gte": target_date_start_utc,
        "$lt": target_date_end_utc
    }
}

print(f"\n쿼리: {query}")

result = collection.find_one(query, sort=[("last_calculate_date", -1)])

if result:
    result_oid = str(result.get('_id'))
    print(f"\n>>> 조회된 문서 OID: {result_oid}")
    if result_oid == target_oid:
        print(">>> ✅ 올바른 문서가 조회되었습니다!")
    else:
        print(f">>> ❌ 다른 문서가 조회되었습니다. (예상: {target_oid})")
        print(f"조회된 문서의 end_date (UTC): {result.get('end_date')}")
        if result.get('end_date'):
            print(f"조회된 문서의 end_date (KST): {result.get('end_date').astimezone(kst)}")
else:
    print(f"\n>>> ❌ 문서를 찾지 못했습니다.")

print("\n" + "="*50)
print("대안: end_date가 2025-12-30 날짜 범위에 포함되는지 확인")
print("="*50)

# end_date가 2025-12-30 날짜에 포함되는지 확인
if doc.get('end_date'):
    end_date_utc = doc.get('end_date')
    if target_date_start_utc <= end_date_utc < target_date_end_utc:
        print(f">>> ✅ end_date가 쿼리 범위에 포함됩니다!")
    else:
        print(f">>> ❌ end_date가 쿼리 범위에 포함되지 않습니다.")
        print(f"end_date (UTC): {end_date_utc}")
        print(f"쿼리 범위: {target_date_start_utc} ~ {target_date_end_utc}")


