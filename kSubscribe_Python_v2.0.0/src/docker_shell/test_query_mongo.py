#!/usr/bin/env python3
"""
MongoDB contents_queue 컬렉션 조회 스크립트
사용법:
    # Docker 컨테이너 내부에서 실행
    docker exec ksubscribe_python_unified python3 /app/docker_shell/test_query_mongo.py
"""

import sys
import os
from pymongo import MongoClient

# 출력 버퍼링 비활성화
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

print("🚀 스크립트 시작...", flush=True)

# Docker 컨테이너 내부에서 실행 시 MongoDB 연결 정보 (docker-compose-unified.yml 기준)
MONGO_IP = "mongodb"  # docker-compose 서비스 이름
MONGO_PORT = 27017
MONGO_DB_NAME = "mycontents"

# 프로젝트 루트 경로 설정 (필요한 경우)
if os.path.exists('/app'):
    sys.path.insert(0, '/app')
    print("✅ Docker 컨테이너 환경 감지", flush=True)
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir.endswith('src'):
        project_root = current_dir
    else:
        project_root = os.path.dirname(current_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    print(f"✅ 호스트 환경 감지: {project_root}", flush=True)
    # 호스트에서 실행 시 localhost 사용
    MONGO_IP = "localhost"

def query_contents_queue(limit=10, org_id=None):
    """contents_queue 컬렉션 조회"""
    print("=" * 80, flush=True)
    print("MongoDB contents_queue 컬렉션 조회", flush=True)
    print("=" * 80, flush=True)
    print(f"연결 정보: {MONGO_IP}:{MONGO_PORT}/{MONGO_DB_NAME}", flush=True)
    print(flush=True)
    
    try:
        print("🔌 MongoDB 연결 시도 중...", flush=True)
        
        # MongoDB 직접 연결 (config.py 사용 안 함)
        connect_string = f"mongodb://{MONGO_IP}:{MONGO_PORT}/?directConnection=true&serverSelectionTimeoutMS=300000&socketTimeoutMS=300000"
        client = MongoClient(connect_string, tz_aware=True)
        db = client[MONGO_DB_NAME]
        collection = db["contents_queue"]
        
        print(f"✅ MongoDB 연결 성공", flush=True)
        print(f"   연결 문자열: {connect_string}", flush=True)
        
        print("📊 문서 수 계산 중...", flush=True)
        total_count = collection.count_documents({})
        print(f"📊 전체 큐 항목 수: {total_count:,}건", flush=True)
        print(flush=True)
        
        if total_count == 0:
            print("⚠️  contents_queue 컬렉션이 비어 있습니다.", flush=True)
            return
        
        query = {}
        if org_id:
            query["contentOrgId"] = org_id
            filtered_count = collection.count_documents(query)
            print(f"🔍 필터링 (기관ID: {org_id}): {filtered_count:,}건", flush=True)
            print(flush=True)
        
        print(f"📋 최신 {limit}개 항목 조회 중...", flush=True)
        cursor = collection.find(query).sort("_id", -1).limit(limit)
        
        print(f"📋 최신 {limit}개 항목:", flush=True)
        print("-" * 80, flush=True)
        
        doc_count = 0
        for i, doc in enumerate(cursor, 1):
            doc_count += 1
            print(f"\n[{i}] ID: {doc.get('_id')}", flush=True)
            print(f"    기관ID: {doc.get('contentOrgId', 'N/A')}", flush=True)
            print(f"    카테고리ID: {doc.get('cateId', 'N/A')}", flush=True)
            title = doc.get('title', 'N/A')
            if title and title != 'N/A':
                print(f"    제목: {title[:60]}", flush=True)
            url = doc.get('url', 'N/A')
            if url and url != 'N/A':
                print(f"    URL: {url[:70]}", flush=True)
            if doc.get('shortUrl'):
                print(f"    짧은URL: {doc.get('shortUrl', 'N/A')[:70]}", flush=True)
            if doc.get('pubDt'):
                print(f"    발행일: {doc.get('pubDt', 'N/A')}", flush=True)
            if doc.get('collectDt'):
                print(f"    수집일: {doc.get('collectDt', 'N/A')}", flush=True)
            if doc.get('collectKeyword'):
                print(f"    수집키워드: {doc.get('collectKeyword', 'N/A')}", flush=True)
        
        if doc_count == 0:
            print("⚠️  조회된 문서가 없습니다.", flush=True)
        
        print(flush=True)
        print("-" * 80, flush=True)
        
        print("\n📊 기관별 큐 항목 수:", flush=True)
        try:
            pipeline = [
                {"$group": {"_id": "$contentOrgId", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            org_stats = list(collection.aggregate(pipeline))
            if org_stats:
                for stat in org_stats:
                    org_id = stat['_id'] if stat['_id'] else 'N/A'
                    print(f"   {org_id}: {stat['count']:,}건", flush=True)
            else:
                print("   통계 데이터가 없습니다.", flush=True)
        except Exception as e:
            print(f"   ⚠️  통계 조회 실패: {e}", flush=True)
        
        print(flush=True)
        print("=" * 80, flush=True)
        print("✅ 조회 완료!", flush=True)
        print("=" * 80, flush=True)
        
        # 연결 종료
        client.close()
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}", flush=True)
        print(f"❌ 오류 타입: {type(e).__name__}", flush=True)
        import traceback
        print("\n상세 오류:", flush=True)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='contents_queue 컬렉션 조회')
    parser.add_argument('--limit', type=int, default=10, help='조회할 항목 수 (기본값: 10)')
    parser.add_argument('--org-id', type=str, help='기관ID로 필터링 (예: A0001)')
    
    args = parser.parse_args()
    
    query_contents_queue(limit=args.limit, org_id=args.org_id)
    print("🏁 스크립트 종료", flush=True)