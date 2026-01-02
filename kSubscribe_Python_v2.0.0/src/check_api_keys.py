#!/usr/bin/env python3
"""
MongoDB에서 나라장터와 네이버 API Key 조회 스크립트
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.append("/home/themiraclesoft/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src")

try:
    from pymongo import MongoClient
    import ksubscribe_share.config as Conf
except ImportError as e:
    print(f"⚠️  모듈 import 실패: {e}")
    sys.exit(1)

def query_api_keys():
    """contents_org 컬렉션에서 나라장터와 네이버 API Key 조회"""
    print("=" * 80)
    print("MongoDB API Key 조회")
    print("=" * 80)
    print(f"연결 정보: {Conf.MONGO_IP}:{Conf.MONGO_PORT}/{Conf.MONGO_DB_NAME}")
    print()
    
    try:
        print("🔌 MongoDB 연결 시도 중...")
        
        # MongoDB 직접 연결
        connect_string = f"mongodb://{Conf.MONGO_IP}:{Conf.MONGO_PORT}/?directConnection=true&serverSelectionTimeoutMS=300000&socketTimeoutMS=300000"
        client = MongoClient(connect_string, tz_aware=True)
        db = client[Conf.MONGO_DB_NAME]
        collection = db["contents_org"]
        
        print(f"✅ MongoDB 연결 성공")
        print()
        
        # 1. 나라장터 (A0004, B0005) 조회
        print("=" * 80)
        print("1. 나라장터 API Key (기관ID: A0004, 카테고리ID: B0005)")
        print("=" * 80)
        
        nara_org = collection.find_one({"orgId": "A0004"})
        if nara_org:
            print(f"기관명: {nara_org.get('orgName', 'N/A')}")
            print(f"기관ID: {nara_org.get('orgId', 'N/A')}")
            print()
            
            if 'categoryList' in nara_org:
                for category in nara_org['categoryList']:
                    if category.get('cateId') == 'B0005':
                        print(f"카테고리명: {category.get('cateName', 'N/A')}")
                        print(f"카테고리ID: {category.get('cateId', 'N/A')}")
                        print(f"수집방법: {category.get('COL_METHOD', 'N/A')}")
                        print()
                        print("API Key 정보:")
                        api_key1 = category.get('APIKEY1', 'N/A')
                        api_key2 = category.get('APIKEY2', 'N/A')
                        
                        # API Key 일부만 표시 (보안)
                        if api_key1 and api_key1 != 'N/A':
                            if len(api_key1) > 20:
                                masked_key1 = api_key1[:10] + "..." + api_key1[-10:]
                            else:
                                masked_key1 = api_key1[:5] + "***"
                            print(f"  APIKEY1 (Service Key): {masked_key1}")
                            print(f"  APIKEY1 (전체): {api_key1}")
                        else:
                            print(f"  APIKEY1: {api_key1}")
                        
                        if api_key2 and api_key2 != 'N/A':
                            if len(api_key2) > 20:
                                masked_key2 = api_key2[:10] + "..." + api_key2[-10:]
                            else:
                                masked_key2 = api_key2[:5] + "***"
                            print(f"  APIKEY2: {masked_key2}")
                            print(f"  APIKEY2 (전체): {api_key2}")
                        else:
                            print(f"  APIKEY2: {api_key2} (나라장터는 사용 안 함)")
                        
                        print()
                        print(f"수집 URL: {category.get('collectUrlInfo', 'N/A')}")
                        break
                else:
                    print("⚠️  카테고리ID B0005를 찾을 수 없습니다.")
            else:
                print("⚠️  categoryList가 없습니다.")
        else:
            print("⚠️  기관ID A0004를 찾을 수 없습니다.")
        
        print()
        print("=" * 80)
        print("2. 네이버 뉴스 API Key (카테고리ID: B0010)")
        print("=" * 80)
        
        # 네이버 뉴스 카테고리를 가진 모든 기관 조회
        naver_orgs = collection.find({"categoryList.cateId": "B0010"})
        naver_found = False
        
        for org in naver_orgs:
            if 'categoryList' in org:
                for category in org['categoryList']:
                    if category.get('cateId') == 'B0010':
                        naver_found = True
                        print(f"기관명: {org.get('orgName', 'N/A')}")
                        print(f"기관ID: {org.get('orgId', 'N/A')}")
                        print(f"카테고리명: {category.get('cateName', 'N/A')}")
                        print(f"카테고리ID: {category.get('cateId', 'N/A')}")
                        print(f"수집방법: {category.get('COL_METHOD', 'N/A')}")
                        print()
                        print("API Key 정보:")
                        api_key1 = category.get('APIKEY1', 'N/A')
                        api_key2 = category.get('APIKEY2', 'N/A')
                        
                        # API Key 일부만 표시 (보안)
                        if api_key1 and api_key1 != 'N/A':
                            if len(api_key1) > 20:
                                masked_key1 = api_key1[:10] + "..." + api_key1[-10:]
                            else:
                                masked_key1 = api_key1[:5] + "***"
                            print(f"  APIKEY1 (Client ID): {masked_key1}")
                            print(f"  APIKEY1 (전체): {api_key1}")
                        else:
                            print(f"  APIKEY1: {api_key1}")
                        
                        if api_key2 and api_key2 != 'N/A':
                            if len(api_key2) > 20:
                                masked_key2 = api_key2[:10] + "..." + api_key2[-10:]
                            else:
                                masked_key2 = api_key2[:5] + "***"
                            print(f"  APIKEY2 (Client Secret): {masked_key2}")
                            print(f"  APIKEY2 (전체): {api_key2}")
                        else:
                            print(f"  APIKEY2: {api_key2}")
                        
                        print()
                        print(f"수집 URL: {category.get('collectUrlInfo', 'N/A')}")
                        print()
                        print("-" * 80)
                        break
        
        if not naver_found:
            print("⚠️  카테고리ID B0010를 찾을 수 없습니다.")
        
        print()
        print("=" * 80)
        print("3. 모든 Open API 카테고리 요약 (COL_METHOD가 C0001, C0002가 아닌 경우)")
        print("=" * 80)
        
        all_orgs = collection.find({})
        openapi_count = 0
        
        for org in all_orgs:
            if 'categoryList' in org:
                for category in org['categoryList']:
                    col_method = category.get('COL_METHOD', '')
                    # C0001: RSS, C0003: Selenium, 그 외: Open API
                    if col_method not in ['C0001', 'C0003'] and col_method:
                        openapi_count += 1
                        print(f"[{openapi_count}] {org.get('orgName', 'N/A')} ({org.get('orgId', 'N/A')})")
                        print(f"    카테고리: {category.get('cateName', 'N/A')} ({category.get('cateId', 'N/A')})")
                        print(f"    수집방법: {col_method}")
                        api_key1 = category.get('APIKEY1', 'N/A')
                        api_key2 = category.get('APIKEY2', 'N/A')
                        if api_key1 and api_key1 != 'N/A':
                            masked = api_key1[:10] + "..." + api_key1[-10:] if len(api_key1) > 20 else api_key1[:5] + "***"
                            print(f"    APIKEY1: {masked}")
                        if api_key2 and api_key2 != 'N/A':
                            masked = api_key2[:10] + "..." + api_key2[-10:] if len(api_key2) > 20 else api_key2[:5] + "***"
                            print(f"    APIKEY2: {masked}")
                        print()
        
        if openapi_count == 0:
            print("⚠️  Open API 카테고리를 찾을 수 없습니다.")
        
        print()
        print("=" * 80)
        print("✅ 조회 완료")
        print("=" * 80)
        
        client.close()
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    query_api_keys()



