#!/usr/bin/env python3
"""
MongoDB 컬렉션 정보 확인 스크립트
- predefine_keyword 컬렉션의 문서 개수 확인
- 기관별 키워드 정보 확인
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.append("/home/themiraclesoft/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src")

try:
    from ksubscribe_share.db.service.predefineKeywordService import PredefineKeywordService
    from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
    from ksubscribe_share.db.mongoManager import MongoManager
except ImportError as e:
    print(f"⚠️  모듈 import 실패: {e}")
    print("직접 MongoDB에 연결합니다...")
    from pymongo import MongoClient
    import ksubscribe_share.config as Conf
    
    # 직접 MongoDB 연결
    connectString = f"mongodb://{Conf.MONGO_IP}:{Conf.MONGO_PORT}/?directConnection=true&serverSelectionTimeoutMS=300000&socketTimeoutMS=300000"
    client = MongoClient(connectString, tz_aware=True)
    db = client[Conf.MONGO_DB_NAME]
    
    # MongoManager 대체
    class SimpleMongoManager:
        def getCollection(self, name):
            return db[name]
    
    MongoManager = SimpleMongoManager

def check_predefine_keyword_count():
    """predefine_keyword 컬렉션의 문서 개수 확인"""
    try:
        mongo_manager = MongoManager()
        collection = mongo_manager.getCollection("predefine_keyword")
        
        # 전체 문서 개수
        total_count = collection.count_documents({})
        
        # deleteYN이 "Y"가 아닌 문서 개수 (활성화된 키워드)
        active_count = collection.count_documents({"deleteYN": {"$ne": "Y"}})
        
        # subscriberIds가 있는 문서 개수 (기관/사용자와 연결된 키워드)
        with_subscribers = collection.count_documents({"subscriberIds": {"$exists": True, "$ne": []}})
        
        print("=" * 60)
        print("📊 predefine_keyword 컬렉션 통계")
        print("=" * 60)
        print(f"전체 문서 개수: {total_count}")
        print(f"활성화된 키워드 (deleteYN != 'Y'): {active_count}")
        print(f"기관/사용자와 연결된 키워드 (subscriberIds 존재): {with_subscribers}")
        print("=" * 60)
        
        return total_count, active_count, with_subscribers
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return None, None, None

def check_org_keywords():
    """기관별 키워드 정보 확인"""
    try:
        org_service = ContentsOrgService()
        mongo_manager = MongoManager()
        collection = mongo_manager.getCollection("contents_org")
        
        # 모든 기관 조회
        orgs = collection.find({}, {"orgId": 1, "orgName": 1, "orgKeywordList": 1})
        
        print("\n" + "=" * 60)
        print("🏢 기관별 키워드 정보")
        print("=" * 60)
        
        org_count = 0
        orgs_with_keywords = 0
        
        for org in orgs:
            org_count += 1
            org_id = org.get("orgId", "N/A")
            org_name = org.get("orgName", "N/A")
            org_keywords = org.get("orgKeywordList", [])
            
            if org_keywords:
                orgs_with_keywords += 1
                print(f"\n[{org_id}] {org_name}")
                print(f"  - orgKeywordList 개수: {len(org_keywords)}")
                print(f"  - 키워드: {', '.join(org_keywords[:5])}{'...' if len(org_keywords) > 5 else ''}")
        
        print("\n" + "=" * 60)
        print(f"전체 기관 수: {org_count}")
        print(f"키워드가 있는 기관 수: {orgs_with_keywords}")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

def check_keyword_org_relationship():
    """predefine_keyword와 기관의 관계 확인"""
    try:
        mongo_manager = MongoManager()
        keyword_collection = mongo_manager.getCollection("predefine_keyword")
        org_collection = mongo_manager.getCollection("contents_org")
        
        # subscriberIds가 있는 키워드 조회
        keywords_with_subscribers = keyword_collection.find(
            {"subscriberIds": {"$exists": True, "$ne": []}},
            {"keyword": 1, "subscriberIds": 1}
        )
        
        print("\n" + "=" * 60)
        print("🔗 predefine_keyword와 기관 연결 정보")
        print("=" * 60)
        
        keyword_org_map = {}
        
        for keyword_doc in keywords_with_subscribers:
            keyword = keyword_doc.get("keyword", "N/A")
            subscriber_ids = keyword_doc.get("subscriberIds", [])
            
            # subscriberIds가 orgId인지 확인
            for sub_id in subscriber_ids:
                org = org_collection.find_one({"orgId": sub_id}, {"orgName": 1})
                if org:
                    if keyword not in keyword_org_map:
                        keyword_org_map[keyword] = []
                    keyword_org_map[keyword].append(org.get("orgName", sub_id))
        
        print(f"\n기관과 연결된 키워드 수: {len(keyword_org_map)}")
        print("\n예시 (최대 10개):")
        for i, (keyword, orgs) in enumerate(list(keyword_org_map.items())[:10]):
            print(f"  - {keyword}: {', '.join(orgs[:3])}{'...' if len(orgs) > 3 else ''}")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

def main():
    print("🔍 MongoDB 컬렉션 정보 확인 시작\n")
    
    # 1. predefine_keyword 컬렉션 개수 확인
    check_predefine_keyword_count()
    
    # 2. 기관별 키워드 정보 확인
    check_org_keywords()
    
    # 3. 키워드-기관 관계 확인
    check_keyword_org_relationship()
    
    print("\n✅ 확인 완료")

if __name__ == "__main__":
    main()

