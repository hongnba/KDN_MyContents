#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
contents에서 기간별 기사를 조회하여 각 기사별 긍정/부정 키워드를 추출하고 엑셀로 저장하는 스크립트
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pytz
import pandas as pd

# 프로젝트 루트 경로 추가
sys.path.insert(0, '/app')
from ksubscribe_share.db.mongoManager import MongoManager


def query_contents_from_mongodb(org_id: str, start_date: datetime, end_date: datetime) -> list:
    """
    MongoDB contents collection에서 조건에 맞는 문서들을 조회합니다.
    
    Args:
        org_id: 기관 ID
        start_date: 시작 날짜 (KST 기준, 포함)
        end_date: 종료 날짜 (KST 기준, 미포함)
        
    Returns:
        조회된 문서들의 리스트 (딕셔너리 형태)
    """
    mongoManager = MongoManager()
    collection = mongoManager.getCollection("contents")
    
    # KST 기준으로 날짜 설정
    kst = pytz.timezone('Asia/Seoul')
    if start_date.tzinfo is None:
        start_date = kst.localize(start_date)
    else:
        start_date = start_date.astimezone(kst)
    
    if end_date.tzinfo is None:
        end_date = kst.localize(end_date)
    else:
        end_date = end_date.astimezone(kst)
    
    # 날짜만 추출 (년-월-일)
    start_date_only = start_date.date()
    end_date_only = end_date.date()
    
    # UTC 날짜 기준으로 범위 생성
    start_date_utc = pytz.utc.localize(datetime.combine(start_date_only, datetime.min.time()))
    end_date_utc = pytz.utc.localize(datetime.combine(end_date_only, datetime.min.time())) + timedelta(days=1)
    
    query = {
        "contentsOrgId": org_id,
        "pubDt": {
            "$gte": start_date_utc,
            "$lt": end_date_utc
        },
        "metaSucYN": "Y"  # 분석이 완료된 컨텐츠만
    }
    
    cursor = collection.find(query)
    contents_list = []
    
    for doc in cursor:
        # ObjectId를 문자열로 변환
        if '_id' in doc:
            doc['_id'] = str(doc['_id'])
        contents_list.append(doc)
    
    return contents_list


def extract_keywords_from_article(content: dict, org_id: str) -> tuple:
    """
    단일 기사에서 긍정/부정 키워드를 추출합니다.
    
    Args:
        content: contents 문서
        org_id: 기관 ID
        
    Returns:
        (positive_keywords, negative_keywords): 긍정/부정 키워드 리스트 튜플
    """
    positive_keywords = []
    negative_keywords = []
    
    if 'contentsMeta' not in content or content['contentsMeta'] is None:
        return positive_keywords, negative_keywords
        
    contents_meta = content['contentsMeta']
    if not isinstance(contents_meta, dict) or 'sentiments' not in contents_meta:
        return positive_keywords, negative_keywords
        
    sentiments = contents_meta['sentiments']
    if not isinstance(sentiments, list):
        return positive_keywords, negative_keywords
    
    # 해당 org_id의 sentiment 찾기
    for sentiment in sentiments:
        if isinstance(sentiment, dict) and sentiment.get('orgId') == org_id:
            # positiveKeywords 추출
            if 'positiveKeywords' in sentiment and isinstance(sentiment['positiveKeywords'], list):
                positive_keywords = [kw for kw in sentiment['positiveKeywords'] if kw]
            
            # negativeKeywords 추출
            if 'negativeKeywords' in sentiment and isinstance(sentiment['negativeKeywords'], list):
                negative_keywords = [kw for kw in sentiment['negativeKeywords'] if kw]
            
            break
    
    return positive_keywords, negative_keywords


def format_date(pub_dt) -> str:
    """
    pubDt를 YYYY-MM-DD 형식으로 변환합니다.
    
    Args:
        pub_dt: datetime 객체 또는 None
        
    Returns:
        날짜 문자열 (YYYY-MM-DD)
    """
    if pub_dt is None:
        return ""
    
    if isinstance(pub_dt, datetime):
        # UTC로 저장되어 있을 수 있으므로 KST로 변환
        if pub_dt.tzinfo is None:
            pub_dt = pytz.utc.localize(pub_dt)
        
        # KST로 변환
        kst = pytz.timezone('Asia/Seoul')
        pub_dt_kst = pub_dt.astimezone(kst)
        return pub_dt_kst.strftime('%Y-%m-%d')
    
    return ""




def main(org_id: str = "A0010", start_date_str: str = "2025-12-24", end_date_str: str = "2025-12-30"):
    """
    메인 실행 함수
    
    Args:
        org_id: 기관 ID
        start_date_str: 시작 날짜 (YYYY-MM-DD)
        end_date_str: 종료 날짜 (YYYY-MM-DD)
    """
    base_dir = Path(__file__).parent
    
    # 날짜 변환
    kst = pytz.timezone('Asia/Seoul')
    start_date = kst.localize(datetime.strptime(start_date_str, '%Y-%m-%d'))
    end_date = kst.localize(datetime.strptime(end_date_str, '%Y-%m-%d'))
    
    print(f"contents 조회 중...")
    print(f"  - 기관 ID: {org_id}")
    print(f"  - 기간: {start_date_str} ~ {end_date_str}")
    
    # MongoDB에서 contents 조회
    contents_data = query_contents_from_mongodb(org_id, start_date, end_date)
    print(f"  - 조회된 문서 수: {len(contents_data)}개")
    
    # 각 기사별로 키워드 추출
    print("\n키워드 추출 중...")
    positive_articles_data = []
    negative_articles_data = []
    
    for content in contents_data:
        pub_dt = content.get('pubDt')
        url = content.get('url', '')
        title = content.get('title', '')
        date_str = format_date(pub_dt)
        
        # 긍정/부정 키워드 추출
        positive_keywords, negative_keywords = extract_keywords_from_article(content, org_id)
        
        # 긍정 키워드가 있으면 긍정 시트에 추가 (각 키워드별로 행 생성)
        if positive_keywords:
            for keyword in positive_keywords:
                positive_articles_data.append({
                    '키워드': keyword,
                    '날짜': date_str,
                    '기사 URL': url,
                    '기사 제목': title
                })
        
        # 부정 키워드가 있으면 부정 시트에 추가 (각 키워드별로 행 생성)
        if negative_keywords:
            for keyword in negative_keywords:
                negative_articles_data.append({
                    '키워드': keyword,
                    '날짜': date_str,
                    '기사 URL': url,
                    '기사 제목': title
                })
    
    print(f"  - 긍정 키워드 행 수: {len(positive_articles_data)}개")
    print(f"  - 부정 키워드 행 수: {len(negative_articles_data)}개")
    
    # DataFrame 생성
    positive_df = pd.DataFrame(positive_articles_data)
    negative_df = pd.DataFrame(negative_articles_data)
    
    # 날짜 기준으로 정렬
    if not positive_df.empty:
        positive_df = positive_df.sort_values(['날짜', '키워드'])
    if not negative_df.empty:
        negative_df = negative_df.sort_values(['날짜', '키워드'])
    
    # 엑셀 파일로 저장 (KST 시간 포함)
    current_datetime_kst = datetime.now(kst).strftime('%Y%m%d_%H%M%S')
    output_file = base_dir / f"keywords_by_article_{org_id}_{start_date_str.replace('-', '')}_{end_date_str.replace('-', '')}_{current_datetime_kst}.xlsx"
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        if not positive_df.empty:
            positive_df.to_excel(writer, sheet_name='긍정', index=False)
        if not negative_df.empty:
            negative_df.to_excel(writer, sheet_name='부정', index=False)
    
    print(f"\n✅ 엑셀 파일 저장 완료: {output_file}")
    print(f"  - 긍정 시트: {len(positive_articles_data)}행")
    print(f"  - 부정 시트: {len(negative_articles_data)}행")


if __name__ == "__main__":
    if len(sys.argv) >= 4:
        org_id = sys.argv[1]
        start_date_str = sys.argv[2]
        end_date_str = sys.argv[3]
        main(org_id, start_date_str, end_date_str)
    else:
        # 기본값으로 실행
        main()

