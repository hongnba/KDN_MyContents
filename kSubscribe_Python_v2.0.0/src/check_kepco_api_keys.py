#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한국전력 관련 contents_org 문서 조회 및 APIKEY1, APIKEY2 확인 스크립트
"""

import sys
sys.path.append('/app')
from pymongo import MongoClient
from ksubscribe_share import config as Conf

print('=' * 80)
print('한국전력 contents_org 문서 조회 및 API Key 확인')
print('=' * 80)
print()

try:
    # MongoDB 연결
    connect_string = f'mongodb://{Conf.MONGO_IP}:{Conf.MONGO_PORT}/?directConnection=true&serverSelectionTimeoutMS=300000&socketTimeoutMS=300000'
    client = MongoClient(connect_string, tz_aware=True)
    db = client[Conf.MONGO_DB_NAME]
    collection = db['contents_org']
    
    print('✅ MongoDB 연결 성공')
    print()
    
    # 한국전력 관련 문서 조회 (orgId: A0010)
    print('=' * 80)
    print('한국전력 문서 조회 (orgId: A0010)')
    print('=' * 80)
    
    kepco_doc = collection.find_one({'orgId': 'A0010'})
    
    if not kepco_doc:
        print('❌ 한국전력 문서를 찾을 수 없습니다. (orgId: A0010)')
        client.close()
        sys.exit(1)
    
    print(f'기관명: {kepco_doc.get("orgName", "N/A")}')
    print(f'기관ID: {kepco_doc.get("orgId", "N/A")}')
    print(f'기관 설명: {kepco_doc.get("orgDesc", "N/A")}')
    print()
    
    # categoryList 확인
    if 'categoryList' not in kepco_doc or not kepco_doc['categoryList']:
        print('⚠️  categoryList가 없거나 비어있습니다.')
        client.close()
        sys.exit(1)
    
    print(f'카테고리 개수: {len(kepco_doc["categoryList"])}')
    print()
    
    # 각 카테고리의 APIKEY1, APIKEY2 조회
    print('=' * 80)
    print('각 카테고리의 APIKEY1, APIKEY2 정보')
    print('=' * 80)
    print()
    
    for idx, category in enumerate(kepco_doc['categoryList'], 1):
        cate_id = category.get('cateId', 'N/A')
        cate_name = category.get('cateName', 'N/A')
        api_key1 = category.get('APIKEY1')
        api_key2 = category.get('APIKEY2')
        col_method = category.get('COL_METHOD', 'N/A')
        
        print(f'[{idx}] 카테고리 정보')
        print(f'    카테고리ID: {cate_id}')
        print(f'    카테고리명: {cate_name}')
        print(f'    수집방법: {col_method}')
        print()
        
        # APIKEY1 확인
        if api_key1 is None or api_key1 == '':
            print(f'    APIKEY1: ❌ 없음')
        else:
            # 마스킹 처리 (보안)
            masked_key1 = api_key1[:10] + '...' + api_key1[-10:] if len(api_key1) > 20 else api_key1
            print(f'    APIKEY1: ✅ 있음 (마스킹: {masked_key1})')
            print(f'    APIKEY1 (전체): {api_key1}')
        
        print()
        
        # APIKEY2 확인
        if api_key2 is None or api_key2 == '':
            print(f'    APIKEY2: ❌ 없음')
        else:
            # 마스킹 처리 (보안)
            masked_key2 = api_key2[:10] + '...' + api_key2[-10:] if len(api_key2) > 20 else api_key2
            print(f'    APIKEY2: ✅ 있음 (마스킹: {masked_key2})')
            print(f'    APIKEY2 (전체): {api_key2}')
        
        print()
        print('-' * 80)
        print()
    
    # 요약
    print('=' * 80)
    print('요약')
    print('=' * 80)
    
    total_categories = len(kepco_doc['categoryList'])
    categories_with_key1 = sum(1 for cat in kepco_doc['categoryList'] if cat.get('APIKEY1'))
    categories_with_key2 = sum(1 for cat in kepco_doc['categoryList'] if cat.get('APIKEY2'))
    categories_with_both = sum(1 for cat in kepco_doc['categoryList'] if cat.get('APIKEY1') and cat.get('APIKEY2'))
    
    print(f'총 카테고리 개수: {total_categories}')
    print(f'APIKEY1이 있는 카테고리: {categories_with_key1}')
    print(f'APIKEY2가 있는 카테고리: {categories_with_key2}')
    print(f'APIKEY1과 APIKEY2가 모두 있는 카테고리: {categories_with_both}')
    print()
    
    print('=' * 80)
    print('✅ 조회 완료')
    print('=' * 80)
    
    client.close()
    
except Exception as e:
    print(f'❌ 오류 발생: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)



