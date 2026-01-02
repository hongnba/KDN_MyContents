#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
negative_keyword_list.txt의 각 텍스트를 contents에서 검색하여 기사 정보를 추출하는 스크립트
"""

import csv
import sys
from pathlib import Path
from datetime import datetime
import pytz

# 프로젝트 루트 경로 추가
sys.path.insert(0, '/app')
from ksubscribe_share.db.mongoManager import MongoManager


def load_negative_keywords(file_path: str) -> list:
    """
    negative_keyword_list.txt 파일을 읽어서 각 줄의 텍스트를 리스트로 반환합니다.
    
    Args:
        file_path: 파일 경로
        
    Returns:
        텍스트 리스트 (빈 줄 제외)
    """
    keywords = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:  # 빈 줄 제외
                keywords.append(line)
    return keywords


def search_contents_by_text(search_text: str, min_date: datetime = None) -> list:
    """
    contents 컬렉션에서 주어진 텍스트가 포함된 문서를 검색합니다.
    title 또는 contentsRaw.contents 필드에서 검색합니다.
    텍스트를 "로 감싸서 정확한 문자열로 검색합니다.
    
    Args:
        search_text: 검색할 텍스트
        min_date: 최소 날짜 (pubDt >= min_date 조건, UTC datetime)
        
    Returns:
        검색된 문서 리스트 (url, title, pubDt 포함)
    """
    mongoManager = MongoManager()
    collection = mongoManager.getCollection("contents")
    
    # 특수 문자 이스케이프 (MongoDB regex에서 필요)
    import re
    
    # 텍스트를 "로 감싸서 검색 시도
    # 먼저 전체 텍스트로 검색, 없으면 "로 감싼 버전으로 검색
    search_patterns = []
    
    # 1. 전체 텍스트 (길면 앞부분만)
    if len(search_text) > 100:
        search_text_short = search_text[:100]
        last_space = search_text_short.rfind(' ')
        if last_space > 30:
            search_text_short = search_text_short[:last_space]
    else:
        search_text_short = search_text
    
    # 2. "로 감싼 버전
    quoted_text = f'"{search_text_short}"'
    
    # 3. "로 감싸지 않은 버전
    unquoted_text = search_text_short
    
    # 두 가지 패턴 모두 시도
    for pattern_text in [quoted_text, unquoted_text]:
        escaped_text = re.escape(pattern_text)
        
        query = {
            "$or": [
                {"title": {"$regex": escaped_text, "$options": "i"}},
                {"contentsRaw.contents": {"$regex": escaped_text, "$options": "i"}}
            ]
        }
        
        # pubDt >= min_date 조건 추가 (UTC 기준)
        if min_date:
            query["pubDt"] = {"$gte": min_date}
        
        cursor = collection.find(query, {"url": 1, "title": 1, "pubDt": 1, "_id": 0})
        found_docs = list(cursor)
        
        if found_docs:
            # 결과가 있으면 반환
            results = []
            for doc in found_docs:
                results.append({
                    "url": doc.get("url", ""),
                    "title": doc.get("title", ""),
                    "pubDt": doc.get("pubDt", None)
                })
            return results
    
    # 두 패턴 모두 실패하면 빈 리스트 반환
    return []
    
    # pubDt >= min_date 조건 추가 (UTC 기준)
    if min_date:
        query["pubDt"] = {"$gte": min_date}
    
    results = []
    cursor = collection.find(query, {"url": 1, "title": 1, "pubDt": 1, "_id": 0})
    
    for doc in cursor:
        results.append({
            "url": doc.get("url", ""),
            "title": doc.get("title", ""),
            "pubDt": doc.get("pubDt", None)
        })
    
    return results


def format_title(title: str) -> str:
    """
    기사 제목을 CSV 형식에 맞게 포맷합니다.
    이미 "로 감싸져 있지 않으면 "로 감쌉니다.
    
    Args:
        title: 기사 제목
        
    Returns:
        포맷된 제목
    """
    if not title:
        return '""'
    
    # 이미 "로 시작하고 끝나면 그대로 반환
    if title.startswith('"') and title.endswith('"'):
        return title
    
    # "가 포함되어 있으면 "로 감싸기
    if '"' in title or ',' in title or '\n' in title:
        # 내부의 "는 ""로 이스케이프
        escaped_title = title.replace('"', '""')
        return f'"{escaped_title}"'
    
    return title


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
            # timezone이 없으면 UTC로 가정
            pub_dt = pytz.utc.localize(pub_dt)
        
        # KST로 변환
        kst = pytz.timezone('Asia/Seoul')
        pub_dt_kst = pub_dt.astimezone(kst)
        return pub_dt_kst.strftime('%Y-%m-%d')
    
    return ""


def main():
    """메인 실행 함수"""
    base_dir = Path(__file__).parent
    
    # 파일 경로
    keyword_file = base_dir / "negatvie_keyword_list.txt"
    output_file = base_dir / "negative_keyword_article_list.csv"
    
    # 최소 날짜 설정 (2025-12-24 이후, KST 기준)
    kst = pytz.timezone('Asia/Seoul')
    min_date_kst = datetime(2025, 12, 24, 0, 0, 0)
    min_date_kst = kst.localize(min_date_kst)
    # UTC로 변환 (MongoDB는 UTC로 저장)
    # KST 2025-12-24 00:00:00 = UTC 2025-12-23 15:00:00
    min_date_utc = min_date_kst.astimezone(pytz.utc)
    
    print(f"조회 기간: 2025-12-24 이후 (KST 기준)")
    print(f"  - UTC 변환: {min_date_utc}")
    
    # 실제 데이터 확인
    mongoManager = MongoManager()
    collection = mongoManager.getCollection("contents")
    total_count = collection.count_documents({"pubDt": {"$gte": min_date_utc}})
    print(f"  - 해당 기간 전체 기사 수: {total_count}개")
    
    # negative_keyword_list.txt 로드
    print(f"\n키워드 파일 로드 중: {keyword_file}")
    keywords = load_negative_keywords(str(keyword_file))
    print(f"  - 로드된 키워드 수: {len(keywords)}개")
    
    # 결과 저장용 리스트
    all_results = []
    
    # 각 키워드에 대해 검색
    print("\ncontents 검색 중...")
    for idx, keyword in enumerate(keywords, 1):
        print(f"  [{idx}/{len(keywords)}] 검색 중: {keyword[:50]}...")
        results = search_contents_by_text(keyword, min_date_utc)
        print(f"    → {len(results)}개 문서 발견")
        
        for result in results:
            # 중복 제거를 위해 (keyword, url) 조합으로 체크
            # 같은 URL이 여러 키워드에서 발견될 수 있으므로 키워드 정보도 함께 저장
            all_results.append({
                "keyword": keyword,
                "url": result["url"],
                "title": result["title"],
                "pubDt": result["pubDt"]
            })
    
    print(f"\n총 {len(all_results)}개 결과 발견")
    
    # URL 기준으로 중복 제거 (같은 기사가 여러 키워드에서 발견된 경우)
    # 가장 최신 날짜의 것을 유지
    print("\n중복 제거 중...")
    unique_results = {}
    for result in all_results:
        url = result["url"]
        if url not in unique_results:
            unique_results[url] = result
        else:
            # 날짜 비교하여 더 최신인 것으로 업데이트
            current_pub_dt = result["pubDt"]
            existing_pub_dt = unique_results[url]["pubDt"]
            if current_pub_dt and existing_pub_dt:
                if current_pub_dt > existing_pub_dt:
                    unique_results[url] = result
            elif current_pub_dt and not existing_pub_dt:
                unique_results[url] = result
    
    print(f"  - 중복 제거 후: {len(unique_results)}개")
    
    # CSV 파일로 저장
    print(f"\nCSV 파일 저장 중: {output_file}")
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        
        # 헤더 작성
        writer.writerow(["날짜", "구분", "기사 제목", "기사 URL"])
        
        # 데이터 작성 (pubDt 기준으로 정렬)
        sorted_results = sorted(unique_results.values(), key=lambda x: x["pubDt"] if x["pubDt"] else datetime.min)
        
        for result in sorted_results:
            date_str = format_date(result["pubDt"])
            title = format_title(result["title"])
            url = result["url"]
            
            # 구분은 "부정"으로 설정 (negative keyword이므로)
            writer.writerow([date_str, "부정", title, url])
    
    print(f"✅ 저장 완료: {output_file}")
    print(f"  - 총 {len(unique_results)}개 기사")


if __name__ == "__main__":
    main()

