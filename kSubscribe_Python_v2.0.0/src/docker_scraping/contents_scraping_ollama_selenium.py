import sys
import traceback
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from bson import ObjectId
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
from ksubscribe_server.analysis.analysis_ollama_generate import AnalysisOllamaGenerateCall
from ksubscribe_server.models.contentsMetaResult import ContentsMetaResult
from ksubscribe_share.logger import Logger
from ksubscribe_server.models.contentsMetaResult import ContentsMetaResult
from docker_scraping.web_loader import WebLoaderV3
from docker_scraping.contents_scraping_base import ContentsScrapingBase, CustomScrapException, time_now


class ContentsScrapingOllama(ContentsScrapingBase):
    '''
        selenium을 사용하여 스크래핑하는 코드 - 현재 사용하지 않음. 
    '''

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
    
    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Contents_queue 데이터에 대한 스크래핑 -> 요약, 키워드 추출, 평판, 
    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    
    def crawl_and_analyze_ollama(self):
        """ contents_queue 정보를 읽어서 스크래핑 및 분석하는 main 
        """
        self.docker_scraping_logger.info("--------------Docker_Scraping 시작--------------")

        webLoader = WebLoaderV3()
        driver = get_driver()
        
        ollamaAnalysis = AnalysisOllamaGenerateCall()
        # 수집한 콘텐츠 가져오기
        queueContents: List[ContentsQueueVO] = self.contentsQueueService.find_all()
 
        if(len(queueContents) <= 0): 
            return  
        self.docker_scraping_logger.info(f"Queue range : {len(queueContents)}")
        for index, contentsQueueVO in enumerate(queueContents):  
            self.crawl_and_analyze_one_ollama(contentsQueueVO, webLoader, driver, ollamaAnalysis)      
        driver.quit()
            
        self.docker_scraping_logger.info("--------------Docker_Scraping 완료 --------------")
        pass 
    
    
    def crawl_and_analyze_one_ollama(self, queueContent:ContentsQueueVO, webLoader:WebLoaderV3, driver, ollamaAnalysis:AnalysisOllamaGenerateCall):
        """ contents_queue에서 읽은 하나의 url에 대한 스크래핑 및 분석 
        """
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
            isSuccess, contentsMetaResult = ollamaAnalysis.analysis_main(content=raw_data, pred_keyword_list=self.keyword_name_list, org_name_list=self.org_name_list, mycontents_logger=self.docker_scraping_logger)

            contentsVO = self.generateContentsMeta_ollama( contentsVO, contentsMetaResult)
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
    
    
    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # KDN에서 수집한 데이터에 대한 스크래핑 -> 요약, 키워드 추출, 평판, 
    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    def scrapping_for_exist_contents(self): 
        """
        기구축 contents에 스크래핑 메인 홤수 
        Args:
        Returns:
        Example:
        """         
        self.docker_scraping_logger.info("--------------Docker_Scraping(ollama 사용, 기구축 contents) 시작--------------")
         
        webLoader = WebLoaderV3()
        driver = get_driver()
        analysisOllama = AnalysisOllamaGenerateCall()
       
        #요약, 사전정의 키워드, 평판등을 ollama를 이용하여 할당한다. 
        contentsVOList:List[ContentsVO] = self.contentsService.findContents_exist_contents(100) 
        if(len(contentsVOList) <= 0): 
            return  
                
        self.docker_scraping_logger.info(f"Queue range : {len(contentsVOList)}")
        
        for index, contentsVO in enumerate(contentsVOList): 
            self.scrapping_one_for_exist_contents(contentsVO, webLoader, driver, analysisOllama)        
        
        driver.quit()
        
        self.docker_scraping_logger.info("--------------Docker_Scraping(ollama 사용, 기구축 contents) 완료--------------")
        

    def scrapping_one_for_exist_contents(self, contentsVO:ContentsVO, webLoader:WebLoaderV3, driver, analysisOllama:AnalysisOllamaGenerateCall):
        """
        기구축 contents 하나에 대한 스크래핑, 요약을 처리하는 함수 
        Args:
        Returns:
        Example:
        """              
        if contentsVO is None:
            return  
        
        contentsOrgVO, contentsOrgCategory = self.contentsOrgService.findOrgAndCategory(contentsVO.contentsOrgId, contentsVO.categoryId)       
               
        try:
            
            #Web 컨텐츠 수집 -----------------------------------------------------------------------------------------------------------------------------------------
            contentsVO.rawCollectDt = datetime.now()
            self.docker_scraping_logger.info(f"Web 컨텐츠 수집 시작({contentsVO.contentsOrgId},{contentsVO.categoryId}) : {contentsVO.url}-----------------")
            
            scrappingPass = False
            if contentsOrgCategory.cateId == "B0010":
                #스크래핑을 이미했어도, 네이버의 경우는 다시한다. 
                isSuccess, raw_data = webLoader.loadContents_naver_contents(contentsVO.url) 
            else: 
                #스크래핑을 이미했으면 다시할 필요없음. 
                if contentsVO.rawCollectSucYN == "N": 
                    isSuccess, raw_data = webLoader.loadContents(contentsVO, contentsOrgVO, contentsOrgCategory,driver) 
                else:
                    scrappingPass = True
                    isSuccess = True
                    raw_data = contentsVO.contentsRaw.contents

            if scrappingPass == False: 
                # Raw 데이터 수집 실패 시 
                if isSuccess == False or raw_data == "" or raw_data == None :
                    self.docker_scraping_logger.info(f"Web 컨텐츠 수집 실패({contentsVO.contentsOrgId},{contentsVO.categoryId}) : {contentsVO.url}")
                    return
                
                # Raw 데이터 수집 성공 시 
                contentsVO.rawCollectSucYN = 'Y'
                contentsVO.contentsRaw = self.generateContentsRaw(contentsVO.title, contents=raw_data, errorInfo=None)
                self.contentsService.update_rawCollect(contentsVO)
                self.docker_scraping_logger.info(f"Web 컨텐츠 수집 성공({contentsVO.contentsOrgId},{contentsVO.categoryId}) : {contentsVO.url}")
            
            
            #요약, 키워드 추출 -----------------------------------------------------------------------------------------------------------------------------------------
            isSuccess, contentsMetaResult = analysisOllama.analysis_main(raw_data, pred_keyword_list=self.keyword_name_list, org_name_list=self.org_name_list, mycontents_logger=self.docker_scraping_logger)                        

            contentsVO.metaSucYN = contentsMetaResult.metaSucYN
            contentsVO.metaAnalyzeDt = contentsMetaResult.metaAnalyzeDt
            contentsVO.contentsMeta = contentsMetaResult.contentsMeta            
            contentsVO = self.generate_imageId(contentsVO)

            if contentsMetaResult.summarySucYN == "Y" or contentsMetaResult.sentimentSucYN == "Y":
                self.contentsService.update_metaAnalyze(contentsVO)
                self.docker_scraping_logger.info(f"ollama 요약 성공({contentsOrgVO.orgId},{contentsOrgCategory.cateId}) : {contentsVO.url}")
            else:
                self.docker_scraping_logger.info(f"ollama 요약 실패({contentsOrgVO.orgId},{contentsOrgCategory.cateId}) : {contentsVO.url}")

            #평판분석 -------------------------------------------------------------------- 
                
                
        except Exception as e:   
            tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            self.docker_scraping_logger.error(f'error :  {tb_str}')
        
        
if __name__ == "__main__":
    
    dontentsScrapingOllama = ContentsScrapingOllama()
    dontentsScrapingOllama.scrapping_for_exist_contents()

    