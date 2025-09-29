import sys

from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from bson import ObjectId
import json
from typing import List
import time
import asyncio

from ksubscribe_server.models.model import NewsModel
from ksubscribe_server.models.model import LoadModel
from ksubscribe_server.fileLoad.webLoaderV2 import WebLoaderV2

from ksubscribe_server.analysis_test.summarization import summarize_ol
from ksubscribe_server.analysis_test.keyword import keyword_ol
from ksubscribe_server.analysis_test.analysis_openai import analysis

from ksubscribe_share.db.dbmodelV2.errorInfo import ErrorInfo
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO, ContentsRaw, ContentsMeta
from ksubscribe_share.db.dbmodelV2.commCodeVO import commCodeVO
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.dbmodel.news import News
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO


def time_now():
    return datetime.now(timezone(timedelta(hours=9)))


class DataModel(BaseModel):
    _id: ObjectId
    url: str
    title: str
    content: str


class ContentsModel(BaseModel):
    _id: ObjectId
    orgName: str
    categoryName: str
    title: str
    url: str
    collectionDate: str


class MoveContents:
    def move_contentsV3(self):
        webLoader = WebLoaderV2()
        summaryAnalysis = analysis()

        # 수집한 콘텐츠 가져오기
        contents: List[ContentsModel] = ContentsQueueVO.find_all()

        newContents = []

        if len(contents) > 0:
            for index, content in enumerate(contents):
                # if(content.orgName != "한국산업기술진흥원" or content.categoryName != "사업공고") :
                #     continue
                document = {}

                result_html = webLoader.WebTotalLoad(content.url)
                if result_html["success"] == False:

                    message = result_html["data"]
                    document = {
                        "title": content.title,
                        "organization": content.orgName,
                        "category": content.categoryName,
                        "originallink": content.url,
                        "link": "",
                        "flag": False,
                        "newsContents": {
                            "title": content.title,
                            # "content": result['contents'],
                            "image": "",
                        },
                        "error": {
                            "type": "html 정보 추출",
                            "reason": result_html["data"],
                        },
                        "look": 0,
                        "good": 0,
                        "bad": 0,
                        "pubDate": content.collectionDate,
                        "modificationTime": datetime.now(timezone(timedelta(hours=9))),
                    }
                else:
                    result_summary = summaryAnalysis.analysis(content=result_html)
                    orgVO = ContentsOrgVO.find_one({"orgName": content.orgName})
                    cmmnVO = commCodeVO.find_one({"codeName": content.categoryName})
                    if orgVO is None or cmmnVO is None:
                        print(f"{orgVO} / {cmmnVO}")
                        continue
                    result_summary["success"]
                    flag = result_summary["success"]
                    if flag:
                        clean_summary = (
                            result_summary["data"].strip("```json").strip("```")
                        )
                        json_parse = json.loads(clean_summary)
                    else:
                        json_parse = {}

                    ContentsVO(
                        title=content.title,
                        contentsOrgId=orgVO.orgId,
                        contentsOrgName=orgVO.orgName,
                        categoryId=cmmnVO.code,
                        categoryName=orgVO.orgName,
                        originallink=content.url,
                        link=content.url,
                        lookCount=0,
                        likeCount=0,
                        disLikeCount=0,
                        flag=flag,
                        newsContents=ContentsRaw(
                            contents="",
                            title=content.title,
                            image="",
                            errorInfo=(
                                None
                                if flag
                                else ErrorInfo(
                                    type="Meta 정보 추출",
                                    reason=result_summary["data"],
                                    date=datetime.now(),
                                    errorYN=True,
                                )
                            ),
                        ),
                        # newsMeta=(
                        #     None
                        #     if not flag
                        #     else ContentsMeta(
                        #         keywords=json_parse["keyword"],
                        #         predKeywords=json_parse["predkeywords"],
                        #         shortSummary=json_parse["short_summary"],
                        #         longSummary=json_parse["long_summary"],
                        #         organization=json_parse["organization"],
                        #         sentiment=json_parse["sentiment"],
                        #         errorInfo=None,
                        #     )
                        # ),
                        newsMeta=(
                            ContentsMeta(
                                keywords=["키워드1", "키워드1", "키워드1"],
                                predKeywords={"전력": 3, "에너지": 2, "인공지능": 1},
                                shortSummary="ㅇㅇㅇ",
                                longSummary="ㅇㅇㅇ",
                                organization="ㅇㅇㅇ",
                                sentiment="ㅇㅇㅇ",
                                errorInfo=None,
                            )
                            if not flag
                            else ContentsMeta(
                                keywords=json_parse["keyword"],
                                predKeywords=json_parse["predkeywords"],
                                shortSummary=json_parse["short_summary"],
                                longSummary=json_parse["long_summary"],
                                organization=json_parse["organization"],
                                sentiment=json_parse["sentiment"],
                                errorInfo=None,
                            )
                        ),
                        editDt=time_now(),
                        pubDt=time_now(),
                        errorInfo=None,
                    ).insert_one()


    # 좋아요 싫어요에 대한 유저 id 추가
    def move_contentsV4(self):
        webLoader = WebLoaderV2()
        summaryAnalysis = analysis()

        # 수집한 콘텐츠 가져오기
        contents: List[ContentsModel] = ContentsQueueVO.find_all()

        newContents = []

        if len(contents) > 0:
            for index, content in enumerate(contents):
                # if(content.orgName != "한국산업기술진흥원" or content.categoryName != "사업공고") :
                #     continue
                document = {}

                result_html = webLoader.WebTotalLoad(content.url)
                if result_html["success"] == False:

                    message = result_html["data"]
                    document = {
                        "title": content.title,
                        "organization": content.orgName,
                        "category": content.categoryName,
                        "originallink": content.url,
                        "link": "",
                        "flag": False,
                        "newsContents": {
                            "title": content.title,
                            # "content": result['contents'],
                            "image": "",
                        },
                        "error": {
                            "type": "html 정보 추출",
                            "reason": result_html["data"],
                        },
                        "look": 0,
                        "lookIds": [],
                        "good": 0,
                        "goodIds": [],
                        "dislike": 0,
                        "dislikeIds": [],
                        "pubDate": content.collectionDate,
                        "modificationTime": datetime.now(timezone(timedelta(hours=9))),
                    }
                else:
                    result_summary = summaryAnalysis.analysis(content=result_html)
                    orgVO = ContentsOrgVO.find_one({"orgName": content.orgName})
                    cmmnVO = commCodeVO.find_one({"codeName": content.categoryName})
                    if orgVO is None or cmmnVO is None:
                        print(f"{orgVO} / {cmmnVO}")
                        continue
                    result_summary["success"]
                    flag = result_summary["success"]
                    if flag:
                        clean_summary = (
                            result_summary["data"].strip("```json").strip("```")
                        )
                        json_parse = json.loads(clean_summary)
                    else:
                        json_parse = {}

                    ContentsVO(
                        title=content.title,
                        contentsOrgId=orgVO.orgId,
                        contentsOrgName=orgVO.orgName,
                        categoryId=cmmnVO.code,
                        categoryName=orgVO.orgName,
                        originallink=content.url,
                        link=content.url,
                        lookCount=0,
                        lookIds=[],
                        likeCount=0,
                        likeIds=[],
                        disLikeCount=0,
                        disLikeIds=[],
                        flag=flag,
                        newsContents=ContentsRaw(
                            contents="",
                            title=content.title,
                            image="",
                            errorInfo=(
                                None
                                if flag
                                else ErrorInfo(
                                    type="Meta 정보 추출",
                                    reason=result_summary["data"],
                                    date=datetime.now(),
                                    errorYN=True,
                                )
                            ),
                        ), 
                        newsMeta=(
                            ContentsMeta(
                                keywords=["키워드1", "키워드1", "키워드1"],
                                predKeywords={"전력": 3, "에너지": 2, "인공지능": 1},
                                shortSummary="ㅇㅇㅇ",
                                longSummary="ㅇㅇㅇ",
                                organization="ㅇㅇㅇ",
                                sentiment={"positiveRatio": "30", "negativeRatio": "20", "reason": "Test Reason"},
                                errorInfo=None,
                            )
                            if not flag
                            else ContentsMeta(
                                keywords=json_parse["keyword"],
                                predKeywords=json_parse["predkeywords"],
                                shortSummary=json_parse["short_summary"],
                                longSummary=json_parse["long_summary"],
                                organization=json_parse["organization"],
                                sentiment=json_parse["sentiment"],
                                errorInfo=None,
                            )
                        ),
                        editDt=time_now(),
                        pubDt=time_now(),
                        errorInfo=None,
                    ).insert_one()


if __name__ == "__main__":
    contents = MoveContents()
    contents.move_contentsV4()
    a = 0
