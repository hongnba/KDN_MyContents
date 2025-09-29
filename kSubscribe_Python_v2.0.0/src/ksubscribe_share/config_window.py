# Fast API 정보 --------------------------------------------------------------------
API_SERVER = "localhost"
API_PORT = 8000

# MongoDB접속 정보 --------------------------------------------------------------------
MONGO_IP = "192.168.1.41"
MONGO_PORT = 27017
MONGO_DB_NAME = "mycontents"

# MariaDB접속 정보 --------------------------------------------------------------------

# OpenAI ChatGPT API Key (threewaysoft) --------------------------------------------------------------------
import os
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# LOG 경로 ---------------------------------------------------------------------------
LOG_DIR = "C://Appl_logs/python"

# pdf 다운로드 경로 --------------------------------------------------------------------
#임형준
#SCRAPING_DOWNLOAD_FOLDER = r"C:\Users\admin\Downloads\mycontents"
#최미화
SCRAPING_DOWNLOAD_FOLDER = r"C:\Users\PC\Downloads\mycontents"
#도커
#SCRAPING_DOWNLOAD_FOLDER = r"C:\Users\admin\Downloads\mycontents"

# 암복호화 키 --------------------------------------------------------------------
SECRET_KEY = "kepco123456"

# Mail --------------------------------------------------------------------
MAIL_SEND_ID = "3waysoft.com@gmail.com"     #3way
MAIL_SEND_TOKEN = "ygqgarkrfiovqcmk"        #3way
# Telegram --------------------------------------------------------------------
TELEGRAM_SEND_TOKEN = "8124555913:AAH08CAIqF2XvQEuPCKn20Pkm9KEBuHjVSM"      #3way
# TELEGRAM_SEND_TOKEN = "6533262494:AAHap9Qi69gXV-u1F0JxQ6Sye-MdQxmOh0c"    #kdn

# Kakao --------------------------------------------------------------------
KAKAO_SEND_USER = "mycontents"
KAKAO_SEND_PW = "dpsjwl3570!"
KAKAO_SEND_REF_KEY = "s9otab042ooluwh1q6icg6f7uuqybegv"
KAKAO_SEND_SENDER_KEY = "606c5fb72ec7cf6562366937c71e44c6c5c6f7b7"
KAKAO_SEND_SENDER_NUMBER = "01011112222"

# Send History 디버깅용 --------------------------------------------------------------------
CONTENTS_SEARCH_PAST_DAY = 1 

# 뭐하는건가? --------------------------------------------------------------------
CONTENTS_BASE_URL = "http://192.168.1.41:3000/kaiaas/login"
# 뭐하는건가? --------------------------------------------------------------------
KDN_KAKAO_SERVICE_URL = "http://10.100.21.128:17878/sendKakao"

# Ollam 모델 정보 --------------------------------------------------------------------
OLLAMA_MODEL = "hf.co/MLP-KTLim/llama-3-Korean-Bllossom-8B-gguf-Q4_K_M:latest"
OLLAMA_URL = "http://192.168.1.191:11434"
