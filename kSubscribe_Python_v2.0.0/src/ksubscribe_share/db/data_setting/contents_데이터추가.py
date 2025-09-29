import random
import sys
from datetime import datetime, timedelta, timezone
from ksubscribe_share.db.dbmodelV2.predefineKeywordVO import PredefineKeywordVO
from ksubscribe_share.db.dbmodel.news import News
from ksubscribe_share.db.dbmodelV2.contentsImageVO import contentsImageVO
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
from ksubscribe_share.db.mongoManager import MongoManager

from ksubscribe_server.fileLoad.webLoaderV2 import WebLoaderV2

from ksubscribe_server.analysis_test.analysis_openai import analysis

from ksubscribe_share.db.dbmodelV2.errorInfo import ErrorInfo
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO, ContentsRaw, ContentsMeta, SentimentInfo
from ksubscribe_share.db.dbmodelV2.commCodeVO import commCodeVO
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO

from pydantic import BaseModel
from bson import ObjectId

import json
from typing import Dict, List

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
        contents: List[ContentsQueueVO] = ContentsQueueVO.find_all()

        # predefine 된 이미지 정보 가져오기
        predefinedImagesDict = {}
        contentsImages: List[contentsImageVO] = contentsImageVO.find_all()
    
        predKeywords: List[PredefineKeywordVO] = PredefineKeywordVO.find_all()
    
        for item in contentsImages:
            if item.keyword not in predefinedImagesDict:
                predefinedImagesDict[item.keyword] = []
            predefinedImagesDict[item.keyword].append(item)
            
        # 기관명 가져오기
        orgs: List[ContentsOrgVO] = ContentsOrgVO.find_all()
        
        # name 속성만 추출하여 List[str]로 변환
        org_name_list: List[str] = [org.orgName for org in orgs]
        
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
                        "organization": content.contentOrgId,
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
                        "imageId": "",
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

                    # 1~5 사이의 랜덤 n 값 생성
                    n = random.randint(0, 5)

                    # 랜덤으로 n개의 요소 추출
                    random_org_list = random.sample(org_name_list, min(n, len(org_name_list)))  # n이 리스트 길이를 초과하지 않도록

                    random_predkeyword_list = random.sample(predKeywords, min(3, len(predKeywords)))  # n이 리스트 길이를 초과하지 않도록

                    ContentsVO(
                        title=content.title,
                        url=content.url,
                        contentsOrgId=orgVO.orgId,
                        contentsOrgName=orgVO.orgName,
                        categoryId=cmmnVO.code,
                        categoryName=cmmnVO.codeName,
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
                                predKeywords={random_predkeyword_list[0].keyword: 3, random_predkeyword_list[1].keyword: 2, random_predkeyword_list[2].keyword: 1},
                                shortSummary="ㅇㅇㅇ",
                                longSummary="ㅇㅇㅇ",
                                # organization=random_org_list,
                                # sentiment={"positiveRatio": "30", "negativeRatio": "20", "reason": "Test Reason"},
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
                        imageId=str(random.choice(predefinedImagesDict[random_predkeyword_list[0].keyword])._id)
                    ).insert_one()

# 좋아요 싫어요에 대한 유저 id 추가
    def move_contents_dummy_data(self):
        # 수집한 콘텐츠 가져오기
        contents: List[ContentsQueueVO] = ContentsQueueVO.find_all()

        # predefine 된 이미지 정보 가져오기
        predefinedImagesDict = {}
        contentsImages: List[contentsImageVO] = contentsImageVO.find_all()
    
        predKeywords: List[PredefineKeywordVO] = PredefineKeywordVO.find_all()
    
        for item in contentsImages:
            if item.keyword not in predefinedImagesDict:
                predefinedImagesDict[item.keyword] = []
            predefinedImagesDict[item.keyword].append(item)
            
        # 기관명 가져오기
        orgs: List[ContentsOrgVO] = ContentsOrgVO.find_all()
        
        # name 속성만 추출하여 List[str]로 변환
        org_name_list: List[str] = [org.orgName for org in orgs]
        org_name_id_dict: Dict[str, str] = {org.orgName: org.orgId for org in orgs}
        
        if len(contents) > 0:
            for index, content in enumerate(contents):
                orgVO = ContentsOrgVO.find_one({"orgId": content.contentOrgId})
                cmmnVO = commCodeVO.find_one({"code": content.cateId})
                if orgVO is None or cmmnVO is None:
                    print(f"{orgVO} / {cmmnVO}")
                    continue

                # 1~5 사이의 랜덤 n 값 생성
                n = random.randint(0, 5)

                # 랜덤으로 n개의 요소 추출
                random_keys = random.sample(list(org_name_id_dict.keys()), 3)
                random_org_dict = {key: org_name_id_dict[key] for key in random_keys}

                random_predkeyword_list = random.sample(predKeywords, min(3, len(predKeywords)))  # n이 리스트 길이를 초과하지 않도록

                target_sum = 100
                ratio_cnt = 3

                sentiment_list = []
                for name, id in random_org_dict.items():
                    # 첫 두 개의 숫자를 랜덤으로 생성
                    num1 = random.randint(1, target_sum - (ratio_cnt - 1))
                    num2 = random.randint(1, target_sum - num1 - (ratio_cnt - 2))
                    num3 = target_sum - num1 - num2
                    numbers = [num1, num2, num3]
                    random.shuffle(numbers)  # 순서를 섞어서 랜덤하게 반환    
                    sentiment_list.append(SentimentInfo(orgId=id, orgName=name, positiveRatio=numbers[0], negativeRatio=numbers[1], neutralRatio=numbers[2], reason="Test Reason"))

                ContentsVO(
                    title=content.title,
                    url=content.url,
                    contentsOrgId=orgVO.orgId,
                    contentsOrgName=orgVO.orgName,
                    categoryId=cmmnVO.code,
                    categoryName=cmmnVO.codeName,
                    originallink=content.url,
                    link=content.url,
                    
                    pubDt=time_now(), #기사 날짜 
                    collectDt=time_now(), #docker_collect 날짜 
                    
                    lookCount=0,
                    likeCount=0,
                    disLikeCount=0,
                    lookIds=[],
                    likeIds=[],
                    disLikeIds=[],
                    rawCollectDt=time_now(),
                    rawCollectSucYN=True,
                    metaSucYN=True,
                    contentsRaw=ContentsRaw(
                        contents="",
                        title=content.title,
                        image="",
                        errorInfo=None
                    ),
                    
                    contentsMeta=ContentsMeta(
                        keywords=["키워드1", "키워드2", "키워드3"],
                        predKeywords={random_predkeyword_list[0].keyword: 3, random_predkeyword_list[1].keyword: 2, random_predkeyword_list[2].keyword: 1},
                        shortSummary="ㅇㅇㅇ",
                        longSummary="ㅁㅁㅁㅁㅁ",
                        sentiments=sentiment_list,
                        errorInfo=None,
                    ),
                    metaAnalyzeDt=time_now(),                    
                    imageId=str(random.choice(predefinedImagesDict[random_predkeyword_list[0].keyword])._id)
                ).insert_one()


if __name__ == "__main__":
    contents = MoveContents()
    contents.move_contents_dummy_data()
