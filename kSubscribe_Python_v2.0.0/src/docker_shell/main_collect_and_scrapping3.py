from datetime import datetime, timedelta
import sys
from typing import List
import pytz

from docker_collect.collect_v2 import DockerCollectMain
from docker_scraping.contents_scraping_ollama_trafilaura import ContentsScrapingOllamaTrafilaura
from ksubscribe_server.analysis.ollama_alive import OllamaAlive
from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService
from ksubscribe_share.db.service.contentsService import ContentsService
from ksubscribe_share.db.service.statsService import StatsService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.service.calendarService import CalendarService
from ksubscribe_share.logger import Logger
import ksubscribe_share.config as Conf


def process_by_last_suc_ymd():
    """
    contents_org collection의 lastSucYMD를 참고하여 
    main_collect_and_scrapping.py 실행 시점과의 기간 차이를 계산하고,
    그 기간에 해당하는 기사와 공고를 수집한 후 stats를 저장합니다.
    """
    logger = Logger().setup_logger(Logger.docker_scraping_result_logger_name)
    logger.info("=== lastSucYMD 기반 수집 및 분석 시작 ===")
    
    try:
        # 1. docker collect (lastSucYMD 기반으로 자동 수집)
        logger.info("=== Step 1: Docker Collect (lastSucYMD 기반) ===")
        try:
            dockerCollectMain = DockerCollectMain()
            logger.info("dockerCollectMain.distribute() 실행")
            dockerCollectMain.distribute()
            logger.info(f"수집 완료 - 성공: {dockerCollectMain.success_cnt}, 실패: {dockerCollectMain.fail_cnt}")
        except Exception as e:
            logger.error(f"Docker collect 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # 2. Queue의 중복성 검사
        logger.info("=== Step 2: Queue 중복성 검사 ===")
        try:
            ContentsQueueService().removeDuplicateUrl()
            logger.info("Queue 중복성 검사 완료")
        except Exception as e:
            logger.error(f"Queue 중복성 검사 오류: {e}")
        
        # 3. start ollama alive thread
        logger.info("=== Step 3: Ollama Alive Thread 시작 ===")
        checker = OllamaAlive(op_mode="docker_server", keep_alive=False)
        checker.start_thread()
        logger.info("Ollama alive thread started")
        
        # 4. docker scrapping
        logger.info("=== Step 4: Docker Scraping 및 분석 ===")
        try:
            contentsScrapingOllamaTrafilaura = ContentsScrapingOllamaTrafilaura()
            logger.info("contentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama() 실행")
            contentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama()
            logger.info(f"스크래핑 완료 - 성공: {contentsScrapingOllamaTrafilaura.scrapping_cnt_for_once}, 분석 성공: {contentsScrapingOllamaTrafilaura.analysis_cnt_for_once}")
        except Exception as e:
            logger.error(f"Scraping 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # 5. 7시간 전 ~ 지금까지의 contents 중 ollama 요약 안된 데이터 다시 요약
        logger.info("=== Step 5: 재요약 처리 (7시간 전 ~ 현재) ===")
        try:
            logger.info("contentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama() - second time....")
            contentsScrapingOllamaTrafilaura = ContentsScrapingOllamaTrafilaura()
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(hours=7)
            logger.info(f"재요약 기간: {start_date} ~ {end_date}")
            contentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama()
        except Exception as e:
            logger.error(f"Second scraping error: {str(e)}")
        
        # 6. Calculate statistics for all organizations
        logger.info("=== Step 6: Statistics 계산 및 저장 ===")
        try:
            stats_service = StatsService()
            calendar_service = CalendarService()
            contents_org_service = ContentsOrgService()
            
            # Get all organizations
            orgs = contents_org_service.find_all()
            logger.info(f"총 {len(orgs)}개 기관 발견")
            
            for org in orgs:
                try:
                    org_id = org.orgId
                    logger.info(f"기관 통계 처리 중: {org.orgName}({org_id})...")
                    
                    # Calculate statistics for each period (day, week, month)
                    for period in ['day', 'week', 'month']:
                        try:
                            # Calculate main statistics
                            stats = stats_service.count_for_period(org_id, period)
                            logger.info(f"  - {period} 통계 저장 완료: {stats._id}")
                            
                            # Calculate calendar results
                            calendar_results = calendar_service.get_calendar_results(org_id)
                            logger.info(f"  - calendar: 긍정 {len(calendar_results['positiveResult'])}일")
                            
                        except Exception as e:
                            logger.error(f"  - {period} 통계 오류: {str(e)}")
                            
                except Exception as e:
                    logger.error(f"기관 {org.orgId} 처리 오류: {str(e)}")
            
            logger.info("=== Statistics 계산 완료 ===")
            
        except Exception as e:
            logger.error(f"Statistics 계산 오류: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        
        checker.stop_thread()
        logger.info("=== 전체 프로세스 완료 ===")
        
    except Exception as e:
        logger.error(f"전체 프로세스 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        if 'checker' in locals():
            checker.stop_thread()


if __name__ == "__main__":
    """
    사용법:
    python main_collect_and_scrapping3.py
    
    이 스크립트는:
    1. contents_org collection의 lastSucYMD를 확인
    2. 실행 시점과 lastSucYMD의 기간 차이를 계산하여 그 기간만 수집
    3. 수집된 데이터를 스크래핑 및 분석
    4. 오늘 날짜 기준으로 daily_stats, weekly_stats, monthly_stats 저장
    
    주의: Stats 저장 시에는 sucYMD가 영향을 미치지 않습니다.
          Stats는 pubDt 기준으로 contents collection을 조회합니다.
    """
    process_by_last_suc_ymd()

