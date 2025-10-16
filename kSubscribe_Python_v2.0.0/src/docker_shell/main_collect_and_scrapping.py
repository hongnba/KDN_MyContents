    

from datetime import datetime,timedelta
import sys

from docker_collect.collect_v2 import DockerCollectMain
from docker_scraping.contents_scraping_ollama_trafilaura import ContentsScrapingOllamaTrafilaura
from ksubscribe_server.analysis.ollama_alive import OllamaAlive
from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService
from ksubscribe_share.db.service.contentsService import ContentsService
from ksubscribe_share.db.service.statsService import StatsService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.logger import Logger
#from ksubscribe_share import config as Conf
import ksubscribe_share.config as Conf
 
        
if __name__ == "__main__":

    # Check if we should process only today.json URLs
    process_today_json_only = len(sys.argv) > 1 and sys.argv[1] == "--today-json"
    
    if process_today_json_only:
        print("=== Processing URLs from today.json only ===")
        try:
            # Start ollama alive thread
            checker = OllamaAlive(op_mode="docker_server",keep_alive=False)
            checker.start_thread()
            
            # Process articles from today.json and save to contents_backup
            contentsScrapingOllamaTrafilaura = ContentsScrapingOllamaTrafilaura()
            print("contentsScrapingOllamaTrafilaura.process_articles_from_today_json()")
            contentsScrapingOllamaTrafilaura.process_articles_from_today_json()
            
            checker.stop_thread()
            print("=== Processing complete ===")
            
        except Exception as e:
            print(f"Error processing today.json: {e}")
            if 'checker' in locals():
                checker.stop_thread()
    else:
        print("=== Running full pipeline (collect + scrape) ===")
        try:
            # 1. docker collect
            dockerCollectMain = DockerCollectMain()
            print("dockerCollectMain.distribute()")
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
            print("contentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama()")
            contentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama()
        except Exception as e:
            print(f"error : {e}") #error : Message: Service /root/.wdm/drivers/chromedriver/linux64/114.0.5735.90/chromedriver unexpectedly exited. Status code was: 127

        try:
            #contents의 중복성 검사 
            logger = Logger().setup_logger(Logger.docker_scraping_result_logger_name)    
            ContentsService().removeDuplicateUrl(logger)
            pass 
        except Exception as e:
            pass  
        try:
            #7시간전 ~ 지금 까지의 contents 중 ollama 요약 안된 데이터 다시 요약(collectDT 기준)
            print("contentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama() - second time....")
            contentsScrapingOllamaTrafilaura = ContentsScrapingOllamaTrafilaura()
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(hours=7)

            #코드 재개발 필요함 
            contentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama()#(start_date=start_date,end_date=end_date,is_all=False)
        except Exception as e:
            pass 

        checker.stop_thread()
    


        