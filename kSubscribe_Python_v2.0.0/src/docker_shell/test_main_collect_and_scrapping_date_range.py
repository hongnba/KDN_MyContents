# docker_shell/main_collect_and_scrapping_date_range.py

from datetime import datetime, timedelta
import sys
import pytz

from docker_collect.test_collect_date_range_2 import DateRangeCollectMain
from docker_scraping.contents_scraping_ollama_trafilaura import ContentsScrapingOllamaTrafilaura
from ksubscribe_server.analysis.ollama_alive import OllamaAlive
from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService
from ksubscribe_share.db.service.contentsService import ContentsService
from ksubscribe_share.db.service.statsService import StatsService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.service.calendarService import CalendarService
from ksubscribe_share.logger import Logger
import ksubscribe_share.config as Conf


if __name__ == "__main__":
    logger = Logger().setup_logger(Logger.docker_scraping_result_logger_name)
    
    # 수집 기간 설정: 2025년 11월 1일 ~ 11월 30일
    seoul_tz = pytz.timezone('Asia/Seoul')
    start_date = seoul_tz.localize(datetime(2025, 11, 1, 0, 0, 0))
    end_date = seoul_tz.localize(datetime(2025, 11, 30, 23, 59, 59))
    
    logger.info("=" * 100)
    logger.info("=== 특정 기간 전체 파이프라인 실행 ===")
    logger.info(f"수집 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    logger.info("=" * 100)
    
    checker = None
    
    try:
        # ====================================================================
        # 1. docker collect (특정 기간 수집)
        # ====================================================================
        logger.info("\n" + "=" * 100)
        logger.info("=== 1단계: Docker Collect (특정 기간 수집) ===")
        logger.info("=" * 100)
        
        try:
            contents_org_service = ContentsOrgService()
            orgs = contents_org_service.find_all()
            logger.info(f"총 {len(orgs)}개 기관 수집 예정")
            
            for org in orgs:
                try:
                    logger.info(f"\n{'='*80}")
                    logger.info(f"기관 수집 시작: {org.orgName}({org.orgId})")
                    logger.info(f"{'='*80}")
                    
                    collector = DateRangeCollectMain(org.orgId, start_date, end_date)
                    collector.collect_for_date_range()
                    
                except Exception as e:
                    logger.error(f"기관 {org.orgId} 수집 중 오류: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Docker collect 오류: {str(e)}")
            pass

        # ====================================================================
        # 2. Queue의 중복성 검사
        # ====================================================================
        logger.info("\n" + "=" * 100)
        logger.info("=== 2단계: Queue 중복성 검사 ===")
        logger.info("=" * 100)
        
        try:
            ContentsQueueService().removeDuplicateUrl()
            logger.info("Queue 중복성 검사 완료")
        except Exception as e:
            logger.error(f"Queue 중복성 검사 오류: {str(e)}")
            pass

        # ====================================================================
        # 3. docker scraping (Queue에 있는 데이터 스크래핑 및 분석)
        # ====================================================================
        logger.info("\n" + "=" * 100)
        logger.info("=== 3단계: Docker Scraping (Queue 데이터 처리) ===")
        logger.info("=" * 100)
        
        try:
            # Start ollama alive thread
            checker = OllamaAlive(op_mode="docker_server", keep_alive=False)
            checker.start_thread()
            
            # Docker scraping
            contentsScrapingOllamaTrafilaura = ContentsScrapingOllamaTrafilaura()
            logger.info("contentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama()")
            contentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama()
            
        except Exception as e:
            logger.error(f"Scraping 오류: {e}")

        # ====================================================================
        # 4. 두 번째 scraping (특정 기간 내의 미처리 데이터 재처리)
        # ====================================================================
        logger.info("\n" + "=" * 100)
        logger.info("=== 4단계: 두 번째 Scraping (특정 기간 내 미처리 데이터 재처리) ===")
        logger.info("=" * 100)
        
        try:
            logger.info("contentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama() - second time....")
            contentsScrapingOllamaTrafilaura = ContentsScrapingOllamaTrafilaura()
            
            # 특정 기간 내의 데이터를 재처리하기 위해 queue를 다시 확인
            # (실제로는 queue에 남아있는 데이터를 처리)
            contentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama()
            
        except Exception as e:
            logger.error(f"Second scraping error: {str(e)}")

        # ====================================================================
        # 5. 통계 계산 (특정 기간에 대한 통계)
        # ====================================================================
        logger.info("\n" + "=" * 100)
        logger.info("=== 5단계: 통계 계산 (특정 기간) ===")
        logger.info("=" * 100)
        
        try:
            stats_service = StatsService()
            calendar_service = CalendarService()
            contents_org_service = ContentsOrgService()
            
            # 모든 기관 조회
            orgs = contents_org_service.find_all()
            logger.info(f"Found {len(orgs)} organizations")
            
            # 특정 기간에 대한 날짜 범위 설정
            # 일별: 2025-11-01
            day_start = datetime(2025, 11, 1, 0, 0, 0, tzinfo=seoul_tz)
            day_end = datetime(2025, 11, 1, 23, 59, 59, 999999, tzinfo=seoul_tz)
            
            # 주별: 2025-11-01 ~ 2025-11-07
            week_start = datetime(2025, 11, 1, 0, 0, 0, tzinfo=seoul_tz)
            week_end = datetime(2025, 11, 7, 23, 59, 59, 999999, tzinfo=seoul_tz)
            
            # 월별: 2025-11-01 ~ 2025-11-30
            month_start = datetime(2025, 11, 1, 0, 0, 0, tzinfo=seoul_tz)
            month_end = datetime(2025, 11, 30, 23, 59, 59, 999999, tzinfo=seoul_tz)
            
            for org in orgs:
                try:
                    org_id = org.orgId
                    logger.info(f"Processing statistics for {org_id}...")
                    
                    # # 일별 통계 계산
                    # try:
                    #     stats = stats_service.count_for_period(org_id, 'day', day_start, day_end)
                    #     logger.info(f"  - day: {stats._id}")
                    # except Exception as e:
                    #     logger.error(f"  - day: Error - {str(e)}")

                    # 수정된 코드 (11월 전체 일별 통계 계산)
                    # 일별 통계 계산 (11월 1일 ~ 30일 각 날짜별로)
                    for day in range(1, 31):  # 11월 1일 ~ 30일
                        day_start = datetime(2025, 11, day, 0, 0, 0, tzinfo=seoul_tz)
                        day_end = datetime(2025, 11, day, 23, 59, 59, 999999, tzinfo=seoul_tz)
                        
                        try:
                            stats = stats_service.count_for_period(org_id, 'day', day_start, day_end)
                            logger.info(f"  - day {day}: {stats._id}")
                        except Exception as e:
                            logger.error(f"  - day {day}: Error - {str(e)}")
                    
                    # 주별 통계 계산
                    try:
                        stats = stats_service.count_for_period(org_id, 'week', week_start, week_end)
                        logger.info(f"  - week: {stats._id}")
                    except Exception as e:
                        logger.error(f"  - week: Error - {str(e)}")
                    
                    # 월별 통계 계산
                    try:
                        stats = stats_service.count_for_period(org_id, 'month', month_start, month_end)
                        logger.info(f"  - month: {stats._id}")
                    except Exception as e:
                        logger.error(f"  - month: Error - {str(e)}")
                    
                    # 캘린더 결과 계산 (현재는 현재 월 기준이지만, 특정 월 데이터 조회 가능)
                    try:
                        # CalendarService는 현재 월 기준이므로, 특정 월 데이터를 조회하려면
                        # get_daily_results_from_db를 사용하거나 별도 구현 필요
                        calendar_results = calendar_service.get_daily_results_from_db(org_id, "2025-11")
                        if calendar_results:
                            logger.info(f"  - calendar: {len(calendar_results.get('positiveResult', {}))} days")
                        else:
                            logger.info(f"  - calendar: 데이터 없음")
                    except Exception as e:
                        logger.error(f"  - calendar: Error - {str(e)}")
                        
                except Exception as e:
                    logger.error(f"Error processing {org.orgId}: {str(e)}")
            
            logger.info("=== Statistics calculation complete ===")
            
        except Exception as e:
            logger.error(f"Error in statistics calculation: {str(e)}")

    finally:
        # Ollama 스레드 종료
        if checker:
            checker.stop_thread()
    
    logger.info("\n" + "=" * 100)
    logger.info("=== 특정 기간 전체 파이프라인 완료 ===")
    logger.info("=" * 100)