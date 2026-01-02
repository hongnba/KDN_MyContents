#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from ksubscribe_share.db.mongoManager import MongoManager
from datetime import datetime
import pytz

mongoManager = MongoManager()
collection = mongoManager.getCollection("weekly_stats")

# A0010 기관의 최근 weekly_stats 문서들 조회
docs = list(collection.find({"orgId": "A0010"}).sort("last_calculate_date", -1).limit(5))

print(f"총 {len(docs)}개의 weekly_stats 문서를 찾았습니다.")
for i, doc in enumerate(docs, 1):
    print(f"\n=== 문서 {i} ===")
    print(f"orgId: {doc.get('orgId')}")
    print(f"start_date: {doc.get('start_date')}")
    print(f"end_date: {doc.get('end_date')}")
    print(f"last_calculate_date: {doc.get('last_calculate_date')}")
    if 'totalPositiveKeywordList' in doc:
        print(f"totalPositiveKeywordList 개수: {len(doc.get('totalPositiveKeywordList', []))}")
    
    # 2025-12-30과 관련된 문서인지 확인
    end_date = doc.get('end_date')
    if end_date:
        kst = pytz.timezone('Asia/Seoul')
        end_date_kst = end_date.astimezone(kst) if end_date.tzinfo else end_date
        print(f"end_date (KST): {end_date_kst}")


