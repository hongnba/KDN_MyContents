#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV 파일에서 기사 정보를 읽어서 contents_queue에 저장하는 스크립트

사용법:
    python3 import_csv_to_contents_queue.py <csv_file_path>
    
예시:
    python3 import_csv_to_contents_queue.py article_202511_fixed.csv
"""

import sys
import os
import csv
import re
from datetime import datetime
import pytz

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from ksubscribe_share.utils.random_utils import generate_random_string
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
from ksubscribe_share.db.service.baseQueryService import BaseQueryService
from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.logger import Logger

# 설정
CONTENT_ORG_ID = "A0010"  # 한국전력
CATE_ID = "B0010"         # 네이버 뉴스
COLLECT_KEYWORD = "한국전력"  # 고정 키워드


def parse_date(date_str):
    """
    날짜 문자열을 datetime 객체로 변환
    
    지원 형식:
    - "2025-11-01" (YYYY-MM-DD)
    - "11월 01일" (MM월 DD일, 연도는 2025로 가정)
    - "20251101" (YYYYMMDD)
    """
    # YYYY-MM-DD 형식
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return datetime.strptime(date_str, "%Y-%m-%d")
    
    # YYYYMMDD 형식
    if re.match(r'^\d{8}$', date_str):
        return datetime.strptime(date_str, "%Y%m%d")
    
    # "11월 01일" 형식
    match = re.match(r'(\d{1,2})월\s*(\d{1,2})일', date_str)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        # 연도는 2025로 가정
        return datetime(2025, month, day)
    
    raise ValueError(f"날짜 형식을 인식할 수 없습니다: {date_str}")


def date_to_yyyymmdd(date_obj):
    """datetime 객체를 YYYYMMDD 문자열로 변환"""
    return date_obj.strftime("%Y%m%d")


def get_article_count_by_date(year=2025, month=11, logger=None):
    """
    contents_queue에서 특정 년/월의 날짜별 기사 건수 조회
    
    Args:
        year: 연도 (기본값: 2025)
        month: 월 (기본값: 11)
        logger: 로거 객체 (선택)
    
    Returns:
        dict: {
            "daily": {날짜: 건수},  # 예: {"2025-11-01": 3, "2025-11-02": 2, ...}
            "total": 총 건수
        }
    """
    if logger is None:
        logger = Logger().setup_logger(Logger.docker_collect_logger_name)
    
    mongoManager = MongoManager()
    collection = mongoManager.getCollection(ContentsQueueVO.collectionName)
    
    # 2025년 11월 범위 설정 (YYYYMMDD 형식)
    start_date_str = f"{year}{month:02d}01"  # "20251122"
    end_date_str = f"{year}{month:02d}31"    # "20251126"
    
    # MongoDB aggregation으로 날짜별 건수 집계
    pipeline = [
        {
            "$match": {
                "contentOrgId": CONTENT_ORG_ID,
                "cateId": CATE_ID,
                "pubDt": {
                    "$gte": start_date_str,
                    "$lte": end_date_str
                }
            }
        },
        {
            "$group": {
                "_id": "$pubDt",
                "count": {"$sum": 1}
            }
        },
        {
            "$sort": {"_id": 1}  # 날짜순 정렬
        }
    ]
    
    results = list(collection.aggregate(pipeline))
    
    # 날짜별 건수 딕셔너리 생성
    daily_counts = {}
    total_count = 0
    
    for result in results:
        pub_dt_str = result["_id"]  # "20251101"
        count = result["count"]
        
        # YYYYMMDD를 YYYY-MM-DD 형식으로 변환
        if len(pub_dt_str) == 8:
            formatted_date = f"{pub_dt_str[:4]}-{pub_dt_str[4:6]}-{pub_dt_str[6:8]}"
            daily_counts[formatted_date] = count
            total_count += count
    
    return {
        "daily": daily_counts,
        "total": total_count
    }


def read_csv_file(csv_file_path):
    """
    CSV 파일을 읽어서 기사 정보 리스트 반환
    
    반환 형식:
    [
        {
            "date": datetime 객체,
            "title": "기사 제목",
            "url": "기사 URL"
        },
        ...
    ]
    """
    articles = []
    
    with open(csv_file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            try:
                # 날짜 파싱
                date_str = row.get('날짜', '').strip()
                if not date_str:
                    print(f"⚠️  날짜가 없는 행을 건너뜁니다: {row.get('기사 제목', '')}")
                    continue
                
                date_obj = parse_date(date_str)
                
                # 제목과 URL 확인
                title = row.get('기사 제목', '').strip()
                url = row.get('기사 URL', '').strip()
                
                if not title or not url:
                    print(f"⚠️  제목 또는 URL이 없는 행을 건너뜁니다: {title}")
                    continue
                
                articles.append({
                    "date": date_obj,
                    "title": title,
                    "url": url
                })
                
            except ValueError as e:
                print(f"⚠️  날짜 파싱 오류 (행 건너뜀): {e} - {row.get('기사 제목', '')}")
                continue
            except Exception as e:
                print(f"⚠️  오류 발생 (행 건너뜀): {e} - {row}")
                continue
    
    return articles


def save_to_contents_queue(articles, logger=None):
    """
    기사 정보를 contents_queue에 저장
    
    Args:
        articles: 기사 정보 리스트
        logger: 로거 객체 (선택)
    
    Returns:
        dict: {
            "success": 성공 건수,
            "skip": 건너뜀 건수,
            "error": 실패 건수,
            "total": 전체 건수,
            "inserted_ids": 저장된 문서의 _id 리스트
        }
    """
    if logger is None:
        logger = Logger().setup_logger(Logger.docker_collect_logger_name)
    
    success_count = 0
    skip_count = 0
    error_count = 0
    inserted_ids = []  # 저장된 문서의 _id 리스트
    
    # 오늘 날짜/시간 (UTC)
    collect_dt = datetime.utcnow().replace(tzinfo=pytz.utc)
    collect_dt_str = collect_dt.strftime("%Y%m%d")
    
    logger.info(f"📝 CSV 파일에서 {len(articles)}건의 기사를 읽었습니다.")
    logger.info(f"📅 수집일: {collect_dt_str}")
    logger.info(f"🏢 기관 ID: {CONTENT_ORG_ID}")
    logger.info(f"📂 카테고리 ID: {CATE_ID}")
    logger.info(f"🔑 수집 키워드: {COLLECT_KEYWORD}")
    logger.info("=" * 80)
    
    for idx, article in enumerate(articles, 1):
        try:
            # URL 중복 체크
            if ContentsQueueService().isExistQueue(article['url']):
                skip_count += 1
                logger.debug(f"[{idx}/{len(articles)}] ⏭️  이미 존재하는 URL (건너뜀): {article['url']}")
                continue
            
            # pubDt를 ISODate 형식으로 변환 (UTC, 00:00:00)
            pub_dt = article['date']
            if pub_dt.tzinfo is None:
                # timezone이 없으면 UTC로 설정
                pub_dt_utc = pytz.utc.localize(pub_dt.replace(hour=0, minute=0, second=0, microsecond=0))
            else:
                # timezone이 있으면 UTC로 변환
                pub_dt_utc = pub_dt.astimezone(pytz.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            
            # ContentsQueueVO 생성
            queueVO = ContentsQueueVO(
                contentOrgId=CONTENT_ORG_ID,
                cateId=CATE_ID,
                title=article['title'],
                url=article['url'],
                shortUrl=generate_random_string(5),
                pubDt=pub_dt_utc,  # ISODate 형식으로 저장됨
                collectDt=collect_dt,  # ISODate 형식으로 저장됨
                collectKeyword=COLLECT_KEYWORD
                # _id는 MongoDB가 자동 생성
            )
            
            # MongoDB에 저장
            BaseQueryService.insert_one(queueVO)
            
            # 저장된 문서의 _id 수집
            if queueVO._id:
                inserted_ids.append(str(queueVO._id))
            
            success_count += 1
            logger.info(f"[{idx}/{len(articles)}] ✅ 저장 성공: {article['title'][:50]}...")
            
        except Exception as e:
            error_count += 1
            logger.error(f"[{idx}/{len(articles)}] ❌ 저장 실패: {article.get('title', '')[:50]}... - {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    # 결과 요약
    logger.info("=" * 80)
    logger.info(f"📊 저장 결과 요약:")
    logger.info(f"  ✅ 성공: {success_count}건")
    logger.info(f"  ⏭️  건너뜀 (중복): {skip_count}건")
    logger.info(f"  ❌ 실패: {error_count}건")
    logger.info(f"  📝 전체: {len(articles)}건")
    logger.info(f"  🆔 저장된 문서 ID 수: {len(inserted_ids)}개")
    logger.info("=" * 80)
    
    return {
        "success": success_count,
        "skip": skip_count,
        "error": error_count,
        "total": len(articles),
        "inserted_ids": inserted_ids
    }


def save_ids_to_file(inserted_ids, csv_file_path, logger=None):
    """
    저장된 문서의 _id를 텍스트 파일로 저장
    
    Args:
        inserted_ids: 저장된 문서의 _id 리스트
        csv_file_path: 원본 CSV 파일 경로
        logger: 로거 객체 (선택)
    """
    if logger is None:
        logger = Logger().setup_logger(Logger.docker_collect_logger_name)
    
    # CSV 파일명에서 확장자 제거하고 파일명만 추출
    csv_filename = os.path.basename(csv_file_path)
    csv_name_without_ext = os.path.splitext(csv_filename)[0]
    
    # 출력 파일 경로 생성
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, f"test_ids_{csv_name_without_ext}.txt")
    
    # _id를 텍스트 파일로 저장
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for doc_id in inserted_ids:
                f.write(f"{doc_id}\n")
        
        logger.info(f"✅ 저장된 문서 ID를 파일에 저장했습니다: {output_file}")
        logger.info(f"  - 총 {len(inserted_ids)}개의 ID 저장")
    except Exception as e:
        logger.error(f"❌ ID 파일 저장 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())


def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("사용법: python3 import_csv_to_contents_queue.py <csv_file_path>")
        print("예시: python3 import_csv_to_contents_queue.py article_202511_fixed.csv")
        sys.exit(1)
    
    csv_file_path = sys.argv[1]
    
    # 파일 존재 확인
    if not os.path.exists(csv_file_path):
        print(f"❌ 오류: 파일을 찾을 수 없습니다: {csv_file_path}")
        sys.exit(1)
    
    # Logger 초기화
    logger_obj = Logger()
    logger = logger_obj.setup_logger(logger_obj.docker_collect_logger_name)
    
    logger.info("=" * 80)
    logger.info("CSV 파일에서 contents_queue로 데이터 가져오기 시작")
    logger.info(f"📁 파일 경로: {csv_file_path}")
    logger.info("=" * 80)
    
    try:
        # CSV 파일 읽기
        articles = read_csv_file(csv_file_path)
        
        if not articles:
            logger.warning("⚠️  읽을 수 있는 기사가 없습니다.")
            return
        
        # contents_queue에 저장
        result = save_to_contents_queue(articles, logger)
        
        logger.info("✅ 저장 작업 완료!")
        
        # 저장된 문서의 _id를 텍스트 파일로 저장
        if result.get("inserted_ids"):
            save_ids_to_file(result["inserted_ids"], csv_file_path, logger)
        
        # 2025년 11월 기사 건수 조회 및 출력
        logger.info("")
        logger.info("=" * 80)
        logger.info("📊 2025년 11월 기사 건수 조회")
        logger.info("=" * 80)
        
        stats = get_article_count_by_date(year=2025, month=11, logger=logger)
        
        # 날짜별 건수 출력
        logger.info("")
        logger.info("📅 날짜별 기사 건수:")
        if stats["daily"]:
            for date_str in sorted(stats["daily"].keys()):
                count = stats["daily"][date_str]
                logger.info(f"  {date_str}: {count}건")
        else:
            logger.info("  조회된 기사가 없습니다.")
        
        # 전체 건수 출력
        logger.info("")
        logger.info(f"📊 2025년 11월 전체 기사 건수: {stats['total']}건")
        logger.info("=" * 80)
        
        logger.info("✅ 모든 작업 완료!")
        
    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()

