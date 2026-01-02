#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV 파일의 URL을 이용하여 contents_queue에서 문서 _id를 추출하는 스크립트

사용법:
    python3 extract_oids_from_csv.py <csv_file_path> <output_file_path>
    
예시:
    python3 extract_oids_from_csv.py naver_news_한국전력_deduped_20251101_20251203.csv test_ids_1101_1203
"""

import sys
import os
import csv
import pymongo
from bson import ObjectId
from datetime import datetime
import pytz

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# 설정
CONTENT_ORG_ID = "A0010"  # 한국전력
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://ksubscribe_mongodb:27017')
MONGO_DB = os.getenv('MONGO_DB', 'mycontents')


def read_urls_from_csv(csv_file_path):
    """
    CSV 파일에서 URL 목록 추출
    
    Returns:
        URL 문자열 리스트
    """
    urls = []
    
    with open(csv_file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            url = row.get('기사 URL', '').strip()
            if url:
                urls.append(url)
    
    return urls


def get_oids_from_urls(urls, org_id):
    """
    contents_queue에서 URL로 문서 _id 조회
    
    Args:
        urls: URL 문자열 리스트
        org_id: 기관 ID
    
    Returns:
        _id 문자열 리스트
    """
    client = None
    oids = []
    
    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client.get_database(MONGO_DB)
        collection = db.get_collection('contents_queue')
        
        print(f"📋 contents_queue에서 {len(urls)}개 URL 조회 중...")
        
        # 오늘 날짜 범위 설정 (UTC 기준)
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=pytz.utc)
        today_end = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=pytz.utc)
        
        # URL로 문서 조회 (오늘 저장된 것만)
        query = {
            "url": {"$in": urls},
            "contentOrgId": org_id,
            "collectDt": {"$gte": today, "$lte": today_end}
        }
        
        cursor = collection.find(query, {"_id": 1, "url": 1, "title": 1, "collectDt": 1}).sort("collectDt", -1)
        
        # URL별로 가장 최근 문서만 선택
        url_to_oid = {}  # {url: oid}
        url_to_title = {}  # {url: title}
        
        for doc in cursor:
            url = doc.get('url', '')
            oid_str = str(doc['_id'])
            
            # 같은 URL에 대해 여러 문서가 있을 수 있으므로, 첫 번째(가장 최근) 것만 사용
            if url and url not in url_to_oid:
                url_to_oid[url] = oid_str
                url_to_title[url] = doc.get('title', 'N/A')
        
        # URL 순서대로 oid 추출
        for url in urls:
            if url in url_to_oid:
                oids.append(url_to_oid[url])
                title = url_to_title[url][:50]
                print(f"  ✅ {url_to_oid[url][:8]}... - {title}...")
        
        # 찾지 못한 URL 확인
        missing_urls = [url for url in urls if url not in url_to_oid]
        if missing_urls:
            print(f"\n⚠️  contents_queue에 없는 URL 수: {len(missing_urls)}건")
            print(f"   예시 (최대 5개):")
            for url in missing_urls[:5]:
                print(f"     - {url[:80]}...")
        
        print(f"\n📊 조회 결과: {len(oids)}건 (고유) / {len(urls)}건 (CSV)")
        
    except Exception as e:
        print(f"❌ MongoDB 조회 실패: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if client:
            client.close()
    
    return oids


def save_oids_to_file(oids, output_file_path):
    """
    _id 목록을 텍스트 파일로 저장 (한 줄에 하나씩)
    
    Args:
        oids: _id 문자열 리스트
        output_file_path: 출력 파일 경로
    """
    output_dir = os.path.dirname(output_file_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # 중복 제거 (혹시 모를 중복 방지)
    unique_oids = list(dict.fromkeys(oids))  # 순서 유지하면서 중복 제거
    
    with open(output_file_path, 'w', encoding='utf-8') as f:
        for oid in unique_oids:
            f.write(f"{oid}\n")
    
    print(f"\n✅ _id 저장 완료: {output_file_path}")
    print(f"   총 {len(unique_oids)}건의 고유 _id 저장")
    if len(unique_oids) != len(oids):
        print(f"   (중복 제거: {len(oids)}건 → {len(unique_oids)}건)")


def main():
    """메인 함수"""
    if len(sys.argv) < 3:
        print("사용법: python3 extract_oids_from_csv.py <csv_file_path> <output_file_name>")
        print("예시: python3 extract_oids_from_csv.py naver_news_한국전력_deduped_20251101_20251203.csv test_ids_1101_1203")
        sys.exit(1)
    
    csv_file_path = sys.argv[1]
    output_file_name = sys.argv[2]
    
    # 파일 존재 확인
    if not os.path.exists(csv_file_path):
        print(f"❌ 오류: CSV 파일을 찾을 수 없습니다: {csv_file_path}")
        sys.exit(1)
    
    # 출력 파일 경로 설정
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file_path = os.path.join(script_dir, output_file_name)
    
    print("=" * 80)
    print("CSV 파일에서 URL 추출 및 contents_queue _id 조회")
    print("=" * 80)
    print(f"📁 CSV 파일: {csv_file_path}")
    print(f"📝 출력 파일: {output_file_path}")
    print(f"🏢 기관 ID: {CONTENT_ORG_ID}")
    print("=" * 80)
    
    try:
        # 1. CSV에서 URL 추출
        print("\n1단계: CSV 파일에서 URL 추출 중...")
        urls = read_urls_from_csv(csv_file_path)
        print(f"   ✅ {len(urls)}개의 URL 추출 완료")
        
        if not urls:
            print("⚠️  추출된 URL이 없습니다.")
            return
        
        # 2. contents_queue에서 _id 조회
        print("\n2단계: contents_queue에서 _id 조회 중...")
        oids = get_oids_from_urls(urls, CONTENT_ORG_ID)
        
        if not oids:
            print("⚠️  조회된 _id가 없습니다.")
            return
        
        # 3. 텍스트 파일로 저장
        print("\n3단계: _id를 텍스트 파일로 저장 중...")
        save_oids_to_file(oids, output_file_path)
        
        print("\n" + "=" * 80)
        print("✅ 모든 작업 완료!")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

