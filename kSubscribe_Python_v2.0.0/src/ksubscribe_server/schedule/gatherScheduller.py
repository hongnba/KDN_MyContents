import schedule
import time
from datetime import datetime
from ksubscribe_server.schedule.naverScraping import NaverNewsScraping


class GatherScheduller():
    
    def __init__(self):
        self.NaverNewsScraping = NaverNewsScraping()
         
    def start(self): 
        # 하루에 한 번 Fun() 실행
        schedule.every().day.at("00:00").do(self.NaverNewsScraping.start_gatherLink)  # 매일 자정에 실행되도록 설정
        
        
        #지금한번 동작하고 그 다음에 1시간 간격으로 동작 
        self.NaverNewsScraping.start_gatherContents()
        schedule.every().hour.do(self.NaverNewsScraping.start_gatherContents)

        # 일정 작업을 계속 체크하면서 실행
        while True:
            schedule.run_pending()  # 예약된 작업을 실행
            time.sleep(600)  # 10분에 한 번씩 대기하며 확인

