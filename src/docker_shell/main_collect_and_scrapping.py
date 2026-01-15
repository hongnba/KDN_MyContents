    

from datetime import datetime,timedelta

from docker_collect.collect_v2 import DockerCollectMain
from docker_scraping.contents_scraping_ollama_trafilaura import ContentsScrapingOllamaTrafilaura
from ksubscribe_server.analysis.ollama_alive import OllamaAlive
from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService
from ksubscribe_share.db.service.contentsService import ContentsService
from ksubscribe_share.logger import Logger
#from ksubscribe_share import config as Conf
import ksubscribe_share.config as Conf

# 20251013 리자 추가 
from ksubscribe_share.db.service.statsService import StatsService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.service.calendarService import CalendarService
 
        
if __name__ == "__main__":

    try:
        # 1. docker collect
        dockerCollectMain = DockerCollectMain()
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
        contentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama()
    except Exception as e:
        pass 

    try:
        #contents의 중복성 검사 
        logger = Logger().setup_logger(Logger.docker_scraping_result_logger_name)    
        ContentsService().removeDuplicateUrl(logger)
        pass 
    except Exception as e:
        pass  
    try:
        #7시간전 ~ 지금 까지의 contents 중 ollama 요약 안된 데이터 다시 요약(collectDT 기준)
        contentsScrapingOllamaTrafilaura = ContentsScrapingOllamaTrafilaura()
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(hours=7)

        #코드 재개발 필요함 
        contentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama()#(start_date=start_date,end_date=end_date,is_all=False)
    except Exception as e:
        pass    
    
    # 20251013 리자 기능 추가: 일,주,월별 통계 계산 후 몽고 db 저장 로직 추가 
    try:
        # 모든 기관(organization)에 대한 통계 계산
        logger = Logger().setup_logger(Logger.docker_scraping_result_logger_name)
        logger.info("=== Calculating statistics ===")

        stats_service = StatsService()
        calendar_service = CalendarService()
        contents_org_service = ContentsOrgService()

        # 전체 기관 목록 조회
        orgs = contents_org_service.find_all()
        logger.info(f"총 {len(orgs)}개 기관 확인됨")

        for org in orgs:
            try:
                org_id = org.orgId
                logger.info(f"기관 {org_id} 통계 계산 시작...")
                
                # day, week, month 별 통계 계산 시도
                for period in ['day', 'week', 'month']:
                    try:
                        # 주기별(일,주,월) 메인 통계 계산
                        stats = stats_service.count_for_period(org_id, period)
                        logger.info(f"  - {period}: {stats._id}")

                        # 캘린더별 긍정결과 일수 계산 등
                        calendar_results = calendar_service.get_calendar_results(org_id)
                        logger.info(f"  - calendar positive: {len(calendar_results['positiveResult'])}일")
                        logger.info(f"  - calendar negative: {len(calendar_results['negativeResult'])}일")
                        logger.info(f"  - calendar neutral: {len(calendar_results['neutralResult'])}일")
                    except Exception as e:
                            logger.error(f"  - {period}: 오류 - {str(e)}")
            except Exception as e:
                logger.error(f"{org.orgId} 처리 중 오류: {str(e)}")
                
        logger.info("=== 전체 기관 통계 계산 완료 ===")
    
    except Exception as e:
        logger.error(f"통계 계산 중 오류: {str(e)}")

    checker.stop_thread()
    


        