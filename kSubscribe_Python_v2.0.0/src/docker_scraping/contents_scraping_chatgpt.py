import sys
import traceback
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from bson import ObjectId
import json
from typing import List, Dict
import time
import asyncio
import json

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
from docker_scraping.contents_scraping_base import ContentsScrapingBase, CustomScrapException, time_now

class ContentsScrapingChatGPT(ContentsScrapingBase):

    commCodeService = CommCodeService()
    contentsOrgService = ContentsOrgService()
    contentsQueueService = ContentsQueueService()    
    contentsService = ContentsService()    
    docker_scraping_logger = Logger().setup_logger(Logger.docker_scraping_logger_name)    
    
    def __init__(self):
        self.orgCodeList = self.commCodeService.get_org_code_list()
        self.cateCodeList = self.commCodeService.get_cate_code_list() 
        
        self.org_list = CommCodeService().get_org_name_list()
        self.keywords = PredefineKeywordService().getKeywordList()
        self.org_name_list = []
        self.keyword_name_list = []

        for org in self.org_list:
            self.org_name_list.append(org["codeName"])
            
        for keyword in self.keywords:
            self.keyword_name_list.append(keyword)
            
        separator = ", "  # 구분자 정의
        self.org_name_list = separator.join(self.org_name_list)    
        self.keyword_name_list = separator.join(self.keyword_name_list)   
    
    def crawl_and_analyze_new(self): 
        self.docker_scraping_logger.info("--------------Docker_Scraping 시작--------------")

        webLoader = WebLoaderV3()
        driver = get_driver()
        
        summaryAnalysis = analysisV2()
        # 수집한 콘텐츠 가져오기
        queueContents: List[ContentsQueueVO] = self.contentsQueueService.find_all()
 
        if(len(queueContents) <= 0): 
            return  
        self.docker_scraping_logger.info(f"Queue range : {len(queueContents)}")
        for index, contentsQueueVO in enumerate(queueContents):  
            self.crawl_and_analyze_one(contentsQueueVO, webLoader, driver, summaryAnalysis)      
        driver.quit()
            
        self.docker_scraping_logger.info("--------------Docker_Scraping 완료 --------------")
    
    def crawl_and_analyze_from_json(self):
        
        self.docker_scraping_logger.info("--------------Docker_Scraping(input : test json) 시작--------------")
        webLoader = WebLoaderV3()
        driver = get_driver()
        summaryAnalysis = analysisV2()
                
        # 저장된 JSON 파일 경로
        file_path = "docker_scraping/mycontents.contents.json"

        # JSON 파일 읽기
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        # 출력
        self.docker_scraping_logger.debug("MongoDB Compass Aggregation Results:")
        for entry in data:
            
            contentsQueueVO = self.generateContentsQueueVO(entry)
            self.crawl_and_analyze_one(contentsQueueVO, webLoader, driver, summaryAnalysis)

        driver.quit()
        self.docker_scraping_logger.info("--------------Docker_Scraping(input : test json) 종료--------------")
            
    def crawl_and_analyze_one(self, queueContent:ContentsQueueVO, webLoader:WebLoaderV3, driver, summaryAnalysis): 
        if queueContent is None:
            return  
            
        if not any(item["code"] == queueContent.contentOrgId for item in self.orgCodeList):
            print(f"orgId : {queueContent.contentOrgId} not exist")                
            return False
        
        if not any(queueContent.cateId == item["code"] for item in self.cateCodeList):
            print(f"cateId : {queueContent.cateId} not exist")                
            return False        
        
        contentsOrgVO, contentsOrgCategory = self.contentsOrgService.findOrgAndCategory(queueContent.contentOrgId, queueContent.cateId)
        contentsVO = self.generateContentVO(queueContent)
         
        try:
            
            #Web 컨텐츠 수집 ##########################################################             
            contentsVO.rawCollectDt = datetime.now()
            self.docker_scraping_logger.info(f"Web 컨텐츠 수집 시작({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}-----------------")
            isSuccess, raw_data = webLoader.loadContents(contentsVO, contentsOrgVO, contentsOrgCategory,driver) 
            
            # Raw 데이터 수집 실패 시 
            if isSuccess == False or raw_data == "" or raw_data == None :
                self.docker_scraping_logger.info(f"Web 컨텐츠 수집 실패({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}")
                contentsVO.rawCollectSucYN = "N"
                contentsVO.contentsRaw = self.generateContentsRaw(contentsVO.title, 
                                                                  contents=raw_data, 
                                                                  errorInfo=self.generateErrorInfo(errorYN="Y", date=contentsVO.rawCollectDt, type=contentsOrgCategory.collectMethod, reason=None))
                
                #이미지 아이디는 무조건 생성한다.      
                contentsVO = self.generate_imageId(contentsVO)
                BaseQueryService.insert_one(contentsVO)  #디버깅 코드 : ContentsService().insert_contents_todebugcollection(contentsVO)           
                ContentsQueueService().deleteQueue(queueContent._id) 
                self.docker_scraping_logger.info(f"Web 컨텐츠 수집 실패 정보 저장({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}")
                return
            
            # Raw 데이터 수집 성공 시 
            contentsVO.rawCollectSucYN = 'Y'
            contentsVO.contentsRaw = self.generateContentsRaw(contentsVO.title, 
                                                              contents=raw_data, 
                                                              errorInfo=None)
            self.docker_scraping_logger.info(f"Web 컨텐츠 수집 성공({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}")
            
            #요약, 키워드 추출, 평판분석 ##########################################################            
            contentsVO.metaAnalyzeDt = datetime.now() 
            isSuccess, result_analysis = summaryAnalysis.analysis(content=raw_data, pred_keyword_list=self.keyword_name_list, org_name_list=self.org_name_list, mycontents_logger=self.docker_scraping_logger)

            contentsVO = self.generateContentsMeta_version2(isSuccess, contentsVO, result_analysis)
            if contentsVO.metaSucYN == "Y":
                ContentsCollectDailyHistoryService().inc_daily_scrapping_cnt()
                self.docker_scraping_logger.info(f"Contents 요약 성공({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}")
            else:
                self.docker_scraping_logger.info(f"Contents 요약 실패({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}")
                #여기서 ollama 또는 nlp 연결하여 본다. 
                
                
        except Exception as e:   
            tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            self.docker_scraping_logger.error(f'error :  {tb_str}')
        
        
        #이미지 아이디는 무조건 생성한다.      
        contentsVO = self.generate_imageId(contentsVO)
        try:
            BaseQueryService.insert_one(contentsVO)
            ContentsQueueService().deleteQueue(queueContent._id) 
            self.docker_scraping_logger.info(f"Web 컨텐츠 수집/요약 성공 정보 저장({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}")
        except Exception as e : 
            pass 
    

if __name__ == "__main__":
    
    dontentsScrapingChatGPT = ContentsScrapingChatGPT()
    dontentsScrapingChatGPT.crawl_and_analyze_new()
    
    

    