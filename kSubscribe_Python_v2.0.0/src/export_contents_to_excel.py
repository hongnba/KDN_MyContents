#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MongoDB contents collection에서 날짜별로 데이터를 조회하여
Excel로 저장하는 스크립트 (세로 방향 저장)

사용법:
    python export_contents_to_excel.py 2025-11-22 2025-11-26
    
    또는 날짜 리스트를 직접 수정:
    date_list = ["2025-11-22", "2025-11-26"]
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import pytz
import pandas as pd
from typing import List, Dict, Any
import json

# ObjectId 처리
try:
    from bson import ObjectId
except ImportError:
    ObjectId = None

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from ksubscribe_share.db.mongoManager import MongoManager
    import ksubscribe_share.config as Conf
except ImportError as e:
    print(f"⚠️  모듈 import 실패: {e}")
    print("직접 MongoDB에 연결합니다...")
    from pymongo import MongoClient
    
    # 직접 MongoDB 연결
    MONGO_IP = os.getenv("MONGO_IP", "localhost")
    MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "mycontents")
    
    connectString = f"mongodb://{MONGO_IP}:{MONGO_PORT}/?directConnection=true&serverSelectionTimeoutMS=300000&socketTimeoutMS=300000"
    client = MongoClient(connectString, tz_aware=True)
    db = client[MONGO_DB_NAME]
    
    class SimpleMongoManager:
        def getCollection(self, name):
            return db[name]
    
    MongoManager = SimpleMongoManager()


def query_contents_by_date(date_str: str, collection) -> List[Dict[str, Any]]:
    """
    특정 날짜의 contents를 조회하고 중복 제거 (metaAnalyzeDt 최신 기준)
    
    Args:
        date_str: 날짜 문자열 (예: "2025-11-22")
        collection: MongoDB collection 객체
    
    Returns:
        중복 제거된 문서 리스트
    """
    # 날짜 범위 설정 (해당 날짜의 00:00:00 ~ 23:59:59)
    start_date = datetime.strptime(date_str, "%Y-%m-%d").replace(
        hour=0, minute=0, second=0, microsecond=0, tzinfo=pytz.UTC
    )
    end_date = datetime.strptime(date_str, "%Y-%m-%d").replace(
        hour=23, minute=59, second=59, microsecond=999999, tzinfo=pytz.UTC
    )
    
    # Aggregation Pipeline
    pipeline = [
        # 1단계: 날짜 범위 및 contentsOrgId 필터링
        {
            "$match": {
                "pubDt": {
                    "$gte": start_date,
                    "$lte": end_date
                },
                "contentsOrgId": "A0010"
            }
        },
        # 2단계: metaAnalyzeDt 내림차순 정렬 (최신이 먼저)
        {
            "$sort": {"metaAnalyzeDt": -1}
        },
        # 3단계: url 기준으로 그룹화하고 첫 번째 문서만 선택
        {
            "$group": {
                "_id": "$url",
                "doc": {"$first": "$$ROOT"}
            }
        },
        # 4단계: doc 필드를 루트로 복원
        {
            "$replaceRoot": {"newRoot": "$doc"}
        },
        # 5단계: 최종 정렬
        {
            "$sort": {"pubDt": 1, "metaAnalyzeDt": -1}
        }
    ]
    
    # 쿼리 실행
    results = list(collection.aggregate(pipeline))
    
    return results


def flatten_document(doc: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict[str, Any]:
    """
    MongoDB 문서를 재귀적으로 평탄화 (중첩된 객체와 리스트를 최종 단계까지 펼침)
    
    Args:
        doc: MongoDB 문서
        parent_key: 부모 키 (재귀 호출 시 사용)
        sep: 키 구분자 (기본값: ".")
    
    Returns:
        평탄화된 딕셔너리 (예: {"contentsRaw.title": "...", "contentsMeta.sentiments.0.positiveRatio": 0.5})
    """
    flattened = {}
    
    for key, value in doc.items():
        # 새로운 키 생성
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        
        # ObjectId 처리
        if ObjectId and isinstance(value, ObjectId):
            flattened[new_key] = str(value)
        elif hasattr(value, '__class__') and value.__class__.__name__ == 'ObjectId':
            flattened[new_key] = str(value)
        # datetime 처리
        elif isinstance(value, datetime):
            flattened[new_key] = value.isoformat()
        # dict 처리: 재귀적으로 펼치기
        elif isinstance(value, dict):
            flattened.update(flatten_document(value, new_key, sep))
        # list 처리: 각 요소를 인덱스와 함께 펼치기
        elif isinstance(value, list):
            if len(value) == 0:
                flattened[new_key] = None
            else:
                for idx, item in enumerate(value):
                    if isinstance(item, dict):
                        # 리스트 내 dict는 인덱스를 키에 포함하여 재귀 호출
                        flattened.update(flatten_document(item, f"{new_key}{sep}{idx}", sep))
                    elif isinstance(item, list):
                        # 리스트 내 리스트도 처리
                        flattened[f"{new_key}{sep}{idx}"] = json.dumps(item, ensure_ascii=False, default=str)
                    else:
                        # 기본 타입은 그대로 저장
                        flattened[f"{new_key}{sep}{idx}"] = item
        # None 처리
        elif value is None:
            flattened[new_key] = None
        # 기본 타입 (str, int, float, bool 등)
        else:
            flattened[new_key] = value
    
    return flattened


def export_to_excel(date_list: List[str], output_file: str = None):
    """
    날짜 리스트에 대해 MongoDB 쿼리를 실행하고 Excel로 저장 (세로 방향)
    
    Args:
        date_list: 날짜 문자열 리스트 (예: ["2025-11-22", "2025-11-23"])
        output_file: 출력 Excel 파일 경로 (None이면 자동 생성)
    """
    # MongoDB 연결
    mongo_manager = MongoManager()
    collection = mongo_manager.getCollection("contents")
    
    # Excel 파일 경로 설정 (ksubscribe_share/test/daily_summary 폴더에 저장)
    output_dir = "/app/ksubscribe_share/test/daily_summary"
    os.makedirs(output_dir, exist_ok=True)
    
    if output_file is None:
        filename = f"contents_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        output_file = os.path.join(output_dir, filename)
    elif not os.path.isabs(output_file):
        # 상대 경로인 경우 test/daily_summary 기준으로 변환
        output_file = os.path.join(output_dir, output_file)
    
    output_path = Path(output_file)
    excel_writer = pd.ExcelWriter(output_path, engine='openpyxl')
    
    print(f"📊 MongoDB 쿼리 시작...")
    print(f"📅 처리할 날짜: {', '.join(date_list)}")
    print(f"📄 Excel 파일: {output_path}\n")
    
    total_count = 0
    
    for date_str in date_list:
        print(f"🔍 [{date_str}] 쿼리 실행 중...")
        
        try:
            # MongoDB 쿼리 실행
            results = query_contents_by_date(date_str, collection)
            
            if not results:
                print(f"   ⚠️  데이터 없음\n")
                # 빈 시트 생성
                empty_df = pd.DataFrame()
                empty_df.to_excel(excel_writer, sheet_name=date_str, index=False)
                continue
            
            # 문서 평탄화
            flattened_results = [flatten_document(doc) for doc in results]
            
            # DataFrame 생성
            df = pd.DataFrame(flattened_results)
            
            # 데이터 전치 (행과 열 교환) - 세로 방향으로 저장
            df_transposed = df.T  # 전치
            
            # Excel 시트에 추가 (전치된 데이터)
            df_transposed.to_excel(excel_writer, sheet_name=date_str, index=True)
            print(f"   ✅ Excel 시트 추가: {date_str} ({len(df)}개 문서, 세로 방향)")
            
            total_count += len(df)
            print()
            
        except Exception as e:
            print(f"   ❌ 오류 발생: {e}\n")
            import traceback
            traceback.print_exc()
            # 빈 시트 생성
            empty_df = pd.DataFrame()
            empty_df.to_excel(excel_writer, sheet_name=date_str, index=False)
    
    # Excel 파일 저장
    excel_writer.close()
    
    print(f"✅ 완료!")
    print(f"📊 총 {total_count}개 문서 처리")
    print(f"📄 Excel 파일 저장 경로: {output_path}")
    print(f"📁 절대 경로: {os.path.abspath(output_path)}")


def main():
    """메인 함수"""
    # 날짜 리스트 설정 (여기서 수정)
    date_list = [
        "2025-11-22",
        "2025-11-26"
    ]
    
    # 또는 명령줄 인자로 받기
    if len(sys.argv) > 1:
        date_list = sys.argv[1:]
        print(f"📅 명령줄 인자로 받은 날짜: {date_list}")
    
    # 실행 (output_file=None이면 자동으로 test/daily_summary에 저장)
    export_to_excel(date_list, output_file=None)


if __name__ == "__main__":
    main()

