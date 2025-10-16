import sys
import traceback
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from bson import ObjectId
import json
from typing import List, Dict 
import time
import asyncio

#from docker_scraping
from docker_collect.driver_utils import get_driver
from ksubscribe_server.models.model import NewsModel
from ksubscribe_server.models.model import LoadModel
from ksubscribe_server.analysis.analysis_openai_v2 import analysisV2
from ksubscribe_share.db.dbmodelV2.errorInfo import ErrorInfo
from ksubscribe_share.db.service.contentsService import ContentsService
from ksubscribe_share.db.service.contentsCollectDailyHistoryService import ContentsCollectDailyHistoryService
from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO, ContentsRaw, ContentsMeta, SentimentInfo
from ksubscribe_share.db.dbmodelV2.commCodeVO import CommCodeVO
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO, ContentsOrgCategory
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.dbmodel.news import News
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
from ksubscribe_share.db.dbmodelV2.predefineKeywordVO import PredefineKeywordVO
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.service.predefineKeywordService import PredefineKeywordService
from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService
from ksubscribe_share.db.service.baseQueryService import BaseQueryService
from ksubscribe_share.db.service.contentsImageService import ContentsImageService
from ksubscribe_server.similarity.simularity_check import SimularityChecker
from ksubscribe_share.logger import Logger
from ksubscribe_server.models.contentsMetaResult import ContentsMetaResult
from docker_scraping.web_loader import WebLoaderV3

class CustomScrapException(Exception):
    def __init__(self, message):
        super().__init__(message)

def time_now():
    return datetime.now(timezone(timedelta(hours=9)))


class ContentsScrapingBase:
                    
    docker_scraping_logger = Logger().setup_logger(Logger.docker_scraping_logger_name)    
                    
    def generateContentsQueueVO(self, entry): 
        contentsQueueVO = ContentsQueueVO()
        contentsQueueVO.contentOrgId=entry["contentsOrgId"]
        contentsQueueVO.cateId=entry["categoryId"]
        contentsQueueVO.url=entry["url"]
        contentsQueueVO.title=entry["title"]
        contentsQueueVO.pubDt=entry["pubDt"]
        return contentsQueueVO
                
    def generateContentVO(self, queueContent : ContentsQueueVO) -> ContentsVO :
        
        contentsVO = ContentsVO()
        contentsVO.title=queueContent.title
        contentsVO.contentsOrgId=queueContent.contentOrgId
        contentsVO.contentsOrgName = self.commCodeService.get_orgName_by_orgId(queueContent.contentOrgId)
        contentsVO.categoryId=queueContent.cateId
        contentsVO.categoryName = self.commCodeService.get_cateName_by_cateId(queueContent.cateId)
        contentsVO.originallink=queueContent.url
        contentsVO.url=queueContent.url 
        contentsVO.link=queueContent.url
        
        # KST 문자열을 datetime으로 변환
        #kst_time = datetime.strptime(queueContent.pubDt, "%Y%m%d")  # "2025-01-19 00:00:00" (KST)
        # KST -> UTC 변환
        #kst_offset = timedelta(hours=9)  # KST는 UTC+9
        #utc_time = kst_time - kst_offset  # UTC 시간 계산
        
        contentsVO.pubDt=queueContent.pubDt#utc_time
        contentsVO.collectDt=queueContent.collectDt
        contentsVO.collectKeyword=queueContent.collectKeyword
        contentsVO.lookCount=0
        contentsVO.likeCount=0
        contentsVO.disLikeCount=0
        contentsVO.lookIds=[]
        contentsVO.likeIds=[]
        contentsVO.disLikeIds=[]
        
        return contentsVO
          
    def generateContentsRaw(self, title=None, contents = None, errorInfo = None) -> ContentsRaw:
        
        contentsRaw = ContentsRaw()
        contentsRaw.title = title
        contentsRaw.contents=contents
        contentsRaw.image=""
        contentsRaw.errorInfo=errorInfo
        return contentsRaw
    
    def generateContentsMeta(self, contentsVO, flag, json_parse, errorInfo = None) -> ContentsMeta:
        
        contentsMeta = ContentsMeta()
        contentsMeta.keywords=json_parse["keyword"]
        contentsMeta.shortSummary=json_parse["short_summary"]
        contentsMeta.longSummary=json_parse["long_summary"]
        contentsMeta.predKeywords=json_parse["predkeywords"]
        contentsMeta.sentiments= self.generateSentiment(json_parse)
        contentsMeta.errorInfo=None,
        contentsMeta.errorInfo=errorInfo
        return contentsMeta

    def get_float(self, json_value, default_value:float ): 
        try:
            if json_value is not None and not isinstance(json_value, float):
                float_value = float(json_value)
        except (ValueError, TypeError, KeyError) as e:
            float_value = default_value
        
        return float_value
    
    
    def generateContentsMeta_ollama(self,contentsVO:ContentsVO,contentsMetaResult: ContentsMetaResult):
        try:
            # Normalize meta success flag (can be boolean or "Y"/"N" string)
            meta_flag = None if contentsMetaResult is None else getattr(contentsMetaResult, "metaSucYN", None)
            is_success = True if meta_flag in [True, "Y", "y"] else False

            if not is_success:
                contentsVO.metaSucYN = "N"
                # Ensure metaAnalyzeDt exists
                if contentsVO.metaAnalyzeDt is None:
                    contentsVO.metaAnalyzeDt = datetime.now()
                contentsVO.contentsMeta = ContentsMeta(
                    errorInfo=self.generateErrorInfo(
                        errorYN="Y",
                        date=contentsVO.metaAnalyzeDt,
                        reason="analysis failed"
                    )
                )
                return contentsVO

            contentsVO.metaSucYN = "Y" if meta_flag in [True, "Y", "y"] else "N"
            if contentsMetaResult is not None:
                if getattr(contentsMetaResult, "metaAnalyzeDt", None) is not None:
                    contentsVO.metaAnalyzeDt = contentsMetaResult.metaAnalyzeDt
                contentsVO.contentsMeta = contentsMetaResult.contentsMeta
            return contentsVO
        except Exception:
            # Fallback: mark as failed with error info
            contentsVO.metaSucYN = "N"
            if contentsVO.metaAnalyzeDt is None:
                contentsVO.metaAnalyzeDt = datetime.now()
            contentsVO.contentsMeta = ContentsMeta(
                errorInfo=self.generateErrorInfo(
                    errorYN="Y",
                    date=contentsVO.metaAnalyzeDt,
                    reason="analysis error"
                )
            )
            return contentsVO
    
    
    def generateContentsMeta_version2(self, isSuccess:bool, contentsVO:ContentsVO, result_analysis)-> ContentsVO:
        
        if isSuccess == False:
            contentsVO.metaSucYN = "N"
            contentsVO.contentsMeta = ContentsMeta(
                errorInfo =  self.generateErrorInfo(errorYN="Y",date=contentsVO.metaAnalyzeDt ,reason=result_analysis["error_data"]) 
            )   
            return contentsVO
            
            
        data_json= None
        try:
            result_analysis["data"] = result_analysis["data"].replace("`","")
            result_analysis["data"] = result_analysis["data"].replace("json","")
            result_analysis["data"] = result_analysis["data"].replace("\n","")
            result_analysis = json.loads(result_analysis["data"])
        except Exception as e :
            contentsVO.metaSucYN = "N"
            contentsVO.contentsMeta = ContentsMeta(
                errorInfo =  self.generateErrorInfo(errorYN="Y",date=contentsVO.metaAnalyzeDt ,reason="meta analyze result is empty") 
            )   
            self.docker_scraping_logger.info(f"Web 컨텐츠 json->dict변환 실패")
            self.docker_scraping_logger.error(traceback.format_exc())
            return contentsVO
        
        
        sentiment_list = []            
        for index, item in enumerate(result_analysis["sentiment"]["organization"]):
            try: 
                orgName=result_analysis["sentiment"]["organization"][index]
                org = ContentsOrgService().findOrgbyName(orgName)
                org_id = None
                if org:
                    org_id = org.orgId
                else:
                    org_id = ContentsOrgService().get_orgId_by_synonym(orgName)
                    org_id = "not found" if org_id is None else org_id
                
                default_value = 0.0    
                float_positiveRatio = self.get_float(result_analysis["sentiment"]["positiveRatio"][index], default_value) 
                float_negativeRatio = self.get_float(result_analysis["sentiment"]["negativeRatio"][index], default_value) 
                float_neutralRatio = self.get_float(result_analysis["sentiment"]["neutralRatio"][index], default_value) 
                
                sentiment =SentimentInfo(
                    orgId=org_id,
                    orgName=orgName,
                    positiveRatio=float_positiveRatio, 
                    negativeRatio=float_negativeRatio,
                    neutralRatio=float_neutralRatio,
                    reason=result_analysis["sentiment"]["reason"][index],)
                sentiment_list.append(sentiment) 
            except Exception as e:
                #traceback.print_exc()
                self.docker_scraping_logger.info(f"Web 컨텐츠(sentiments) 파싱 실패({contentsVO.contentsOrgId},{contentsVO.categoryId})")
                self.docker_scraping_logger.error(traceback.format_exc())
                pass 
        
        contentsVO.metaSucYN = "Y"            
        # 안전하게 값 변환
        predKeywordsDict: Dict[str, float] = {}           
        if result_analysis["predkeywords"]: 
            for key, value in result_analysis["predkeywords"].items():
                try:
                    predKeywordsDict[key] = float(value)  
                except ValueError:
                    predKeywordsDict[key] = 0  # 변환 실패 시 기본값 설정

        contentsVO.contentsMeta = ContentsMeta(
            keywords = result_analysis["keyword"],
            predKeywords = predKeywordsDict,
            shortSummary = result_analysis["short_summary"],
            longSummary = result_analysis["long_summary"],
            sentiments= sentiment_list, 
            errorInfo=None
            ) 
            
        return contentsVO      
 
    def generate_imageId(self, contentsVO:ContentsVO)-> ContentsVO:
        
        try:
            if contentsVO is not None and contentsVO.contentsMeta is not None and contentsVO.contentsMeta.predKeywords is not None:
                for key,value in contentsVO.contentsMeta.predKeywords.items():    
                    contentsVO.imageId = ContentsImageService().recommendKeywordImage(key)
                    if contentsVO.imageId is not None:
                        break     

            #타이틀과 유사도측정하여 이미지 할당 
            if contentsVO.imageId is None:
                title = contentsVO.title
                predefineKeyword = PredefineKeywordService().getKeywordList()
                bestKeywordList= SimularityChecker().best_keyword_of_title(title, predefineKeyword)
                if bestKeywordList is not None and len(bestKeywordList) > 0:
                    contentsVO.imageId = ContentsImageService().recommendKeywordImage(bestKeywordList[0])
                    
            if contentsVO.imageId is None:
                contentsVO.imageId = ContentsImageService().recommendImage()    

        except Exception as e :
            contentsVO.imageId = ContentsImageService().recommendImage()
            self.docker_scraping_logger.info(f"이미지id 생성 실패 ({contentsVO.contentsOrgId},{contentsVO.categoryId})")
            self.docker_scraping_logger.error(traceback.format_exc())

        return contentsVO          
        
    def generateSentiment(self, json_parse) -> List[SentimentInfo]:        
        sentiment_list = []

        for data in json_parse:
            sentimentInfo = SentimentInfo()
            sentimentInfo.orgName = data.get('orgName', None)
            sentimentInfo.positiveRatio = data.get('positiveRatio', None)
            sentimentInfo.negativeRatio = data.get('negativeRatio', None)
            sentimentInfo.reason = data.get('reason', None)

            sentiment_list.append(sentimentInfo)

        return sentiment_list

    def generateErrorInfo(self, errorYN :str, date :datetime, type:str = None, reason=None) -> ErrorInfo:
        
        errorInfo = ErrorInfo()
        errorInfo.errorYN=errorYN,            
        errorInfo.type=type
        errorInfo.date=date
        errorInfo.reason=reason
        
        return errorInfo


    def test_raw(self):
        
        isSuccess = True
        raw_data = f"""
        보도자료
        2024. 1. 18.(목) 06:00
        보도시점 배포 2024. 1. 17.(수)
        < 1.18.(목) 석간 >
        한미 차세대 배터리 협력방안 논의
        - 차세대 배터리 우수기술 보유 기업인 미(美) 쏠리드 파워
        최고운영책임자(COO) 면담
        - 차세대 배터리 분야 공동 연구개발(R&D), 국내 투자 등 협력 방안 논의
        산업통상자원부(장관 안덕근, 이하 산업부) 양병내 통상차관보는 1월 18일(목)
        산업부에 방문한 데릭 존슨(Derek Johnson) 쏠리드파워(Solid Power) 최고
        운영책임자(Chief Operating Officer) 등 기업 대표단을 접견하고, 차세대 배터리
        분야 협력 방안 등을 논의하였다.
        쏠리드파워는 “꿈의 배터리”로 불리는 전고체 배터리 분야 선도기술을
        보유한 미국 기업으로 최근 SK온, 한국전자기술연구원(KETI), 한국산업기술
        기획평가원(KEIT) 등 한국의 민간기업 및 공공연구소 등과 양해각서(MOU)를
        체결하고 공동 연구개발(R&D) 등 협력
        """        
        return isSuccess, raw_data