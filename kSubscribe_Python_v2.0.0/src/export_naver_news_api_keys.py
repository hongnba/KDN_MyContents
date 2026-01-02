#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
네이버 뉴스 카테고리의 APIKEY1, APIKEY2, collectUrlInfo, pageUrlInfo를 조회하여 표로 정리하는 스크립트
"""

import sys
sys.path.append('/app')
from pymongo import MongoClient
from ksubscribe_share import config as Conf
import pandas as pd
from datetime import datetime

def query_naver_news_categories():
    """contents_org 컬렉션에서 네이버 뉴스 카테고리 정보 조회"""
    print('=' * 100)
    print('네이버 뉴스 카테고리 API Key 및 URL 정보 조회')
    print('=' * 100)
    print()
    
    try:
        # MongoDB 연결
        connect_string = f'mongodb://{Conf.MONGO_IP}:{Conf.MONGO_PORT}/?directConnection=true&serverSelectionTimeoutMS=300000&socketTimeoutMS=300000'
        client = MongoClient(connect_string, tz_aware=True)
        db = client[Conf.MONGO_DB_NAME]
        collection = db['contents_org']
        
        print('✅ MongoDB 연결 성공')
        print()
        
        # Aggregation 파이프라인 실행
        pipeline = [
            # categoryList 배열을 펼치기
            {
                "$unwind": "$categoryList"
            },
            # cateName이 "네이버 뉴스"인 것만 필터링
            {
                "$match": {
                    "categoryList.cateName": "네이버 뉴스"
                }
            },
            # 필요한 필드만 프로젝션
            {
                "$project": {
                    "_id": 0,
                    "orgId": 1,
                    "orgName": 1,
                    "cateId": "$categoryList.cateId",
                    "cateName": "$categoryList.cateName",
                    "APIKEY1": "$categoryList.APIKEY1",
                    "APIKEY2": "$categoryList.APIKEY2",
                    "collectUrlInfo": "$categoryList.collectUrlInfo",
                    "pageUrlInfo": "$categoryList.pageUrlInfo",
                    "COL_METHOD": "$categoryList.COL_METHOD"
                }
            },
            # 정렬 (orgId 순)
            {
                "$sort": { "orgId": 1 }
            }
        ]
        
        print('🔍 네이버 뉴스 카테고리 조회 중...')
        results = list(collection.aggregate(pipeline))
        
        if not results:
            print('⚠️  네이버 뉴스 카테고리를 찾을 수 없습니다.')
            client.close()
            return None
        
        print(f'✅ {len(results)}개의 네이버 뉴스 카테고리 발견')
        print()
        
        # DataFrame 생성
        df = pd.DataFrame(results)
        
        # 컬럼 순서 재정렬
        column_order = ['orgId', 'orgName', 'cateId', 'cateName', 'APIKEY1', 'APIKEY2', 'collectUrlInfo', 'pageUrlInfo', 'COL_METHOD']
        df = df.reindex(columns=column_order)
        
        # APIKEY 마스킹 처리 (보안)
        df_display = df.copy()
        if 'APIKEY1' in df_display.columns:
            df_display['APIKEY1'] = df_display['APIKEY1'].apply(
                lambda x: x[:10] + '...' + x[-10:] if x and len(str(x)) > 20 else x
            )
        if 'APIKEY2' in df_display.columns:
            df_display['APIKEY2'] = df_display['APIKEY2'].apply(
                lambda x: x[:10] + '...' + x[-10:] if x and len(str(x)) > 20 else x
            )
        
        # 표로 출력
        print('=' * 100)
        print('네이버 뉴스 카테고리 정보 (마스킹 처리됨)')
        print('=' * 100)
        print()
        print(df_display.to_string(index=False))
        print()
        
        # 통계 정보
        print('=' * 100)
        print('통계 정보')
        print('=' * 100)
        print(f'총 기관 수: {len(df)}')
        print(f'APIKEY1이 있는 기관: {df["APIKEY1"].notna().sum()}')
        print(f'APIKEY2가 있는 기관: {df["APIKEY2"].notna().sum()}')
        print(f'APIKEY1과 APIKEY2가 모두 있는 기관: {(df["APIKEY1"].notna() & df["APIKEY2"].notna()).sum()}')
        print()
        
        # Excel 파일로 저장 (전체 정보, 마스킹 없음)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        import os
        import shutil
        
        # 컨테이너 내부 경로
        container_excel_path = f'/app/exports/naver_news_api_keys_{timestamp}.xlsx'
        container_csv_path = f'/app/exports/naver_news_api_keys_{timestamp}.csv'
        
        # exports 디렉토리 생성 (컨테이너 내부)
        os.makedirs('/app/exports', exist_ok=True)
        
        # Excel로 저장 (컨테이너 내부 - docker-compose volume 마운트로 로컬과 자동 동기화)
        with pd.ExcelWriter(container_excel_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='네이버뉴스_API정보', index=False)
        
        print(f'✅ Excel 파일 저장 완료: {container_excel_path}')
        print(f'   → 로컬 경로: ./exports/naver_news_api_keys_{timestamp}.xlsx (volume 마운트로 자동 동기화)')
        
        # CSV 파일로도 저장 (컨테이너 내부 - docker-compose volume 마운트로 로컬과 자동 동기화)
        df.to_csv(container_csv_path, index=False, encoding='utf-8-sig')
        print(f'✅ CSV 파일 저장 완료: {container_csv_path}')
        print(f'   → 로컬 경로: ./exports/naver_news_api_keys_{timestamp}.csv (volume 마운트로 자동 동기화)')
        print()
        
        client.close()
        
        return df
        
    except Exception as e:
        print(f'❌ 오류 발생: {e}')
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    query_naver_news_categories()

