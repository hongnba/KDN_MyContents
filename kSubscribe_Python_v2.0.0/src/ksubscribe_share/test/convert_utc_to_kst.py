#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
import pytz

utc = pytz.utc
kst = pytz.timezone("Asia/Seoul")

# UTC 시간
utc_time1 = utc.localize(datetime(2025, 12, 23, 15, 0, 0))
utc_time2 = utc.localize(datetime(2025, 12, 31, 14, 59, 59, 999000))

# KST로 변환
kst_time1 = utc_time1.astimezone(kst)
kst_time2 = utc_time2.astimezone(kst)

print("UTC 시간 1: 2025-12-23T15:00:00Z")
print(f"KST 시간 1: {kst_time1}")
print(f"KST 시간 1 (ISO 형식): {kst_time1.isoformat()}")
print()

print("UTC 시간 2: 2025-12-31T14:59:59.999Z")
print(f"KST 시간 2: {kst_time2}")
print(f"KST 시간 2 (ISO 형식): {kst_time2.isoformat()}")
print()

print("기간:")
print(f"  시작: {kst_time1.strftime('%Y-%m-%d %H:%M:%S')} (KST)")
print(f"  종료: {kst_time2.strftime('%Y-%m-%d %H:%M:%S')} (KST)")
print()

print("날짜만:")
print(f"  시작 날짜: {kst_time1.strftime('%Y-%m-%d')} (KST)")
print(f"  종료 날짜: {kst_time2.strftime('%Y-%m-%d')} (KST)")


