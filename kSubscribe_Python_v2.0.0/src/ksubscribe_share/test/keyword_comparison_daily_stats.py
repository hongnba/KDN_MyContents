#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
daily_stats 조회 전용 키워드 비교 및 분석 스크립트

contents collection과 daily_stats collection에서 키워드를 추출하여 비교합니다.
단일 날짜를 입력받아 해당 날짜의 daily_stats와 contents를 조회합니다.
"""

import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import os
from datetime import datetime, timedelta
import pytz
import sys
from collections import Counter

# 프로젝트 루트 경로 추가
sys.path.insert(0, '/app')
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO


def query_contents_from_mongodb_by_date(org_id: str, target_date: datetime) -> List[Dict]:
    """
    MongoDB contents collection에서 특정 날짜의 문서들을 조회합니다.
    
    Args:
        org_id: 기관 ID
        target_date: 조회할 날짜 (KST 기준)
        
    Returns:
        조회된 문서들의 리스트 (딕셔너리 형태)
    """
    mongoManager = MongoManager()
    collection = mongoManager.getCollection("contents")
    
    # KST 기준으로 날짜 설정
    kst = pytz.timezone('Asia/Seoul')
    if target_date.tzinfo is None:
        target_date = kst.localize(target_date)
    else:
        target_date = target_date.astimezone(kst)
    
    # 날짜만 추출 (년-월-일)
    target_date_only = target_date.date()
    
    # UTC 날짜 기준으로 범위 생성
    # contents의 pubDt는 UTC로 저장되어 있으므로, UTC 날짜 기준으로 조회
    start_date_utc = pytz.utc.localize(datetime.combine(target_date_only, datetime.min.time()))
    end_date_utc = start_date_utc + timedelta(days=1)
    
    query = {
        "contentsOrgId": org_id,
        "pubDt": {
            "$gte": start_date_utc,
            "$lt": end_date_utc  # 다음 날 00:00:00 미포함
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


def extract_keywords_from_contents(contents_data: List[Dict]) -> Tuple[List[str], List[str]]:
    """
    contents 데이터에서 positiveKeywords와 negativeKeywords를 리스트로 추출합니다.
    Counter를 사용하기 위해 모든 키워드를 리스트로 반환합니다.
    
    Args:
        contents_data: contents 데이터 리스트
        
    Returns:
        (positive_keywords_list, negative_keywords_list): 모든 키워드가 포함된 리스트 튜플
    """
    positive_keywords_list = []
    negative_keywords_list = []
    
    for content in contents_data:
        if 'contentsMeta' not in content or content['contentsMeta'] is None:
            continue
            
        contents_meta = content['contentsMeta']
        if not isinstance(contents_meta, dict) or 'sentiments' not in contents_meta:
            continue
            
        sentiments = contents_meta['sentiments']
        if not isinstance(sentiments, list):
            continue
            
        for sentiment in sentiments:
            # positiveKeywords 추출
            if 'positiveKeywords' in sentiment and isinstance(sentiment['positiveKeywords'], list):
                for keyword in sentiment['positiveKeywords']:
                    if keyword:  # 빈 문자열 제외
                        positive_keywords_list.append(keyword)
            
            # negativeKeywords 추출
            if 'negativeKeywords' in sentiment and isinstance(sentiment['negativeKeywords'], list):
                for keyword in sentiment['negativeKeywords']:
                    if keyword:  # 빈 문자열 제외
                        negative_keywords_list.append(keyword)
    
    return positive_keywords_list, negative_keywords_list


def classify_contents_by_sentiment(contents_data: List[Dict], org_id: str) -> Tuple[int, int, int, int, float, float, float]:
    """
    contents 데이터에서 각 문서를 긍정/부정/중립으로 분류하고 통계를 계산합니다.
    
    Args:
        contents_data: contents 데이터 리스트
        org_id: 기관 ID
        
    Returns:
        (total_count, positive_count, negative_count, neutral_count, 
         avg_positive_ratio, avg_negative_ratio, avg_neutral_ratio)
    """
    total_count = 0
    positive_count = 0
    negative_count = 0
    neutral_count = 0
    
    for content in contents_data:
        if 'contentsMeta' not in content or content['contentsMeta'] is None:
            continue
            
        contents_meta = content['contentsMeta']
        if not isinstance(contents_meta, dict) or 'sentiments' not in contents_meta:
            continue
            
        sentiments = contents_meta['sentiments']
        if not isinstance(sentiments, list):
            continue
        
        # 해당 org_id의 sentiment 찾기
        sentiment_info = None
        for sentiment in sentiments:
            if isinstance(sentiment, dict) and sentiment.get('orgId') == org_id:
                sentiment_info = sentiment
                break
        
        if sentiment_info is None:
            continue
        
        # ratio 추출
        positive_ratio = sentiment_info.get('positiveRatio', 0.0) or 0.0
        negative_ratio = sentiment_info.get('negativeRatio', 0.0) or 0.0
        
        # float로 변환
        try:
            positive_ratio = float(positive_ratio) if positive_ratio is not None else 0.0
            negative_ratio = float(negative_ratio) if negative_ratio is not None else 0.0
        except (ValueError, TypeError):
            continue
        
        total_count += 1
        
        # 분류 로직: positiveRatio > 50 -> 긍정, negativeRatio > 50 -> 부정, 나머지 -> 중립
        if positive_ratio > 50:
            positive_count += 1
        elif negative_ratio > 50:
            negative_count += 1
        else:
            neutral_count += 1
    
    # 평균 비율 계산: (분류된 기사 수 / 전체 기사 수) * 100
    avg_positive_ratio = (positive_count / total_count * 100) if total_count > 0 else 0.0
    avg_negative_ratio = (negative_count / total_count * 100) if total_count > 0 else 0.0
    avg_neutral_ratio = (neutral_count / total_count * 100) if total_count > 0 else 0.0
    
    return total_count, positive_count, negative_count, neutral_count, avg_positive_ratio, avg_negative_ratio, avg_neutral_ratio


def extract_keywords_with_count_from_contents(contents_data: List[Dict]) -> Tuple[Dict[str, int], Dict[str, int]]:
    """
    contents 데이터에서 positiveKeywords와 negativeKeywords를 추출하고 출현 횟수를 카운트합니다.
    Counter를 사용하여 회수를 계산합니다.
    
    Args:
        contents_data: contents 데이터 리스트
        
    Returns:
        (positive_keyword_map, negative_keyword_map): 키워드별 출현 횟수를 담은 딕셔너리 튜플
    """
    # 키워드 리스트 추출
    positive_keywords_list, negative_keywords_list = extract_keywords_from_contents(contents_data)
    
    # Counter를 사용하여 회수 계산
    positive_keyword_map = dict(Counter(positive_keywords_list))
    negative_keyword_map = dict(Counter(negative_keywords_list))
    
    return positive_keyword_map, negative_keyword_map


def create_stats_comparison_dataframe(
    contents_total_count: int,
    contents_positive_count: int,
    contents_negative_count: int,
    contents_neutral_count: int,
    contents_avg_positive_ratio: float,
    contents_avg_negative_ratio: float,
    contents_avg_neutral_ratio: float,
    stats_total_count: int,
    stats_positive_count: int,
    stats_negative_count: int,
    stats_neutral_count: int,
    stats_avg_positive_ratio: float,
    stats_avg_negative_ratio: float,
    stats_avg_neutral_ratio: float
) -> pd.DataFrame:
    """
    contents에서 계산한 통계와 daily_stats의 통계를 비교하는 DataFrame을 생성합니다.
    
    Returns:
        비교 결과를 담은 DataFrame
    """
    data = {
        '항목': [
            'totalContentsCounts',
            'totalPositiveContentsCount',
            'totalNegativeContentsCount',
            'totalNeutralContentsCount',
            'averagePositiveRatio',
            'averageNegativeRatio',
            'averageNeutralRatio'
        ],
        'contents에서 계산한 값': [
            contents_total_count,
            contents_positive_count,
            contents_negative_count,
            contents_neutral_count,
            round(contents_avg_positive_ratio, 2),
            round(contents_avg_negative_ratio, 2),
            round(contents_avg_neutral_ratio, 2)
        ],
        'daily_stats 값': [
            stats_total_count,
            stats_positive_count,
            stats_negative_count,
            stats_neutral_count,
            round(stats_avg_positive_ratio, 2) if stats_avg_positive_ratio is not None else None,
            round(stats_avg_negative_ratio, 2) if stats_avg_negative_ratio is not None else None,
            round(stats_avg_neutral_ratio, 2) if stats_avg_neutral_ratio is not None else None
        ],
        '일치 여부': []
    }
    
    # 일치 여부 계산
    contents_values = data['contents에서 계산한 값']
    stats_values = data['daily_stats 값']
    
    for i in range(len(data['항목'])):
        contents_val = contents_values[i]
        stats_val = stats_values[i]
        
        if stats_val is None:
            data['일치 여부'].append(0)
        elif isinstance(contents_val, float) and isinstance(stats_val, (int, float)):
            # float 비교 (소수점 2자리까지 비교)
            if abs(contents_val - float(stats_val)) < 0.01:
                data['일치 여부'].append(1)
            else:
                data['일치 여부'].append(0)
        else:
            # int 비교
            if contents_val == stats_val:
                data['일치 여부'].append(1)
            else:
                data['일치 여부'].append(0)
    
    df = pd.DataFrame(data)
    return df
    """
    contents 데이터에서 positiveKeywords와 negativeKeywords를 추출하고 출현 횟수를 카운트합니다.
    
    Args:
        contents_data: contents 데이터 리스트
        
    Returns:
        (positive_keyword_map, negative_keyword_map): 키워드별 출현 횟수를 담은 딕셔너리 튜플
    """
    positive_keyword_map = {}
    negative_keyword_map = {}
    
    for content in contents_data:
        if 'contentsMeta' not in content or content['contentsMeta'] is None:
            continue
            
        contents_meta = content['contentsMeta']
        if not isinstance(contents_meta, dict) or 'sentiments' not in contents_meta:
            continue
            
        sentiments = contents_meta['sentiments']
        if not isinstance(sentiments, list):
            continue
            
        for sentiment in sentiments:
            # positiveKeywords 추출 및 카운트
            if 'positiveKeywords' in sentiment and isinstance(sentiment['positiveKeywords'], list):
                for keyword in sentiment['positiveKeywords']:
                    if keyword:  # 빈 문자열 제외
                        positive_keyword_map[keyword] = positive_keyword_map.get(keyword, 0) + 1
            
            # negativeKeywords 추출 및 카운트
            if 'negativeKeywords' in sentiment and isinstance(sentiment['negativeKeywords'], list):
                for keyword in sentiment['negativeKeywords']:
                    if keyword:  # 빈 문자열 제외
                        negative_keyword_map[keyword] = negative_keyword_map.get(keyword, 0) + 1
    
    return positive_keyword_map, negative_keyword_map


def query_daily_stats_from_mongodb(org_id: str, target_date: datetime) -> Optional[Dict]:
    """
    MongoDB daily_stats collection에서 특정 날짜의 문서를 조회합니다.
    
    Args:
        org_id: 기관 ID
        target_date: 조회할 날짜 (KST 기준)
        
    Returns:
        조회된 daily_stats 문서 (딕셔너리 형태) 또는 None
    """
    mongoManager = MongoManager()
    collection = mongoManager.getCollection("daily_stats")
    
    # KST 기준으로 날짜 설정
    kst = pytz.timezone('Asia/Seoul')
    if target_date.tzinfo is None:
        target_date = kst.localize(target_date)
    else:
        target_date = target_date.astimezone(kst)
    
    # KST 기준 날짜의 시작과 끝 시간
    target_date_start_kst = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    target_date_end_kst = target_date_start_kst + timedelta(days=1)
    
    # UTC로 변환
    # daily_stats의 last_calculate_date는 UTC로 저장되어 있으므로, KST 날짜를 UTC로 변환
    target_date_start_utc = target_date_start_kst.astimezone(pytz.utc)
    target_date_end_utc = target_date_end_kst.astimezone(pytz.utc)
    
    query = {
        "orgId": org_id,
        "last_calculate_date": {
            "$gte": target_date_start_utc,
            "$lt": target_date_end_utc
        }
    }
    
    # 가장 최신 문서 조회
    document = collection.find_one(query, sort=[("last_calculate_date", -1)])
    
    if document:
        # ObjectId를 문자열로 변환
        if '_id' in document:
            document['_id'] = str(document['_id'])
        return document
    
    return None


def create_keyword_count_comparison_dataframe(
    contents_keyword_map: Dict[str, int],
    stats_keyword_map: Dict[str, int],
    keyword_type: str = "positive"
) -> pd.DataFrame:
    """
    contents에서 추출한 키워드 맵과 daily_stats의 키워드 맵을 비교하는 DataFrame을 생성합니다.
    
    Args:
        contents_keyword_map: contents에서 추출한 키워드별 출현 횟수 딕셔너리
        stats_keyword_map: daily_stats에서 추출한 키워드별 출현 횟수 딕셔너리
        keyword_type: "positive" 또는 "negative" (컬럼명에 사용)
        
    Returns:
        비교 결과를 담은 DataFrame
    """
    # 모든 키워드를 수집 (두 맵의 키를 합침)
    all_keywords = set(contents_keyword_map.keys()) | set(stats_keyword_map.keys())
    all_keywords = sorted(list(all_keywords))  # 오름차순 정렬
    
    # 리스트 초기화
    contents_keywords_list = []
    contents_counts_list = []
    stats_keywords_list = []
    stats_counts_list = []
    keyword_match_list = []
    count_match_list = []
    
    for keyword in all_keywords:
        contents_count = contents_keyword_map.get(keyword, 0)
        stats_count = stats_keyword_map.get(keyword, 0)
        
        contents_keywords_list.append(keyword)
        contents_counts_list.append(contents_count)
        stats_keywords_list.append(keyword)
        stats_counts_list.append(stats_count)
        
        # 키워드 일치 여부 (항상 1, 같은 키워드를 비교하므로)
        keyword_match_list.append(1)
        
        # 회수 일치 여부
        if contents_count == stats_count:
            count_match_list.append(1)
        else:
            count_match_list.append(0)
    
    # 컬럼명 설정
    if keyword_type == "positive":
        contents_column_name = "contents에서 수집한 긍정 키워드"
        contents_count_column_name = "contents에서 수집한 긍정 키워드 출현 회수"
        stats_column_name = "daily_stats positiveKeywordMap 키"
        stats_count_column_name = "daily_stats positiveKeywordMap 회수"
    else:
        contents_column_name = "contents에서 수집한 부정 키워드"
        contents_count_column_name = "contents에서 수집한 부정 키워드 출현 회수"
        stats_column_name = "daily_stats negativeKeywordMap 키"
        stats_count_column_name = "daily_stats negativeKeywordMap 회수"
    
    df = pd.DataFrame({
        contents_column_name: contents_keywords_list,
        contents_count_column_name: contents_counts_list,
        stats_column_name: stats_keywords_list,
        stats_count_column_name: stats_counts_list,
        '키워드 일치 여부': keyword_match_list,
        '회수 일치 여부': count_match_list
    })
    
    return df


def save_to_excel(dataframes: Dict[str, pd.DataFrame], output_path: str):
    """
    여러 DataFrame을 하나의 엑셀 파일의 개별 시트로 저장합니다.
    
    Args:
        dataframes: {시트명: DataFrame} 형태의 딕셔너리
        output_path: 출력 엑셀 파일 경로
    """
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for sheet_name, df in dataframes.items():
            # 시트명은 최대 31자로 제한 (Excel 제약)
            safe_sheet_name = sheet_name[:31] if len(sheet_name) > 31 else sheet_name
            df.to_excel(writer, sheet_name=safe_sheet_name, index=False)
    
    print(f"엑셀 파일이 저장되었습니다: {output_path}")


def main(org_id: str = None, target_date: datetime = None):
    """
    메인 실행 함수 (daily_stats 조회 전용)
    
    Args:
        org_id: 기관 ID (예: "A0010")
        target_date: 조회할 날짜 (datetime 객체, KST 또는 timezone-aware)
    """
    # 입력 인자 확인
    if org_id is None or target_date is None:
        print("사용법: python keyword_comparison_daily_stats.py <org_id> <target_date>")
        print("예시: python keyword_comparison_daily_stats.py A0010 '2025-12-30'")
        print("\n또는 함수로 호출:")
        print("  main(org_id='A0010', target_date=datetime(...))")
        return
    
    base_dir = Path(__file__).parent
    output_dir = base_dir / "daily_comparison_result"
    
    # 출력 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # MongoDB에서 contents 조회
    print(f"MongoDB에서 contents 조회 중...")
    print(f"  - 기관 ID: {org_id}")
    print(f"  - 조회 날짜: {target_date}")
    contents_data = query_contents_from_mongodb_by_date(org_id, target_date)
    print(f"  - 조회된 문서 수: {len(contents_data)}개")
    
    # 통계 계산 (긍정/부정/중립 분류 및 평균 비율)
    print("통계 계산 중...")
    contents_total_count, contents_positive_count, contents_negative_count, contents_neutral_count, \
        contents_avg_positive_ratio, contents_avg_negative_ratio, contents_avg_neutral_ratio = \
        classify_contents_by_sentiment(contents_data, org_id)
    
    print(f"  - contents 총 기사 수: {contents_total_count}개")
    print(f"  - 긍정 기사: {contents_positive_count}개")
    print(f"  - 부정 기사: {contents_negative_count}개")
    print(f"  - 중립 기사: {contents_neutral_count}개")
    print(f"  - 평균 긍정 비율: {contents_avg_positive_ratio:.2f}%")
    print(f"  - 평균 부정 비율: {contents_avg_negative_ratio:.2f}%")
    print(f"  - 평균 중립 비율: {contents_avg_neutral_ratio:.2f}%")
    
    print("\n키워드 추출 중...")
    # contents에서 키워드 리스트 추출 (Counter 사용을 위해)
    contents_positive_keywords_list, contents_negative_keywords_list = extract_keywords_from_contents(contents_data)
    
    # Counter를 사용하여 회수 계산
    contents_positive_keyword_map = dict(Counter(contents_positive_keywords_list))
    contents_negative_keyword_map = dict(Counter(contents_negative_keywords_list))
    
    print(f"  - contents positive keywords: {len(contents_positive_keyword_map)}개 (고유 키워드)")
    print(f"  - contents negative keywords: {len(contents_negative_keyword_map)}개 (고유 키워드)")
    
    # MongoDB에서 daily_stats 조회
    print(f"\nMongoDB에서 daily_stats 조회 중...")
    print(f"  - 조회 기준 날짜: {target_date} (last_calculate_date가 이 날짜인 daily_stats를 찾음)")
    daily_stats_data = query_daily_stats_from_mongodb(org_id, target_date)
    
    if daily_stats_data:
        print(f"  - daily_stats 문서를 찾았습니다.")
        
        # daily_stats에서 키워드 맵 추출
        daily_positive_keyword_map = daily_stats_data.get('positiveKeywordMap', {}) or {}
        daily_negative_keyword_map = daily_stats_data.get('negativeKeywordMap', {}) or {}
        
        # 딕셔너리로 변환
        if not isinstance(daily_positive_keyword_map, dict):
            daily_positive_keyword_map = {}
        if not isinstance(daily_negative_keyword_map, dict):
            daily_negative_keyword_map = {}
        
        print(f"  - daily_stats positiveKeywordMap: {len(daily_positive_keyword_map)}개 키워드")
        print(f"  - daily_stats negativeKeywordMap: {len(daily_negative_keyword_map)}개 키워드")
        
        # daily_stats에서 통계값 추출
        stats_total_count = daily_stats_data.get('totalContentsCounts', 0) or 0
        stats_positive_count = daily_stats_data.get('totalPositiveContentsCount', 0) or 0
        stats_negative_count = daily_stats_data.get('totalNegativeContentsCount', 0) or 0
        stats_neutral_count = daily_stats_data.get('totalNeutralContentsCount', 0) or 0
        stats_avg_positive_ratio = daily_stats_data.get('averagePositiveRatio', 0.0) or 0.0
        stats_avg_negative_ratio = daily_stats_data.get('averageNegativeRatio', 0.0) or 0.0
        stats_avg_neutral_ratio = daily_stats_data.get('averageNeutralRatio', 0.0) or 0.0
        
        # float로 변환
        try:
            stats_total_count = int(stats_total_count) if stats_total_count is not None else 0
            stats_positive_count = int(stats_positive_count) if stats_positive_count is not None else 0
            stats_negative_count = int(stats_negative_count) if stats_negative_count is not None else 0
            stats_neutral_count = int(stats_neutral_count) if stats_neutral_count is not None else 0
            stats_avg_positive_ratio = float(stats_avg_positive_ratio) if stats_avg_positive_ratio is not None else 0.0
            stats_avg_negative_ratio = float(stats_avg_negative_ratio) if stats_avg_negative_ratio is not None else 0.0
            stats_avg_neutral_ratio = float(stats_avg_neutral_ratio) if stats_avg_neutral_ratio is not None else 0.0
        except (ValueError, TypeError):
            pass
        
        print(f"\ndaily_stats 통계값:")
        print(f"  - 총 기사 수: {stats_total_count}개")
        print(f"  - 긍정 기사: {stats_positive_count}개")
        print(f"  - 부정 기사: {stats_negative_count}개")
        print(f"  - 중립 기사: {stats_neutral_count}개")
        print(f"  - 평균 긍정 비율: {stats_avg_positive_ratio:.2f}%")
        print(f"  - 평균 부정 비율: {stats_avg_negative_ratio:.2f}%")
        print(f"  - 평균 중립 비율: {stats_avg_neutral_ratio:.2f}%")
        
        # 통계 비교 DataFrame 생성
        print("\n통계 비교 중...")
        stats_comparison_df = create_stats_comparison_dataframe(
            contents_total_count,
            contents_positive_count,
            contents_negative_count,
            contents_neutral_count,
            contents_avg_positive_ratio,
            contents_avg_negative_ratio,
            contents_avg_neutral_ratio,
            stats_total_count,
            stats_positive_count,
            stats_negative_count,
            stats_neutral_count,
            stats_avg_positive_ratio,
            stats_avg_negative_ratio,
            stats_avg_neutral_ratio
        )
        
        # 통계 일치 통계 출력
        stats_match_count = stats_comparison_df['일치 여부'].sum()
        print(f"  - 통계 일치 항목: {stats_match_count}개 / {len(stats_comparison_df)}개")
        
        # daily_stats와 비교 DataFrame 생성
        print("\ndaily_stats와 키워드 회수 비교 중...")
        positive_count_comparison_df = create_keyword_count_comparison_dataframe(
            contents_positive_keyword_map,
            daily_positive_keyword_map,
            keyword_type="positive"
        )
        
        negative_count_comparison_df = create_keyword_count_comparison_dataframe(
            contents_negative_keyword_map,
            daily_negative_keyword_map,
            keyword_type="negative"
        )
        
        print(f"  - positive 비교 결과: {positive_count_comparison_df.shape[0]}행")
        print(f"  - negative 비교 결과: {negative_count_comparison_df.shape[0]}행")
        
        # 일치 통계 출력
        positive_keyword_match = positive_count_comparison_df['키워드 일치 여부'].sum()
        positive_count_match = positive_count_comparison_df['회수 일치 여부'].sum()
        negative_keyword_match = negative_count_comparison_df['키워드 일치 여부'].sum()
        negative_count_match = negative_count_comparison_df['회수 일치 여부'].sum()
        
        print(f"\ndaily_stats 비교 통계:")
        print(f"  - positive 키워드 일치: {positive_keyword_match}개")
        print(f"  - positive 회수 일치: {positive_count_match}개")
        print(f"  - negative 키워드 일치: {negative_keyword_match}개")
        print(f"  - negative 회수 일치: {negative_count_match}개")
        
        # 엑셀 파일로 저장 (파일 생성 날짜 정보 추가 - KST 기준)
        kst = pytz.timezone('Asia/Seoul')
        current_datetime_kst = datetime.now(kst).strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f"keyword_comparison_daily_stats_{org_id}_{target_date.strftime('%Y%m%d')}_{current_datetime_kst}.xlsx"
        dataframes = {
            "stats_comparison": stats_comparison_df,
            "positive_count_comparison": positive_count_comparison_df,
            "negative_count_comparison": negative_count_comparison_df
        }
        
        save_to_excel(dataframes, str(output_file))
        
        # CSV 파일로도 저장
        stats_csv = output_dir / f"stats_comparison_daily_{org_id}_{target_date.strftime('%Y%m%d')}.csv"
        positive_csv = output_dir / f"positive_keyword_count_comparison_daily_{org_id}_{target_date.strftime('%Y%m%d')}.csv"
        negative_csv = output_dir / f"negative_keyword_count_comparison_daily_{org_id}_{target_date.strftime('%Y%m%d')}.csv"
        
        stats_comparison_df.to_csv(stats_csv, index=False, encoding='utf-8-sig')
        positive_count_comparison_df.to_csv(positive_csv, index=False, encoding='utf-8-sig')
        negative_count_comparison_df.to_csv(negative_csv, index=False, encoding='utf-8-sig')
        
        print(f"\nCSV 파일도 저장되었습니다:")
        print(f"  - {stats_csv}")
        print(f"  - {positive_csv}")
        print(f"  - {negative_csv}")
    else:
        print(f"  - 해당 날짜의 daily_stats 문서를 찾을 수 없습니다.")
    
    print("\n작업 완료!")


if __name__ == "__main__":
    # 명령줄 인자 처리
    if len(sys.argv) >= 3:
        org_id = sys.argv[1]
        target_date_str = sys.argv[2]
        
        # 날짜 문자열을 datetime으로 변환
        kst = pytz.timezone('Asia/Seoul')
        try:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
            target_date = kst.localize(target_date)
        except ValueError:
            print("날짜 형식 오류: YYYY-MM-DD 형식으로 입력해주세요.")
            sys.exit(1)
        
        main(org_id, target_date)
    else:
        # 기본값으로 실행 (예시)
        print("명령줄 인자가 부족합니다. 기본 예시로 실행합니다.")
        print("사용법: python keyword_comparison_daily_stats.py <org_id> <target_date>")
        print("\n예시 실행:")
        kst = pytz.timezone('Asia/Seoul')
        target_date = kst.localize(datetime(2025, 12, 30, 0, 0, 0))
        main("A0010", target_date)

