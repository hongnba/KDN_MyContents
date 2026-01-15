import sys, os
import bson

# sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__)))) # kSubscribe_Python_v1.0.0

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Query, Request, UploadFile
from pydantic import BaseModel
# from analysis.summarization import summarize_ol
# from analysis.category import category_ol
# from analysis.keyword import keyword_ol
# from analysis.reputation import emotion_ol
# from models.model import MatchModel, EmotionModel, LoadModel, ContentModel, NewsModel
from ksubscribe_share.db.dbmodel.news import News
from ksubscribe_share.db.dbmodel.subscribe import Subscribe
from dataclasses import dataclass, asdict
from bson.binary import Binary  # Binary 클래스 임포트

# from db.dbmodel.subscribe import Subscribe

from typing import List
# from fileLoad import load
import nest_asyncio
import json
from datetime import datetime, timedelta, timezone
import re
import base64

app = FastAPI()
nest_asyncio.apply()


@app.get("/")
async def read_root():
    return {"Hello": "World"}


# WebLoad = load.WebLoad()


# Request body로 받을 데이터를 정의합니다.
class Item(BaseModel):
    content: str
    userId: int


class ImageModel(BaseModel):
    filename: str
    contentType: str
    base64: str


class ViewCountModel(BaseModel):
    data: str


class RequestModel(BaseModel):
    data: str


class SubModel(BaseModel):
    user: str
    subInfo: List[int]


class UserSubListModel(BaseModel):
    data: List[str]


class KeywordModel(BaseModel):
    data: List[str]
    time: datetime


class ContentsModel(BaseModel):
    data: List[str]
    count: int
    time: datetime


# /////////////////////////////// GET ///////////////////////////////////////////////


# 로컬 폴더에 저장된 이미지 Client로 보냄
# 이미지 반환
@app.get("/test/img")
async def get_image_json(request: Request):
    try:
        params = dict(request.query_params)
        filename = params["data"]

        file_path = f"uploaded_images/{filename}"
        if not os.path.exists(file_path):
            print("파일이 존재하지 않습니다.")

        # 파일 읽기 및 Base64 인코딩
        with open(file_path, "rb") as f:
            base64_data = base64.b64encode(f.read()).decode("utf-8")

        # JSON 응답 반환
        result_json = json.dumps(
            {
                "filename": filename,
                "contentType": "image/jpeg",  # MIME 타입 설정
                "base64": base64_data,
            },
            ensure_ascii=False,
            indent=4,
            default=str,
        )

        return {"data": result_json, "message": "", "success": True}

        # return {
        #     "filename": filename,
        #     "contentType": "image/jpeg",  # MIME 타입 설정
        #     "base64": base64_data,
        # }
    except Exception as e:
        raise print("이미지 처리 실패")


# link로 Contents 찾기
# 일단 안씀
@app.get("/content/view/link")
async def get_image_json(request: Request):
    try:
        params = dict(request.query_params)
        link = params["data"]

        result = News.find_one({"link": link})
        # JSON 응답 반환
        result_json = json.dumps(
            {
                "id": result._id,
                "title": result.title,
                "organization": result.organization,
                "category": result.category,
                "originallink": result.originallink,
                "link": result.link,
                "pubDate": result.pubDate,
                "newsContents": {
                    "title": getattr(result.newsContents, "title", None),
                    "image": getattr(result.newsContents, "image", None),
                },
                "newsMeta": {
                    "keywords": getattr(result.newsMeta, "keywords", None),
                    "shortSummary": getattr(result.newsMeta, "shortSummary", None),
                    "longSummary": getattr(result.newsMeta, "longSummary", None),
                    "organization": getattr(result.newsMeta, "organization", None),
                    "sentiment": getattr(result.newsMeta, "sentiment", None),
                },  # user.newsMeta,
                "error": {
                    "type": getattr(result.error, "type", None),
                    "reason": getattr(result.error, "reason", None),
                },
                "look": result.look,
                "good": result.good,
                "bad": result.bad,
                "flag": result.flag,
                "modificationTime": result.modificationTime,
            },
            ensure_ascii=False,
            indent=4,
            default=str,
        )

        return {"data": result_json, "message": "", "success": True}

        # return {
        #     "filename": filename,
        #     "contentType": "image/jpeg",  # MIME 타입 설정
        #     "base64": base64_data,
        # }
    except Exception as e:
        raise print("콘텐츠 조회 실패")


# ObjectId로 Contents 찾기
@app.get("/content/view/id")
async def get_image_json(request: Request):
    try:
        params = dict(request.query_params)
        id = params["data"]

        result = News.find_one_id(id)

        # JSON 응답 반환
        result_json = json.dumps(
            {
                "id": result._id,
                "title": result.title,
                "organization": result.organization,
                "category": result.category,
                "originallink": result.originallink,
                "link": result.link,
                "pubDate": result.pubDate,
                "newsContents": {
                    "title": getattr(result.newsContents, "title", None),
                    "image": getattr(result.newsContents, "image", None),
                },
                "newsMeta": {
                    "keywords": getattr(result.newsMeta, "keywords", None),
                    "shortSummary": getattr(result.newsMeta, "shortSummary", None),
                    "longSummary": getattr(result.newsMeta, "longSummary", None),
                    "organization": getattr(result.newsMeta, "organization", None),
                    "sentiment": getattr(result.newsMeta, "sentiment", None),
                },  # user.newsMeta,
                "error": {
                    "type": getattr(result.error, "type", None),
                    "reason": getattr(result.error, "reason", None),
                },
                "look": result.look,
                "good": result.good,
                "bad": result.bad,
                "flag": result.flag,
                "modificationTime": result.modificationTime,
            },
            ensure_ascii=False,
            indent=4,
            default=str,
        )

        return {"data": result_json, "message": "", "success": True}

        # return {
        #     "filename": filename,
        #     "contentType": "image/jpeg",  # MIME 타입 설정
        #     "base64": base64_data,
        # }
    except Exception as e:
        raise print("콘텐츠 조회 실패")


# /////////////////////////////// POST ///////////////////////////////////////////////
# 이미지 업로드 시 로컬 폴더에 저장
# 관리자 CI 업로드 등에서 사용
@app.post("/test/img/upload")
async def read_item(request: ImageModel):
    # data : SubModel = json.loads(content.data)

    # Base64 디코딩
    image_data = base64.b64decode(request.base64)
    file_path = f"uploaded_images/{request.filename}"

    # 디렉토리 생성 후 파일 저장
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(image_data)

    return {"data": "", "message": "", "success": True}


# 1000개 정도의 0,1로 이루어진 List
# ByteArray 로 저장 시 Size: 196
# List 로 저장 시 Size: 8952
#  (Size: 컬렉션이 차지하는 실제 데이터 크기(바이트 단위))


# 사용자 구독 정보 저장
@app.post("/user/subscribe/add")
async def read_item(content: RequestModel):

    data: SubModel = json.loads(content.data)

    binary_string = "".join(map(str, data["subInfo"]))

    # 이진 문자열을 bytearray로 변환
    byte_array = bytearray(
        int(binary_string, 2).to_bytes((len(binary_string) + 7) // 8, byteorder="big")
    )

    document = {
        "user": data["user"],
        "subscribeInfo": Binary(byte_array),  # bytearray를 Binary로 래핑하여 저장
        "len": len(data["subInfo"]),
    }

    if Subscribe.find_one({"user": document["user"]}) is None:
        # 중복이 없을 경우 데이터 삽입
        Subscribe.insert(document)
        print("success")
    else:
        print("Document with the same 'user' already exists.")

    # print(f'{data["user"]}  | Original : {data["subInfo"]}')
    # get_userSub(document["user"])

    return {"data": "", "message": "", "success": True}


# user 정보 조회 예시
def get_userSub(user):
    result_find: SubModel = Subscribe.find_one({"user": user})

    if result_find == None:
        return

    list = byte_to_list(result_find.subscribeInfo, result_find.len)
    print(f"{user}  | Save :{list}")


# binary 데이터를 list로 변환하는 함수
def byte_to_list(data, len):
    # Binary 데이터를 bytearray로 변환
    loaded_byte_array = bytearray(data)

    # 이진 문자열을 List[int]로 변환
    loaded_binary_string = bin(int.from_bytes(loaded_byte_array, byteorder="big"))[
        2:
    ].zfill(len)
    loaded_data = [int(x) for x in loaded_binary_string]

    return loaded_data


# 콘텐츠 조회
@app.post("/content/list/keyword")
async def read_item(request: RequestModel):
    # params = keyword.data

    content: KeywordModel = json.loads(request.data)

    time = content["time"]
    params = content["keywords"]
    if time == None:
        return

    date_time = datetime.strptime(time, "%Y-%m-%dT%H:%M:%S.%fZ")

    # keyword = list(keyword)  # set을 list로 변환

    # 정규식을 사용하여 title 필드에 'AI'가 포함된 문서 필터링
    query = ""
    time = {"modificationTime": {"$lt": date_time}}
    total_s = []
    if len(params) > 0:
        for index, param in enumerate(params):
            s = {"title": {"$regex": param, "$options": "i"}}
            total_s.append(s)

    total_s.append(time)
    query = {"$and": total_s}

    result = News.find_many(query, limit=30)

    result_json = json.dumps(
        [
            {
                "id": user._id,
                "title": user.title,
                "organization": user.organization,
                "category": user.category,
                "originallink": user.originallink,
                "link": user.link,
                "pubDate": user.pubDate,
                "newsContents": {
                    "title": getattr(user.newsContents, "title", None),
                    "image": getattr(user.newsContents, "image", None),
                },
                "newsMeta": {
                    "keywords": getattr(user.newsMeta, "keywords", None),
                    "shortSummary": getattr(user.newsMeta, "shortSummary", None),
                    "longSummary": getattr(user.newsMeta, "longSummary", None),
                    "organization": getattr(user.newsMeta, "organization", None),
                    "sentiment": getattr(user.newsMeta, "sentiment", None),
                },  # user.newsMeta,
                "error": {
                    "type": getattr(user.error, "type", None),
                    "reason": getattr(user.error, "reason", None),
                },
                "look": user.look,
                "good": user.good,
                "bad": user.bad,
                "flag": user.flag,
                "modificationTime": user.modificationTime,
            }
            for user in result
        ],
        ensure_ascii=False,
        indent=4,
        default=str,
    )

    return {"data": result_json, "message": "", "success": True}


# 콘텐츠 추가 조회 - PAGE (더보기 버튼 선택 시 )
@app.post("/content/list/add")
async def read_item(request: RequestModel):

    content: ContentsModel = json.loads(request.data)

    time = content["time"]
    params = content["keywords"]
    page = content["count"]

    date_time = datetime.strptime(time, "%Y-%m-%dT%H:%M:%S.%fZ")

    # keyword = list(keyword)  # set을 list로 변환

    # 정규식을 사용하여 title 필드에 'AI'가 포함된 문서 필터링
    query = ""
    time = {"modificationTime": {"$lt": date_time}}
    total_s = []
    if len(params) > 0:

        for index, param in enumerate(params):
            s = {"title": {"$regex": param, "$options": "i"}}
            total_s.append(s)

    total_s.append(time)
    query = {"$and": total_s}

    result = News.find_many(query, limit=30, skip=30 * page)

    result_json = json.dumps(
        [
            {
                "id": user._id,
                "title": user.title,
                "organization": user.organization,
                "category": user.category,
                "originallink": user.originallink,
                "link": user.link,
                "pubDate": user.pubDate,
                "newsContents": {
                    "title": getattr(user.newsContents, "title", None),
                    "image": getattr(user.newsContents, "image", None),
                },
                "newsMeta": {
                    "keywords": getattr(user.newsMeta, "keywords", None),
                    "shortSummary": getattr(user.newsMeta, "shortSummary", None),
                    "longSummary": getattr(user.newsMeta, "longSummary", None),
                    "organization": getattr(user.newsMeta, "organization", None),
                    "sentiment": getattr(user.newsMeta, "sentiment", None),
                },  # user.newsMeta,
                "error": {
                    "type": getattr(user.error, "type", None),
                    "reason": getattr(user.error, "reason", None),
                },
                "look": user.look,
                "good": user.good,
                "bad": user.bad,
                "flag": user.flag,
                "modificationTime": user.modificationTime,
            }
            for user in result
        ],
        ensure_ascii=False,
        indent=4,
        default=str,
    )

    return {"data": result_json, "message": "", "success": True}


# 조회수 추가
@app.post("/content/view/count")
async def read_item(request: ViewCountModel):
    News.update_count_byid(request.data, {"look": 1})

    # data = News.find_one({'link': link})

    return {"data": "", "message": "", "success": True}


# 좋아요 추가
@app.post("/content/good/Add/count")
async def read_item(request: ViewCountModel):
    News.update_count_byid(request.data, {"good": 1})

    # data = News.find_one({'link': link})
    # TODO:어떤 사용자가 좋아요 했는지 DB에 추가

    return {"data": "", "message": "", "success": True}


# 좋아요 삭제
@app.post("/content/good/remove/count")
async def read_item(request: ViewCountModel):
    News.update_count_byid(request.data, {"good": -1})

    # data = News.find_one({'link': link})
    # TODO:어떤 사용자 정보 DB에서 좋아요 기록 제거

    return {"data": "", "message": "", "success": True}


# 싫어요 추가
@app.post("/content/bad/Add/count")
async def read_item(request: ViewCountModel):
    News.update_count_byid(request.data, {"bad": 1})

    # data = News.find_one({'link': link})
    # TODO:어떤 사용자가 싫어요 했는지 DB에 저장

    return {"data": "", "message": "", "success": True}


# 싫어요 삭제
@app.post("/content/bad/remove/count")
async def read_item(request: ViewCountModel):
    News.update_count_byid(request.data, {"bad": -1})

    # data = News.find_one({'link': link})
    # TODO:어떤 사용자 정보 DB에서 싫어요 기록 제거

    return {"data": "", "message": "", "success": True}


# 콘텐츠 추천 알고리즘 테스트용
@app.post("/content/recommand")
async def read_item(request: RequestModel):
    # params = keyword.data

    idList = ['6762718ac765394830f064bf', '6762718ac765394830f064c0', '6762718ac765394830f064c1']

    return {"result": idList}


    content: KeywordModel = json.loads(request.data)

    time = content["time"]
    params = content["keywords"]
    if time == None:
        return

    date_time = datetime.strptime(time, "%Y-%m-%dT%H:%M:%S.%fZ")

    # keyword = list(keyword)  # set을 list로 변환

    # 정규식을 사용하여 title 필드에 'AI'가 포함된 문서 필터링
    query = ""
    time = {"modificationTime": {"$lt": date_time}}
    total_s = []
    if len(params) > 0:
        for index, param in enumerate(params):
            s = {"title": {"$regex": param, "$options": "i"}}
            total_s.append(s)

    total_s.append(time)
    query = {"$and": total_s}

    result = News.find_many(query, limit=30)

    result_json = json.dumps(
        [
            {
                "id": user._id,
                "title": user.title,
                "organization": user.organization,
                "category": user.category,
                "originallink": user.originallink,
                "link": user.link,
                "pubDate": user.pubDate,
                "newsContents": {
                    "title": getattr(user.newsContents, "title", None),
                    "image": getattr(user.newsContents, "image", None),
                },
                "newsMeta": {
                    "keywords": getattr(user.newsMeta, "keywords", None),
                    "shortSummary": getattr(user.newsMeta, "shortSummary", None),
                    "longSummary": getattr(user.newsMeta, "longSummary", None),
                    "organization": getattr(user.newsMeta, "organization", None),
                    "sentiment": getattr(user.newsMeta, "sentiment", None),
                },  # user.newsMeta,
                "error": {
                    "type": getattr(user.error, "type", None),
                    "reason": getattr(user.error, "reason", None),
                },
                "look": user.look,
                "good": user.good,
                "bad": user.bad,
                "flag": user.flag,
                "modificationTime": user.modificationTime,
            }
            for user in result
        ],
        ensure_ascii=False,
        indent=4,
        default=str,
    )

    return {"data": result_json, "message": "", "success": True}

# ## CORS 설정 ///////////////////////////////////////////////////////////
app.add_middleware(
    CORSMiddleware,
    # allow_origins=["http://localhost:3000"],  # React 클라이언트 도메인 또는 ["*"]로 모든 도메인 허용 가능
    allow_origins=["*"],  # React 클라이언트 도메인 또는 ["*"]로 모든 도메인 허용 가능
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메소드 허용 (GET, POST 등)
    allow_headers=["*"],  # 모든 헤더 허용
)


# if __name__ == "__main__":
#     uvicorn.run("fastAPI:app", host="127.0.0.1", port=8000)
