# Fast API 정보 --------------------------------------------------------------------
API_SERVER = "10.100.12.70"
API_PORT = 38000

# MongoDB접속 정보 --------------------------------------------------------------------
# MONGO_IP = "10.99.2.69"
# MONGO_IP = "10.100.12.71"
# MONGO_IP = "mongodb"
MONGO_IP = "localhost"
MONGO_PORT = 27017
MONGO_DB_NAME = "mycontents"

# MariaDB접속 정보 --------------------------------------------------------------------

# OpenAI ChatGPT API Key (threewaysoft) --------------------------------------------------------------------
OPENAI_API_KEY = "os.getenv("OPENAI_API_KEY", "")"

# LOG 경로 ---------------------------------------------------------------------------
LOG_DIR = "C://Appl_logs/python"

# pdf 다운로드 경로 --------------------------------------------------------------------
SCRAPING_DOWNLOAD_FOLDER = "/Appl_logs/python/scraping_download"
#SCRAPING_DOWNLOAD_FOLDER = "C://Appl_logs/python/scraping_download"


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
KAKAO_SEND_SENDER_NUMBER = "0619317114"

# Send History 디버깅용 --------------------------------------------------------------------
CONTENTS_SEARCH_PAST_DAY = 1 

# 뭐하는건가? --------------------------------------------------------------------
CONTENTS_BASE_URL = "http://10.100.22.84:3000/kaiaas/login"
# 뭐하는건가? --------------------------------------------------------------------
KDN_KAKAO_SERVICE_URL = "http://10.100.21.128:17878/sendKakao"

# Ollam 모델 정보 --------------------------------------------------------------------
OLLAMA_MODEL = "llama-3-Korean-Bllossom-8B-Q4_K_M:latest"
# OLLAMA_URL = "http://10.99.2.71:11434"
OLLAMA_URL = "http://ollama:11434"

# Redis 접속 정보 --------------------------------------------------------------------
REDIS_HOST = "redis"
REDIS_PORT = 6379
REDIS_PASSWORD = "3waysoft"