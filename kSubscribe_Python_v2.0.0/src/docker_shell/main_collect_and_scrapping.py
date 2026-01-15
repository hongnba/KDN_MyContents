    
    
from datetime import datetime,timedelta
import sys
import os
import pytz

# huggingface/tokenizers 경고 제거
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

from docker_collect.collect_v2 import DockerCollectMain
from docker_scraping.contents_scraping_ollama_trafilaura import ContentsScrapingOllamaTrafilaura
from ksubscribe_server.analysis.ollama_alive import OllamaAlive
from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService
from ksubscribe_share.db.service.contentsService import ContentsService
from ksubscribe_share.db.service.statsService import StatsService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.service.calendarService import CalendarService
from ksubscribe_share.logger import Logger
#from ksubscribe_share import config as Conf
import ksubscribe_share.config as Conf
 
        
if __name__ == "__main__":

    # Check if we should process only today.json URLs
    process_today_json_only = len(sys.argv) > 1 and sys.argv[1] == "--today-json"
    
    if process_today_json_only:
        logger = Logger().setup_logger(Logger.docker_scraping_result_logger_name)
        logger.info("=== Processing URLs from today.json only ===")
        try:
            # Start ollama alive thread
            checker = OllamaAlive(op_mode="docker_server",keep_alive=False)
            checker.start_thread()
            
            # Process articles from today.json and save to contents_backup
            contentsScrapingOllamaTrafilaura = ContentsScrapingOllamaTrafilaura()
            logger.info("contentsScrapingOllamaTrafilaura.process_articles_from_today_json()")
            contentsScrapingOllamaTrafilaura.process_articles_from_today_json()
            
            checker.stop_thread()
            logger.info("=== Processing complete ===")
            
        except Exception as e:
            logger.error(f"Error processing today.json: {e}")
            if 'checker' in locals():
                checker.stop_thread()
    else:
        logger = Logger().setup_logger(Logger.docker_scraping_result_logger_name)
        logger.info("=== Running full pipeline (collect + scrape) ===")

        try:
            # 1. docker collect
            dockerCollectMain = DockerCollectMain()
            logger.info("dockerCollectMain.distribute()")
            dockerCollectMain.distribute()
            
        except Exception as e:
            pass 

        try:
            #Queue의 중복성 검사   
            ContentsQueueService().removeDuplicateUrl() 
        except Exception as e:
            pass 

        try:
            # 2. start ollama alive thread
            checker = OllamaAlive(op_mode="docker_server",keep_alive=False)
            checker.start_thread()    
            # 3. docker scrapping
            contentsScrapingOllamaTrafilaura = ContentsScrapingOllamaTrafilaura()
            logger.info("contentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama()")
            contentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama()
        except Exception as e:
            logger.error(f"error : {e}") #error : Message: Service /root/.wdm/drivers/chromedriver/linux64/114.0.5735.90/chromedriver unexpectedly exited. Status code was: 127

        # try:
        #     #contents의 중복성 검사 
        #     logger = Logger().setup_logger(Logger.docker_scraping_result_logger_name)    
        #     ContentsService().removeDuplicateUrl(logger)
        #     pass 
        # except Exception as e:
        #     pass  
        try:
            #7시간전 ~ 지금 까지의 contents 중 ollama 요약 안된 데이터 다시 요약(collectDT 기준)
            logger.info("contentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama() - second time....")
            contentsScrapingOllamaTrafilaura = ContentsScrapingOllamaTrafilaura()
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(hours=7)

            #코드 재개발 필요함 
            contentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama()#(start_date=start_date,end_date=end_date,is_all=False)
        except Exception as e:
            logger.error(f"Second scraping error: {str(e)}")

        try:
            # 4. Calculate statistics for all organizations
            logger = Logger().setup_logger(Logger.docker_scraping_result_logger_name)
            logger.info("=== Calculating statistics ===")
            
            stats_service = StatsService()
            calendar_service = CalendarService()
            contents_org_service = ContentsOrgService()
            
            # 20260115: 0~6시 첫 크론잡 실행 시 전날과 당일 stats 생성
            kst = pytz.timezone('Asia/Seoul')
            now_kst = datetime.now(kst)
            is_early_morning = now_kst.hour < 6
            
            # Get all organizations
            orgs = contents_org_service.find_all()
            logger.info(f"Found {len(orgs)} organizations")
            
            for org in orgs:
                try:
                    org_id = org.orgId
                    logger.info(f"Processing statistics for {org_id}...")
                    
                    # Calculate statistics for each period
                    for period in ['day', 'week', 'month']:
                        try:
                            if is_early_morning:
                                curr_start, curr_end = stats_service._get_period_dates(period)

                                # 전날 stats 생성
                                if period == 'day':
                                    # 하루 전: 전날 00:00 ~ 23:59
                                    prev_start = curr_start - timedelta(days=1)
                                    prev_end = curr_end - timedelta(days=1)
                                    
                                elif period == 'week':
                                    # 일주일 전: 7일 전 00:00 ~ 전날 23:59
                                    prev_start = curr_start - timedelta(days=7)
                                    prev_end = curr_end - timedelta(days=7)
                                
                                else:  # month
                                    # 한 달 전: 30일 전 00:00 ~ 전날 23:59
                                    prev_start = curr_start - timedelta(days=30)
                                    prev_end = curr_end - timedelta(days=30)
                                
                                # ✅ 전날 stats 생성 (타임존 정보 포함된 datetime 전달)
                                stats_prev = stats_service.count_for_period(org_id, period, prev_start, prev_end)
                                logger.info(f"  - {period} (prev): {stats_prev._id}")
                                
                                # ✅ 당일 stats 생성 (_get_period_dates()가 자동 계산)
                                stats_curr = stats_service.count_for_period(org_id, period)
                                logger.info(f"  - {period} (curr): {stats_curr._id}")

                            else:
                                # 일반 시간대: 당일 stats만 생성
                                stats = stats_service.count_for_period(org_id, period)
                                logger.info(f"  - {period}: {stats._id}")
                            
                            # Calculate calendar results
                            calendar_results = calendar_service.get_calendar_results(org_id)
                            logger.info(f"  - calendar: {len(calendar_results['positiveResult'])} days")
                            
                        except Exception as e:
                            logger.error(f"  - {period}: Error - {str(e)}")
                            
                except Exception as e:
                    logger.error(f"Error processing {org.orgId}: {str(e)}")
            
            logger.info("=== Statistics calculation complete ===")
            
        except Exception as e:
            logger.error(f"Error in statistics calculation: {str(e)}")

        checker.stop_thread()
    


        