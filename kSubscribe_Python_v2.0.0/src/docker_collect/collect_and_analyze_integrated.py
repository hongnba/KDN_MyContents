#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 수집 및 분석 스크립트

목적:
    - 특정 기관과 날짜 범위에 대해 기사 수집 및 LLM 분석을 통합적으로 수행
    - 3가지 모드 지원: collect_only, analyze_only, collect_and_analyze

사용법:
    # 수집만 수행
    python collect_and_analyze_integrated.py --mode collect --org-id A0010 --start-date 2025-11-01 --end-date 2025-11-30
    
    # 분석만 수행 (contents_queue에서 pubDt 기준으로 조회)
    python collect_and_analyze_integrated.py --mode analyze --org-id A0010 --start-date 2025-11-01 --end-date 2025-11-30
    
    # 수집 후 분석
    python collect_and_analyze_integrated.py --mode collect_and_analyze --org-id A0010 --start-date 2025-11-01 --end-date 2025-11-30
    
    # 설정 파일 사용
    python collect_and_analyze_integrated.py --config config.json

주의사항:
    - 날짜 범위는 pubDt (기사 발행일) 기준입니다.
    - analyze 모드는 contents_collect_history에서 URL을 추출하여 contents_queue에서 조회합니다.
    - collect 모드는 test_collect_date_range.py의 로직을 사용합니다.
    - analyze 모드는 test_llm_evaluation.py의 로직을 사용합니다.
"""

import os
import sys
import argparse
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pytz
import pymongo
from bson import ObjectId

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ksubscribe_share.logger import Logger
from docker_collect.driver_utils import get_driver
from docker_collect.error_handler import ErrorHandler, OpenAPIErrorHandler, SeleniumErrorHandler
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from docker_collect.rss_collector import get_contents_by_rss
from docker_collect.openapi_collector import get_g2b_nara, get_naver_news
from docker_collect.selenium_collector import get_contents_by_selenium_main, get_kepco_news
from docker_scraping.web_loader import WebLoaderV3
from docker_scraping.contents_scraping_ollama_trafilaura import ContentsScrapingOllamaTrafilaura
from ksubscribe_server.analysis.ollama_alive import OllamaAlive
from ksubscribe_server.analysis.analysis_ollama_generate import AnalysisOllamaGenerateCall
from ksubscribe_share.db.service.contentsService import ContentsService
from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
from ksubscribe_share.db.dbmodelV2.contentsCollectHistoryVO import ContentsCollectHistoryVO
import ksubscribe_share.config as CONF


class DateRangeCollectMain:
    """
    특정 날짜 범위에 대한 기사 수집을 위한 클래스
    (test_collect_date_range.py에서 추출)
    """
    
    def __init__(self, target_org_id: str, start_date: datetime, end_date: datetime, logger):
        """
        Args:
            target_org_id: 수집할 기관 ID (예: "A0010" - 한국전력)
            start_date: 수집 시작 날짜 (datetime, timezone-aware)
            end_date: 수집 종료 날짜 (datetime, timezone-aware)
            logger: Logger 인스턴스
        """
        self.target_org_id = target_org_id
        self.start_date = start_date
        self.end_date = end_date
        self.logger = logger
        
        self.contentsOrgService = ContentsOrgService()
        self.success_cnt = 0
        self.fail_cnt = 0
        self.total_cnt = 0
        
        # 원래 lastSucYMD 값을 저장 (복원용)
        self.original_last_suc_ymd = {}
    
    def _backup_and_modify_last_suc_ymd(self, org, category):
        """카테고리의 lastSucYMD를 백업하고 수집 기간에 맞게 수정"""
        key = f"{org.orgId}_{category.cateId}"
        
        if key not in self.original_last_suc_ymd:
            self.original_last_suc_ymd[key] = category.lastSucYMD
        
        # 수집 시작 날짜의 하루 전으로 설정
        category.lastSucYMD = self.start_date - timedelta(days=1)
        
        self.logger.info(
            f"  [날짜 수정] {org.orgName}({org.orgId}) - {category.cateName}({category.cateId}): "
            f"lastSucYMD를 {category.lastSucYMD.strftime('%Y-%m-%d')}로 임시 설정"
        )
    
    def _restore_last_suc_ymd(self, org, category):
        """카테고리의 lastSucYMD를 원래 값으로 복원"""
        key = f"{org.orgId}_{category.cateId}"
        if key in self.original_last_suc_ymd:
            category.lastSucYMD = self.original_last_suc_ymd[key]
            self.logger.info(
                f"  [날짜 복원] {org.orgName}({org.orgId}) - {category.cateName}({category.cateId}): "
                f"lastSucYMD를 원래 값으로 복원"
            )
    
    def collect_for_date_range(self):
        """지정된 날짜 범위에 대해 기사 수집 실행"""
        self.logger.info("=" * 100)
        self.logger.info(f"특정 날짜 범위 수집 시작")
        self.logger.info(f"  기관 ID: {self.target_org_id}")
        self.logger.info(f"  수집 기간: {self.start_date.strftime('%Y-%m-%d')} ~ {self.end_date.strftime('%Y-%m-%d')}")
        self.logger.info("=" * 100)
        
        # IS_USE: True인 기관 목록 조회
        contentsOrgList = self.contentsOrgService.find_all()
        self.logger.info(f"총 {len(contentsOrgList)}개 기관 조회 완료")
        
        # 대상 기관만 필터링
        target_org = None
        for org in contentsOrgList:
            if org.orgId == self.target_org_id:
                target_org = org
                break
        
        if not target_org:
            self.logger.error(f"기관 ID '{self.target_org_id}'를 찾을 수 없습니다.")
            return
        
        self.logger.info(f"대상 기관: {target_org.orgName}({target_org.orgId}), 카테고리 수: {len(target_org.categoryList)}")
        
        if len(target_org.categoryList) == 0:
            self.logger.warning(f"  카테고리가 없어서 종료합니다.")
            return
        
        # 나라장터 키워드 조회 (필요한 경우)
        g2b_keywords = self.contentsOrgService.findOrgKeywords("A0004")
        
        driver = get_driver()
        
        try:
            # 각 카테고리별로 수집
            for category in target_org.categoryList:
                self.logger.info(f"\n카테고리 처리: {category.cateName}({category.cateId})")
                
                # lastSucYMD 백업 및 수정
                self._backup_and_modify_last_suc_ymd(target_org, category)
                
                result = None
                collect_datetime = datetime.utcnow().replace(tzinfo=pytz.utc)
                err_handler = ErrorHandler()
                
                try:
                    # SELENIUM
                    if category.COL_METHOD == "C0003":
                        if target_org.orgId == "A0010" and category.cateId == "B0001":
                            result = get_kepco_news(driver, target_org, category)
                        else:
                            result = get_contents_by_selenium_main(driver, target_org, category)
                        err_handler.set_processor(SeleniumErrorHandler())
                    
                    # RSS
                    elif category.COL_METHOD == "C0001":
                        result = get_contents_by_rss(target_org, category)
                    
                    # OPEN API
                    else:
                        if target_org.orgId == "A0004" and category.cateId == "B0005":
                            result = get_g2b_nara(target_org, category, g2b_keywords)
                            err_handler.set_processor(OpenAPIErrorHandler())
                        else:
                            result = get_naver_news("A0026", target_org, category)
                            err_handler.set_processor(OpenAPIErrorHandler())
                
                except Exception as e:
                    self.logger.error(f"수집 함수 예외: {target_org.orgName}({target_org.orgId}) - {category.cateName}({category.cateId}): {e}")
                    result = {"success": False, "error": str(e)}
                
                # lastSucYMD 복원
                self._restore_last_suc_ymd(target_org, category)
                
                if not result:
                    self.logger.warning(f"result가 None: {target_org.orgName}({target_org.orgId}) - {category.cateName}({category.cateId})")
                    continue
                
                if result["success"]:
                    self.success_cnt += 1
                else:
                    error_info = err_handler.handle(result["error"])
                    self.fail_cnt += 1
                    self.logger.error(f"수집 실패: {error_info}")
                
                self.total_cnt += 1
        
        finally:
            driver.quit()
        
        self.logger.info("=" * 100)
        self.logger.info("특정 날짜 범위 수집 종료")
        self.logger.info(f"통계: 총 {self.total_cnt}건, 성공 {self.success_cnt}건, 실패 {self.fail_cnt}건")
        self.logger.info("=" * 100)


def get_urls_from_collect_history_by_pubdt(
    org_id: str,
    start_date: datetime,
    end_date: datetime,
    logger
) -> List[Dict]:
    """
    contents_collect_history에서 pubDt 기준으로 URL 목록 추출
    
    Args:
        org_id: 기관 ID
        start_date: 시작 날짜 (datetime, timezone-aware)
        end_date: 종료 날짜 (datetime, timezone-aware)
        logger: Logger 인스턴스
    
    Returns:
        URL 정보가 담긴 딕셔너리 리스트
        [{"url": "...", "title": "...", "pubDt": datetime, "cateId": "...", ...}, ...]
    """
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://ksubscribe_mongodb:27017')
    mongo_db = os.getenv('MONGO_DB', 'mycontents')
    client = None
    urls = []
    
    try:
        client = pymongo.MongoClient(mongo_uri)
        db = client.get_database(mongo_db)
        collection = db.get_collection('contents_collect_history')
        
        # UTC로 변환 (MongoDB는 UTC를 사용)
        start_utc = start_date.astimezone(pytz.utc)
        end_utc = end_date.astimezone(pytz.utc)
        
        # start_date와 end_date가 같은 날짜인지 확인
        is_single_date = start_date.date() == end_date.date()
        
        # end_date는 23:59:59까지 포함
        end_utc = end_utc.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # start_date도 해당 날짜의 00:00:00으로 설정 (단일 날짜 조회 시)
        if is_single_date:
            start_utc = start_utc.replace(hour=0, minute=0, second=0, microsecond=0)
            logger.info(f"contents_collect_history 조회: org_id={org_id}, 단일 날짜 조회: {start_date.date()} (00:00:00 ~ 23:59:59)")
        else:
            logger.info(f"contents_collect_history 조회: org_id={org_id}, pubDt 범위: {start_utc} ~ {end_utc}")
        
        # aggregation pipeline으로 pubDt 기준 필터링
        pipeline = [
            {
                "$match": {
                    "contentOrgId": org_id
                }
            },
            {
                "$unwind": "$contentCollectList"
            },
            {
                "$unwind": "$contentCollectList.collectionDetailList"
            },
            {
                "$match": {
                    "contentCollectList.collectionDetailList.pubDt": {
                        "$gte": start_utc,
                        "$lte": end_utc
                    }
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "url": "$contentCollectList.collectionDetailList.url",
                    "title": "$contentCollectList.collectionDetailList.title",
                    "pubDt": "$contentCollectList.collectionDetailList.pubDt",
                    "cateId": "$contentCollectList.categoryId",
                    "shortUrl": "$contentCollectList.collectionDetailList.shortUrl",
                    "collectKeyword": "$contentCollectList.collectionDetailList.collectKeyword"
                }
            }
        ]
        
        results = list(collection.aggregate(pipeline))
        
        logger.info(f"조회된 URL 수: {len(results)}건")
        
        for item in results:
            urls.append({
                "url": item.get("url"),
                "title": item.get("title"),
                "pubDt": item.get("pubDt"),
                "cateId": item.get("cateId"),
                "shortUrl": item.get("shortUrl"),
                "collectKeyword": item.get("collectKeyword")
            })
        
    except Exception as e:
        logger.error(f"❌ contents_collect_history 조회 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if client:
            client.close()
    
    return urls


def get_queue_documents_by_urls(
    urls: List[Dict],
    org_id: str,
    logger
) -> List[Dict]:
    """
    contents_queue에서 URL 목록으로 문서 조회
    
    Args:
        urls: URL 정보 딕셔너리 리스트
        org_id: 기관 ID
        logger: Logger 인스턴스
    
    Returns:
        contents_queue 문서 딕셔너리 리스트
    """
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://ksubscribe_mongodb:27017')
    mongo_db = os.getenv('MONGO_DB', 'mycontents')
    client = None
    docs = []
    
    try:
        client = pymongo.MongoClient(mongo_uri)
        db = client.get_database(mongo_db)
        collection = db.get_collection('contents_queue')
        
        # URL 목록 추출
        url_list = [item["url"] for item in urls if item.get("url")]
        
        if not url_list:
            logger.warning("조회할 URL이 없습니다.")
            return docs
        
        logger.info(f"contents_queue에서 {len(url_list)}개 URL 조회 시작")
        
        # URL로 문서 조회
        query = {
            "url": {"$in": url_list},
            "contentOrgId": org_id
        }
        
        cursor = collection.find(query)
        
        for doc in cursor:
            docs.append(doc)
        
        logger.info(f"조회된 문서 수: {len(docs)}건")
        
        # URL이 contents_queue에 없는 경우 로그 출력
        found_urls = {doc.get("url") for doc in docs}
        missing_urls = [url for url in url_list if url not in found_urls]
        
        if missing_urls:
            logger.warning(f"contents_queue에 없는 URL 수: {len(missing_urls)}건")
            logger.warning(f"예시 (최대 5개): {missing_urls[:5]}")
    
    except Exception as e:
        logger.error(f"❌ contents_queue 조회 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if client:
            client.close()
    
    return docs


def process_documents_for_analysis(
    docs: List[Dict],
    logger,
    keep_queue: bool = False
):
    """
    문서 스크래핑 및 LLM 분석 실행
    (test_llm_evaluation.py에서 추출 및 수정)
    
    Args:
        docs: 문서 딕셔너리 리스트
        logger: Logger 인스턴스
        keep_queue: True면 Queue에서 삭제하지 않음
    """
    if len(docs) == 0:
        logger.error("❌ 처리할 문서가 없습니다.")
        return
    
    logger.info(f"\n총 {len(docs)}개 문서 처리 시작\n")
    
    # 스크래핑 준비
    scraper = ContentsScrapingOllamaTrafilaura()
    
    # keep_queue 옵션 적용
    if keep_queue:
        scraper.delete_queue_after_processing = False
        logger.info("🔒 Queue 유지 모드: 처리 후에도 Queue에서 삭제하지 않습니다.")
    
    webLoader = WebLoaderV3()
    driver = get_driver()
    ollamaAnalysis = AnalysisOllamaGenerateCall()
    contents_service = ContentsService()
    
    results = []
    
    for idx, doc in enumerate(docs, 1):
        logger.info("=" * 80)
        logger.info(f"[{idx}/{len(docs)}] 처리 중")
        logger.info(f"ID: {doc.get('_id')}")
        logger.info(f"URL: {doc.get('url')}")
        logger.info(f"제목: {doc.get('title', 'N/A')}")
        logger.info("=" * 80)
        
        # MongoDB 문서 필드명을 ContentsQueueVO 파라미터명에 맞게 매핑
        def _get_field(d, *keys):
            for k in keys:
                if k in d and d.get(k) is not None:
                    return d.get(k)
            return None
        
        queue_doc = {
            'contentOrgId': _get_field(doc, 'contentOrgId', 'contentsOrgId', 'orgId', 'contents_org_id'),
            'cateId': _get_field(doc, 'cateId', 'categoryId', 'category_id', 'cate_id'),
            'title': _get_field(doc, 'title', 'newsTitle', 'headline'),
            'url': _get_field(doc, 'url', 'link', 'originalUrl'),
            'pubDt': _get_field(doc, 'pubDt', 'publishDate', 'pub_dt'),
            'collectDt': _get_field(doc, 'collectDt', 'collectedAt', 'collect_dt'),
            'collectKeyword': _get_field(doc, 'collectKeyword', 'keyword', 'collectKeywordList'),
            '_id': doc.get('_id'),
        }
        
        queue_vo = ContentsQueueVO(**queue_doc)
        
        start_time = datetime.now()
        
        try:
            # 스크래핑 및 LLM 분석
            isSuccess, text, title, contentsVO = scraper.scrape_content(queue_vo, webLoader, driver)
            
            if not isSuccess or not text:
                logger.error(f"크롤링 실패: {queue_vo.url}")
                results.append({
                    "url": queue_vo.url,
                    "success": False,
                    "error": "크롤링 실패"
                })
            else:
                # LLM 분석 실행
                logger.info(f"🚀 LLM 분석 실행: {queue_vo.url}")
                
                try:
                    # analysis_main returns tuple: (bool, ContentsMetaResult, ...)
                    analysis_result = ollamaAnalysis.analysis_main(
                        queueContent=queue_vo,
                        contentsRaw=contentsVO.contentsRaw,
                        org=contents_service.findOrg(queue_vo.contentOrgId),
                        category=contents_service.findOrgAndCategory(queue_vo.contentOrgId, queue_vo.cateId),
                        logger=logger
                    )
                    
                    success, meta_result, _ = analysis_result
                    
                    if success and meta_result:
                        contentsVO.contentsMeta = meta_result
                        contentsVO.metaSucYN = "Y"
                        
                        # MongoDB에 저장
                        BaseQueryService.insert_one(contentsVO)
                        
                        logger.info(f"✅ 분석 완료 및 저장: {queue_vo.url}")
                        results.append({
                            "url": queue_vo.url,
                            "success": True
                        })
                    else:
                        logger.error(f"❌ 분석 실패: {queue_vo.url}")
                        results.append({
                            "url": queue_vo.url,
                            "success": False,
                            "error": "LLM 분석 실패"
                        })
                
                except Exception as e:
                    logger.error(f"❌ 분석 중 예외 발생: {queue_vo.url}")
                    logger.error(f"예외 내용: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    results.append({
                        "url": queue_vo.url,
                        "success": False,
                        "error": str(e)
                    })
        
        except Exception as e:
            logger.error(f"❌ 처리 중 예외 발생: {queue_vo.url}")
            logger.error(f"예외 내용: {e}")
            import traceback
            logger.error(traceback.format_exc())
            results.append({
                "url": queue_vo.url,
                "success": False,
                "error": str(e)
            })
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"처리 시간: {elapsed:.2f}초\n")
    
    driver.quit()
    
    # 결과 통계
    success_count = sum(1 for r in results if r.get("success"))
    fail_count = len(results) - success_count
    
    logger.info("=" * 100)
    logger.info("분석 완료")
    logger.info(f"통계: 총 {len(results)}건, 성공 {success_count}건, 실패 {fail_count}건")
    logger.info("=" * 100)


def parse_date(date_str: str) -> datetime:
    """
    날짜 문자열을 datetime 객체로 변환
    
    Args:
        date_str: 날짜 문자열 (예: "2025-11-01", "2025/11/01", "20251101")
    
    Returns:
        timezone-aware datetime 객체 (Asia/Seoul)
    """
    seoul_tz = pytz.timezone('Asia/Seoul')
    
    # 다양한 형식 지원
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y%m%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S"
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return seoul_tz.localize(dt)
        except ValueError:
            continue
    
    raise ValueError(f"날짜 형식을 인식할 수 없습니다: {date_str}")


def load_config(config_path: str) -> dict:
    """설정 파일 로드"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def parse_arguments():
    """명령줄 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="통합 수집 및 분석 스크립트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 수집만 수행
  python collect_and_analyze_integrated.py --mode collect --org-id A0010 --start-date 2025-11-01 --end-date 2025-11-30
  
  # 분석만 수행
  python collect_and_analyze_integrated.py --mode analyze --org-id A0010 --start-date 2025-11-01 --end-date 2025-11-30
  
  # 수집 후 분석
  python collect_and_analyze_integrated.py --mode collect_and_analyze --org-id A0010 --start-date 2025-11-01 --end-date 2025-11-30
  
  # 설정 파일 사용
  python collect_and_analyze_integrated.py --config config.json
        """
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        choices=['collect', 'analyze', 'collect_and_analyze'],
        required=False,
        help='실행 모드: collect (수집만), analyze (분석만), collect_and_analyze (수집 후 분석)'
    )
    
    parser.add_argument(
        '--org-id',
        type=str,
        help='기관 ID (예: A0010)'
    )
    
    parser.add_argument(
        '--start-date',
        type=str,
        help='시작 날짜 (예: 2025-11-01)'
    )
    
    parser.add_argument(
        '--end-date',
        type=str,
        help='종료 날짜 (예: 2025-11-30)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='설정 파일 경로 (JSON 형식)'
    )
    
    parser.add_argument(
        '--keep-queue',
        action='store_true',
        help='분석 후 Queue에서 삭제하지 않음 (재실행 가능)'
    )
    
    return parser.parse_args()


def main():
    """메인 실행 함수"""
    args = parse_arguments()
    
    # 설정 파일이 있으면 우선 사용
    if args.config:
        config = load_config(args.config)
        mode = config.get('mode', 'collect_and_analyze')
        org_id = config.get('org_id', 'A0010')
        start_date_str = config.get('start_date')
        end_date_str = config.get('end_date')
        keep_queue = config.get('keep_queue', False)
    else:
        mode = args.mode or 'collect_and_analyze'
        org_id = args.org_id or 'A0010'
        start_date_str = args.start_date
        end_date_str = args.end_date
        keep_queue = args.keep_queue
    
    # 날짜 설정
    seoul_tz = pytz.timezone('Asia/Seoul')
    
    if start_date_str:
        start_date = parse_date(start_date_str)
    else:
        # 기본값: 2025년 11월 1일
        start_date = seoul_tz.localize(datetime(2025, 11, 1, 0, 0, 0))
    
    if end_date_str:
        end_date = parse_date(end_date_str)
        # 종료 날짜는 23:59:59로 설정
        end_date = end_date.replace(hour=23, minute=59, second=59)
    else:
        # 기본값: 2025년 11월 30일
        end_date = seoul_tz.localize(datetime(2025, 11, 30, 23, 59, 59))
    
    # 날짜 검증
    if start_date > end_date:
        print("❌ 오류: 시작 날짜가 종료 날짜보다 늦습니다.")
        sys.exit(1)
    
    # Logger 초기화
    logger_obj = Logger()
    logger = logger_obj.setup_logger(logger_obj.docker_collect_logger_name)
    
    # 실행 설정 출력
    logger.info("=" * 100)
    logger.info("통합 수집 및 분석 스크립트 실행")
    logger.info(f"  모드: {mode}")
    logger.info(f"  기관 ID: {org_id}")
    logger.info(f"  시작 날짜: {start_date.strftime('%Y-%m-%d')}")
    logger.info(f"  종료 날짜: {end_date.strftime('%Y-%m-%d')}")
    logger.info(f"  Queue 유지: {keep_queue}")
    logger.info("=" * 100)
    
    # OllamaAlive 스레드 시작 (분석 모드일 때만)
    ollama_thread = None
    if mode in ['analyze', 'collect_and_analyze']:
        ollama_thread = OllamaAlive()
        ollama_thread.start()
        logger.info("✅ OllamaAlive 스레드 시작")
    
    try:
        # 수집 모드
        if mode in ['collect', 'collect_and_analyze']:
            logger.info("\n" + "=" * 100)
            logger.info("1단계: 기사 수집 시작")
            logger.info("=" * 100)
            
            collector = DateRangeCollectMain(org_id, start_date, end_date, logger)
            collector.collect_for_date_range()
            
            logger.info("✅ 수집 완료\n")
        
        # 분석 모드
        if mode in ['analyze', 'collect_and_analyze']:
            logger.info("\n" + "=" * 100)
            logger.info("2단계: LLM 분석 시작")
            logger.info("=" * 100)
            
            # contents_collect_history에서 pubDt 기준으로 URL 추출
            logger.info("contents_collect_history에서 URL 추출 중...")
            urls = get_urls_from_collect_history_by_pubdt(org_id, start_date, end_date, logger)
            
            if not urls:
                logger.warning("⚠️ 조회된 URL이 없습니다. 분석을 건너뜁니다.")
            else:
                # contents_queue에서 문서 조회
                logger.info("contents_queue에서 문서 조회 중...")
                docs = get_queue_documents_by_urls(urls, org_id, logger)
                
                if not docs:
                    logger.warning("⚠️ contents_queue에 해당 문서가 없습니다. 분석을 건너뜁니다.")
                else:
                    # LLM 분석 실행
                    process_documents_for_analysis(docs, logger, keep_queue=keep_queue)
            
            logger.info("✅ 분석 완료\n")
    
    finally:
        # OllamaAlive 스레드 종료
        if ollama_thread:
            ollama_thread.stop()
            logger.info("✅ OllamaAlive 스레드 종료")
    
    logger.info("=" * 100)
    logger.info("전체 작업 완료")
    logger.info("=" * 100)


if __name__ == "__main__":
    main()

