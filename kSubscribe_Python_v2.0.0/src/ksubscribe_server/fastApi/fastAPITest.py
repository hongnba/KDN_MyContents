import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__)))) # kSubscribe_Python_v1.0.0
        
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Query
import uvicorn
import asyncio
from pydantic import BaseModel
from analysis.summarization import summarize_ol
import nest_asyncio

app = FastAPI()
nest_asyncio.apply()

summary = summarize_ol.Summary()

# Request body로 받을 데이터를 정의합니다.
class Item(BaseModel):
    content: str
    userId: int

# 데이터를 POST로 받는 엔드포인트
@app.post("/items")
async def create_item(url: Item):
    print(url)
    pass 

# 데이터를 GET으로 제공하는 엔드포인트
@app.get("/items/{url}")
async def read_item(url: str):
    result = await summary.Summary("https://n.news.naver.com/mnews/article/421/0007826303")
    # print({"content": result, "name": f"Item {item_id}"})
    return {"content": result, "name": f"Item https://{url}"}


class Content(BaseModel):
    content: str


# 데이터를 GET으로 제공하는 엔드포인트
@app.get("/items")
async def read_item():
    result = await summary.Summary("https://n.news.naver.com/mnews/article/421/0007826303")
    # print({"content": result, "name": f"Item {item_id}"})
    return {"data": result, "message": "", "success" : True}


class ContentModel(BaseModel):
    data: str
    
# 데이터를 POST으로 제공하는 엔드포인트
@app.post("/params")
async def read_item(content :ContentModel):
    url = f"{content.data}"
    result = await summary.Summary(url)
    # print({"content": result, "name": f"Item {item_id}"})
    return {"data": result, "message": "", "success" : True}

# 데이터를 GET으로 제공하는 엔드포인트
# @app.get("/items/params")
# async def read_item(content: str):
#     result = await summary.Summary("https://n.news.naver.com/mnews/article/421/0007826303")
#     # print({"content": result, "name": f"Item {item_id}"})
#     return {"data": result, "message": "", "success" : True}




async def main():
    # Uvicorn 서버 실행
    config = uvicorn.Config("fastAPITest:app", host="127.0.0.1", port=8000)
    server = uvicorn.Server(config)
    await server.serve()


# ## CORS 설정 ///////////////////////////////////////////////////////////



app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React 클라이언트 도메인 또는 ["*"]로 모든 도메인 허용 가능
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메소드 허용 (GET, POST 등)
    allow_headers=["*"],  # 모든 헤더 허용
)



if __name__ == "__main__":
    uvicorn.run("fastAPITest:app", host="127.0.0.1", port=8000)