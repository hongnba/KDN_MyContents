#!/usr/bin/env python3
"""
MongoDB contents 컬렉션에서 가장 최근에 작성된 문서를 조회하는 스크립트
"""
import sys
import os
from datetime import datetime
import pytz
import json

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from ksubscribe_share.db.service.contentsService import ContentsService
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO
from pymongo import DESCENDING


def query_latest_contents(limit=1, sort_by="metaAnalyzeDt"):
    """
    contents 컬렉션에서 가장 최근 문서 조회
    
    Args:
        limit: 조회할 문서 수 (기본값: 1)
        sort_by: 정렬 기준 필드 (기본값: "metaAnalyzeDt")
                 옵션: "metaAnalyzeDt", "rawCollectDt", "collectDt", "_id"
    """
    try:
        print("=" * 80)
        print("MongoDB contents 컬렉션 최신 문서 조회")
        print("=" * 80)
        print(f"정렬 기준: {sort_by}")
        print(f"조회 개수: {limit}")
        print("=" * 80)
        print()
        
        # ContentsService 초기화
        contents_service = ContentsService()
        collection = contents_service.mongoManager.getCollection("contents")
        
        # 전체 문서 수 확인
        total_count = collection.count_documents({})
        print(f"📊 전체 contents 문서 수: {total_count:,}건")
        print()
        
        if total_count == 0:
            print("⚠️  contents 컬렉션이 비어 있습니다.")
            return
        
        # 정렬 기준에 따라 쿼리
        sort_fields = []
        if sort_by == "metaAnalyzeDt":
            sort_fields = [("metaAnalyzeDt", DESCENDING), ("rawCollectDt", DESCENDING), ("_id", DESCENDING)]
        elif sort_by == "rawCollectDt":
            sort_fields = [("rawCollectDt", DESCENDING), ("metaAnalyzeDt", DESCENDING), ("_id", DESCENDING)]
        elif sort_by == "collectDt":
            sort_fields = [("collectDt", DESCENDING), ("_id", DESCENDING)]
        else:  # _id
            sort_fields = [("_id", DESCENDING)]
        
        # 최신 문서 조회
        print(f"🔍 최신 {limit}개 문서 조회 중...")
        print()
        
        cursor = collection.find({}).sort(sort_fields).limit(limit)
        
        for idx, doc in enumerate(cursor, 1):
            print(f"{'=' * 80}")
            print(f"📄 문서 #{idx}")
            print(f"{'=' * 80}")
            
            # ContentsVO로 변환 (가능한 경우)
            try:
                content = ContentsVO.from_mongo(doc)
                print(f"📌 문서 ID: {content._id}")
                print(f"📌 제목: {content.title}")
                print(f"📌 URL: {content.url}")
                print(f"📌 기관 ID: {content.contentOrgId}")
                print(f"📌 카테고리 ID: {content.cateId}")
                print(f"📌 수집 키워드: {content.collectKeyword}")
                print(f"📌 발행일: {content.pubDt}")
                print(f"📌 수집일 (collectDt): {content.collectDt}")
                print(f"📌 원본 수집일 (rawCollectDt): {content.rawCollectDt}")
                print(f"📌 메타 분석일 (metaAnalyzeDt): {content.metaAnalyzeDt}")
                print(f"📌 메타 분석 성공 여부: {content.metaSucYN}")
                print(f"📌 감정 분석: {content.metaSentiment}")
                print(f"📌 키워드: {content.metaKeywords}")
                if content.shortSummary:
                    print(f"📌 요약: {content.shortSummary[:100]}..." if len(content.shortSummary) > 100 else f"📌 요약: {content.shortSummary}")
            except Exception as e:
                # ContentsVO 변환 실패 시 원본 문서 출력
                print(f"⚠️  ContentsVO 변환 실패, 원본 문서 출력: {e}")
                print(f"📌 문서 ID: {doc.get('_id', 'N/A')}")
                print(f"📌 제목: {doc.get('title', 'N/A')}")
                print(f"📌 URL: {doc.get('url', 'N/A')}")
                print(f"📌 기관 ID: {doc.get('contentOrgId', 'N/A')}")
                print(f"📌 카테고리 ID: {doc.get('cateId', 'N/A')}")
                print(f"📌 수집 키워드: {doc.get('collectKeyword', 'N/A')}")
                print(f"📌 발행일: {doc.get('pubDt', 'N/A')}")
                print(f"📌 수집일 (collectDt): {doc.get('collectDt', 'N/A')}")
                print(f"📌 원본 수집일 (rawCollectDt): {doc.get('rawCollectDt', 'N/A')}")
                print(f"📌 메타 분석일 (metaAnalyzeDt): {doc.get('metaAnalyzeDt', 'N/A')}")
                print(f"📌 메타 분석 성공 여부: {doc.get('metaSucYN', 'N/A')}")
                print(f"📌 감정 분석: {doc.get('metaSentiment', 'N/A')}")
                print(f"📌 키워드: {doc.get('metaKeywords', 'N/A')}")
            
            print()
            print(f"{'─' * 80}")
            print("📋 전체 문서 (JSON 형식):")
            print(f"{'─' * 80}")
            # JSON으로 출력 (ObjectId 등은 문자열로 변환)
            doc_json = json.loads(json.dumps(doc, default=str, ensure_ascii=False, indent=2))
            print(json.dumps(doc_json, indent=2, ensure_ascii=False))
            print()
        
        print("=" * 80)
        print("✅ 조회 완료")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MongoDB contents 컬렉션에서 최신 문서 조회")
    parser.add_argument(
        "--limit",
        type=int,
        default=1,
        help="조회할 문서 수 (기본값: 1)"
    )
    parser.add_argument(
        "--sort-by",
        type=str,
        default="metaAnalyzeDt",
        choices=["metaAnalyzeDt", "rawCollectDt", "collectDt", "_id"],
        help="정렬 기준 필드 (기본값: metaAnalyzeDt)"
    )
    
    args = parser.parse_args()
    
    query_latest_contents(limit=args.limit, sort_by=args.sort_by)



