

from threading import Thread,Event
import requests
from langchain_ollama import ChatOllama
from ollama import ProcessResponse,chat,ps,pull
import time
import subprocess
import ksubscribe_share.config as CONF  
from docker_talk_send.model.TelegramSendModel import TelegramSendModel
from ksubscribe_share.logger import Logger
from ksubscribe_share.db.service.memberService import MemberService
import threading
import asyncio
"""
Ollama 서비스 Alive 체크
"""
class OllamaAlive():

    def __init__(self, op_mode:str, keep_alive : bool):
        """
        keep_alive : true 이면 계속 산다, deamon = False 여야 함. 
        """ 
        self.op_mode = op_mode
        self.tele_send_status =False
        # scrapping에서 사용하는 로그와 같은 주소값 가지는 로거임.
        self.docker_scraping_logger = Logger().setup_logger(Logger.docker_scraping_logger_name) 
        
        #self.chat_id = "7405686836"# 쿼리 조건 : mberType = F0001, mberAuthority = AUTH00001
        #docker_collect_logger.info(f"텔레그램 초기화 시작")
        self.send_telegram_manager = TelegramSendModel(token=CONF.TELEGRAM_SEND_TOKEN)
        #self.send_telegram_manager = TelegramSendModel("6533262494:AAHap9Qi69gXV-u1F0JxQ6Sye-MdQxmOh0c" )
        self.send_telegram_manager.initialize()
        
        self.stop_event = Event()

        self.alive_check_thread = Thread(
            target = self._start,
            args=(self.stop_event,),
            daemon= not keep_alive
        )
        
        self.admin_chat_id = MemberService().getAdminMembersTeleChatIds() 
        pass  
    def stop_thread(self):
        self.stop_event.set()
        pass 

    def start_thread(self):
        self.alive_check_thread.start()

    def restart_ollama(self):
        """ ollama 서비스를 재시작하는 함수 """
        try:
            result = subprocess.run(["sudo", "systemctl", "restart", "ollama"], check=True, capture_output=True, text=True)
            return f"✅ ollama 서비스 재시작 성공:\n{result.stdout}"
        except subprocess.CalledProcessError as e:
            return f"❌ ollama 서비스 재시작 실패:\n{e.stderr}"
 
    def _start(self,stop_event:Event):
        # 1. request  
        url = f'{CONF.OLLAMA_URL}/api/ps'
        err_counter = [] 
        
        while(not stop_event.is_set()):
            time.sleep(1)
            try:
                if len(err_counter) >= 5:
                    message = f"ollama 재시작 필요 : {len(err_counter)}회 오류"
                    self.docker_scraping_logger.error(message)
                    err_counter.clear()    
                    
                    #한번만 텔레그램에 보내도록 함. 
                    if self.op_mode == "ollama_server": 
                        #self.restart_ollama()
                        pass 
                    elif self.op_mode == "docker_server": 
                        if not self.tele_send_status: 
                            for admin in self.admin_chat_id:

                                chat_id = admin.teleChatId
                                reuslt = self.send_telegram_manager.send_feed_message_in_thread(chat_id,message)
                                print("---------------------ollama------------")
                                print(reuslt)
                                self.tele_send_status = True 
                    err_counter.clear()

                response = requests.get(url, timeout=3)   
                response.raise_for_status()   
                
            except requests.exceptions.Timeout: 
                err_counter.append("The request timed out")
                self.ollama_status = False
            except requests.exceptions.RequestException as e: 
                err_counter.append(f"{e}")
                self.ollama_status = False
            except Exception as e: 
                err_counter.append(f"{e}")
                self.ollama_status = False
import telegram
from telegram.ext import Updater, CommandHandler, CallbackContext
def start(update: telegram.Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    update.message.reply_text(f"Your Chat ID is: {chat_id}")
    print(f"Chat ID: {chat_id}")  # 서버 콘솔에 출력

def main(): 
    checker = OllamaAlive("docker_server",keep_alive=False)  
    checker.start_thread()  
    while(1):
        pass 
    pass 

if __name__ == "__main__":
    main()