import time

from fastapi import APIRouter, FastAPI, Request
import uvicorn

import ksubscribe_server.fastApi.contentsAPI as contentsAPI
import ksubscribe_share.config as cfg

## 1. API 옵션 설정
app = FastAPI()
app.include_router(contentsAPI.router, prefix="/kcs/api/v1/python/contents")


## 2. 미들웨어 세팅
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    # start_time = time.perf_counter()
    response = await call_next(request)
    # process_time = time.perf_counter() - start_time
    # response.headers["X-Process-Time"] = str(process_time)
    return response


## 3. DB 세팅
# MongoManager().set_db(MONGO_DB_NAME)
# MongoManager().set_conn_string(MONGO_CONNECTION_STRING)
# MongoManager().start()


## 4. 알고리즘 세팅
# ContentAlgorithm().set_model(BERT_MODEL_NAME)
# ContentAlgorithm().set_pre_defined_keywords(PRE_DEFINED_KEYWORDS)

if __name__ == "__main__":
    uvicorn.run(app, host=cfg.API_SERVER, port=cfg.API_PORT)
