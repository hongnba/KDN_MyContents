import sys
import traceback
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from bson import ObjectId
from typing import List, Dict 
import time
import asyncio
import json
import re
import pytz
import os
from pathlib import Path


#from docker_scraping
from docker_collect.driver_utils import get_driver
from ksubscribe_server.models.model import NewsModel
from ksubscribe_server.models.model import LoadModel
from ksubscribe_server.analysis.analysis_openai_v2 import analysisV2
from ksubscribe_server.similarity.simularity_check import SimularityChecker
from ksubscribe_server.analysis.analysis_ollama_generate import AnalysisOllamaGenerateCall
from ksubscribe_server.models.contentsMetaResult import ContentsMetaResult
from ksubscribe_share.logger import Logger
from ksubscribe_share.db.dbmodelV2.errorInfo import ErrorInfo
from ksubscribe_share.db.service.contentsService import ContentsService
from ksubscribe_share.db.service.contentsCollectDailyHistoryService import ContentsCollectDailyHistoryService
from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO, ContentsRaw, ContentsMeta, SentimentInfo
from ksubscribe_share.db.dbmodelV2.commCodeVO import CommCodeVO
import ksubscribe_share.config as CONF
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
from ksubscribe_share.db.data_migration.data_validator import data_validator
# from ksubscribe_share.db.json_backup_utils import JsonBackupUtils  # Commented out - file was deleted
from docker_scraping.web_loader import WebLoaderV3
from docker_scraping.contents_scraping_base import ContentsScrapingBase, CustomScrapException, time_now
from docker_scraping.ai_scraping.trafilaura import TrafilauraScraper


class ContentsScrapingOllamaTrafilaura(ContentsScrapingBase):
    '''        
        현재 사용하는 매우 중요한 코드 
        Trafilaura을 사용하여 스크래핑하는 코드 - 현재 이 클래스를 이용하여 스크래핑하고 있음.
    '''
    commCodeService = CommCodeService()
    contentsOrgService = ContentsOrgService()
    contentsQueueService = ContentsQueueService()    
    contentsService = ContentsService()    
    trafilauraScraper = TrafilauraScraper()
    docker_scraping_logger = Logger().setup_logger(Logger.docker_scraping_logger_name)    
    docker_scraping_result_logger = Logger().setup_logger(Logger.docker_scraping_result_logger_name)    
    def __init__(self):
        self.orgCodeList = self.commCodeService.get_org_code_list()
        self.cateCodeList = self.commCodeService.get_cate_code_list() 
        
        self.org_list = CommCodeService().get_org_name_list()
        self.keywords = PredefineKeywordService().getKeywordList()
        self.org_name_list = []
        self.keyword_name_list = []
        # 한번 실행 시 scrapping cnt 
        self.scrapping_cnt_for_once = 0
        # 한번 실행 시 요약분석cnt 
        self.analysis_cnt_for_once = 0
        for org in self.org_list:
            self.org_name_list.append(org["codeName"])
            
        for keyword in self.keywords:
           # self.keyword_name_list.append(keyword + " 기술")
            self.keyword_name_list.append(keyword)
            
        separator = ", "  # 구분자 정의
        self.org_name_list = separator.join(self.org_name_list)    
        self.keyword_name_list = separator.join(self.keyword_name_list)
        
        # MongoDB connection for backup collection
        self.mongo_manager = MongoManager()
        self.db = self.mongo_manager.dataBase
        self.contents_backup_collection = self.db['contents_backup']
        
        # JSON export settings
        self.export_to_json = True
        self.json_export_dir = "/app/exports"
        Path(self.json_export_dir).mkdir(parents=True, exist_ok=True)
        
        # Control whether to remove items from contents_queue after processing
        self.delete_queue_after_processing = True   
    
    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Contents_queue 데이터에 대한 스크래핑 -> 요약, 키워드 추출, 평판, 
    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    def scrape_content(self, queueContent: ContentsQueueVO, webLoader: WebLoaderV3, driver):
        """
        스크래핑 로직만 분리 (테스트 및 재사용 목적)
        Returns: (isSuccess, text, title, contentsVO)
        """
        if queueContent is None:
            return False, None, None, None
            
        if not any(item["code"] == queueContent.contentOrgId for item in self.orgCodeList):
            print(f"orgId : {queueContent.contentOrgId} not exist")                
            return False, None, None, None
        
        if not any(queueContent.cateId == item["code"] for item in self.cateCodeList):
            print(f"cateId : {queueContent.cateId} not exist")                
            return False, None, None, None
        
        contentsOrgVO, contentsOrgCategory = self.contentsOrgService.findOrgAndCategory(queueContent.contentOrgId, queueContent.cateId)
        contentsVO = self.generateContentVO(queueContent)
        contentsVO.rawCollectDt = datetime.now()
        
        self.docker_scraping_logger.info(f"Web 컨텐츠 수집 시작({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}-----------------")
        
        text = ""
        title = ""
        isSuccess = False
        
        try:
            if contentsOrgCategory.cateId == "B0010":
                isSuccess, title, text = self.trafilauraScraper.get_newbody(contentsVO.url) 
            else: 
                collect_method = contentsOrgCategory.collectMethod.upper() if contentsOrgCategory.collectMethod else 'TEXTINBODY'
                
                if collect_method == 'ONLYPDF':
                    isSuccess, text = webLoader.loadContents(contentsVO, contentsOrgVO, contentsOrgCategory,driver) 
                elif collect_method == 'TEXTINTAG':
                    isSuccess, title, text = self.trafilauraScraper.get_newbody(contentsVO.url) 
                elif collect_method == 'TEXTINBODY': 
                    isSuccess, text = webLoader.loadContents(contentsVO, contentsOrgVO, contentsOrgCategory,driver)
                else:
                    isSuccess, text = webLoader.loadContents(contentsVO, contentsOrgVO, contentsOrgCategory,driver)
            
            return isSuccess, text, title, contentsVO
            
        except Exception as e:
            self.docker_scraping_logger.error(f"Scraping error: {e}")
            return False, None, None, contentsVO
    
    def crawl_and_analyze_ollama(self):
        """ contents_queue 정보를 읽어서 스크래핑 및 분석하는 main 
        """
        self.docker_scraping_logger.info("--------------Docker_Scraping 시작 - this one!!! --------------")
        self.docker_scraping_result_logger.info("--------------Docker_Scraping 시작 --------------")         

        webLoader = WebLoaderV3()
        driver = get_driver()
        validater = data_validator()
        ollamaAnalysis = AnalysisOllamaGenerateCall()
        # 수집한 콘텐츠 가져오기
        queueContents: List[ContentsQueueVO] = self.contentsQueueService.find_all()
        
        # pubDt 필터링 제거: 수집 단계(openapi_collector.py)에서 이미 필터링되었으므로 스크래핑 단계에서는 모든 기사 처리
 
        print(f"queueContents : {len(queueContents)}")
        if(len(queueContents) == 0): 
            self.docker_scraping_logger.info(f"Queue is empty")
            return  
        
        self.docker_scraping_logger.info(f"Queue range : {len(queueContents)}")
        for index, contentsQueueVO in enumerate(queueContents):  
            self.crawl_and_analyze_one_ollama(contentsQueueVO, webLoader, driver, ollamaAnalysis)      
        
        driver.quit()
        
        
        # 성공 개수 로깅
        self.docker_scraping_logger.info(f"Docker_Scraping summary")
        self.docker_scraping_logger.info(f"기존 Queue : {len(queueContents)}")
        self.docker_scraping_logger.info(f"스크랩 성공 개수 : {self.scrapping_cnt_for_once}")
        self.docker_scraping_logger.info(f"요약 및 분석 성공 개수 : {self.analysis_cnt_for_once}")
        self.docker_scraping_logger.info("--------------Docker_Scraping 완료 --------------") 
        
        # 성공 개수 로깅
        self.docker_scraping_result_logger.info(f"Docker_Scraping summary")
        self.docker_scraping_result_logger.info(f"기존 Queue : {len(queueContents)}")
        self.docker_scraping_result_logger.info(f"스크랩 성공 개수 : {self.scrapping_cnt_for_once}")
        self.docker_scraping_result_logger.info(f"요약 및 분석 성공 개수 : {self.analysis_cnt_for_once}")
        self.docker_scraping_result_logger.info("--------------Docker_Scraping 완료 --------------")         
        pass 
    
    #25.03.13 분석용 함수.당분간 _test함수 유지     
    def crawl_and_analyze_one_ollama_test(self, queueContent:ContentsQueueVO, webLoader:WebLoaderV3, driver, ollamaAnalysis:AnalysisOllamaGenerateCall):
        """ contents_queue에서 읽은 하나의 url에 대한 스크래핑 및 분석 
        """
        if queueContent is None:
            self.docker_scraping_logger.info(f"queueContent is None")
            return  
        if ContentsService().isExistContents(queueContent.url):
            self.docker_scraping_logger and self.docker_scraping_logger.info(f"이미 ContentsDB에 존재하는 contents입니다. {queueContent.url}")
            
            # JSON backup: Save queue content even if it already exists in DB
            # JsonBackupUtils.save_to_json(queueContent, "contents_queue", "already_exists", self.docker_scraping_logger)  # Commented out - file was deleted
            
            return None
            
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
            
            #isSuccess, raw_data = webLoader.loadContents(contentsVO, contentsOrgVO, contentsOrgCategory,driver) 
            
            if contentsOrgCategory.cateId == "B0010":
                isSuccess, title, text = self.trafilauraScraper.get_newbody(contentsVO.url) 
            else: 
                if contentsOrgCategory.collectMethod.upper() == 'onlyPdf'.upper():
                    isSuccess, text = webLoader.loadContents(contentsVO, contentsOrgVO, contentsOrgCategory,driver) 
                elif contentsOrgCategory.collectMethod.upper() == 'textInTag'.upper():
                    isSuccess, title, text = self.trafilauraScraper.get_newbody(contentsVO.url) 
                elif contentsOrgCategory.collectMethod.upper() == 'textInBody'.upper(): 
                    isSuccess, text = webLoader.loadContents(contentsVO, contentsOrgVO, contentsOrgCategory,driver) 
            
            
            # Raw 데이터 수집 실패 시 
            if isSuccess == False or text == "" or text == None :
                self.docker_scraping_logger.info(f"Web 컨텐츠 수집 실패({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}")
                contentsVO.rawCollectSucYN = "N"
                contentsVO.contentsRaw = self.generateContentsRaw(contentsVO.title, 
                                                                  contents=text, 
                                                                  errorInfo=self.generateErrorInfo(errorYN="Y", date=contentsVO.rawCollectDt, type=contentsOrgCategory.collectMethod, reason=None))
                
                #이미지 아이디는 무조건 생성한다.      
                contentsVO = self.generate_imageId(contentsVO)
                BaseQueryService.insert_one(contentsVO)  #디버깅 코드 : ContentsService().insert_contents_todebugcollection(contentsVO)           
                ContentsQueueService().deleteQueue(queueContent._id) 
                self.docker_scraping_logger.info(f"Web 컨텐츠 수집 실패 정보 저장({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}")
                return 
            # Raw 데이터 수집 성공 시 
            self.scrapping_cnt_for_once +=1
            contentsVO.rawCollectSucYN = 'Y'
            contentsVO.contentsRaw = self.generateContentsRaw(contentsVO.title, 
                                                              contents=text, 
                                                              errorInfo=None)
            
            # JSON backup: Save ContentsRaw data after scraping
            # JsonBackupUtils.save_contents_raw(contentsVO.contentsRaw, self.docker_scraping_logger)  # Commented out - file was deleted
            
            self.docker_scraping_logger.info(f"Web 컨텐츠 수집 성공({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}")
            
            ONLY_SCRAPPING = False 
            if ONLY_SCRAPPING: 
                contentsVO.metaSucYN = "N"
                contentsVO.metaAnalyzeDt = datetime.now() 
                contentsVO.contentsMeta = ContentsMeta(
                    errorInfo =  self.generateErrorInfo(errorYN="N",date=contentsVO.metaAnalyzeDt ,reason="skip") 
                )   
                pass
            else : 
                
                # #요약, 키워드 추출, 평판분석 ##########################################################            
                contentsVO.metaAnalyzeDt = datetime.now() 
                # title 추가 
                isSuccess, contentsMetaResult,summary,sentiment,error_ollamaMetaResult = ollamaAnalysis.analysis_main(queueContent=queueContent, title=queueContent.title, content=text, pred_keyword_list=self.keyword_name_list, org_name_list=self.org_name_list, mycontents_logger=self.docker_scraping_logger)            
                #isSuccess, contentsMetaResult,summary,sentiment,error_ollamaMetaResult = ollamaAnalysis.analysis_main(content=text, pred_keyword_list=self.keyword_name_list, org_name_list=self.org_name_list, mycontents_logger=self.docker_scraping_logger)            
                if isSuccess:
                    contentsVO = self.generateContentsMeta_ollama( contentsVO, contentsMetaResult)
                else:
                    contentsVO = self.generateContentsMeta_ollama( contentsVO, error_ollamaMetaResult)
                if contentsVO.metaSucYN == "Y":
                    ContentsCollectDailyHistoryService().inc_daily_scrapping_cnt()
                    self.analysis_cnt_for_once += 1
                    self.docker_scraping_logger.info(f"Contents 요약 및 분석 성공({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}")
                else:
                    self.docker_scraping_logger.info(f"컨텐츠 요약 실패 원문 : sumary : {summary} \n sentiments: {sentiment}")
                    self.docker_scraping_logger.info(f"Contents 요약 및 분석 실패({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}")
                #여기서 ollama 또는 nlp 연결하여 본다. 
                
        except Exception as e:   
            pass 
            #tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            #self.docker_scraping_logger.error(f'error :  {tb_str}')
         
        #이미지 아이디는 무조건 생성한다.      
        contentsVO = self.generate_imageId(contentsVO)
        try:
            BaseQueryService.insert_one(contentsVO)
            
            # Export to JSON after successful insertion
            self.export_content_to_json(contentsVO)
            
            if self.delete_queue_after_processing:
                ContentsQueueService().deleteQueue(queueContent._id) 
            self.docker_scraping_logger.info(f"Web 컨텐츠 수집/요약 정보 저장({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}")
        except Exception as e : 
            tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            self.docker_scraping_logger.error(f'error :  {tb_str}')
            self.docker_scraping_logger.info(f"Web 컨텐츠 수집/요약 정보 저장 실패({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}")
            pass 

    
    def crawl_and_analyze_one_ollama(self, queueContent:ContentsQueueVO, webLoader:WebLoaderV3, driver, ollamaAnalysis:AnalysisOllamaGenerateCall):
        """ contents_queue에서 읽은 하나의 url에 대한 스크래핑 및 분석 
        """
        if queueContent is None:
            return  
        # if ContentsService().isExistContents(queueContent.url):
        #     self.docker_scraping_logger and self.docker_scraping_logger.info(f"이미 ContentsDB에 존재하는 contents입니다. {queueContent.url}")
        #     return None
            
        if not any(item["code"] == queueContent.contentOrgId for item in self.orgCodeList):
            print(f"orgId : {queueContent.contentOrgId} not exist")                
            return False
        
        if not any(queueContent.cateId == item["code"] for item in self.cateCodeList):
            print(f"cateId : {queueContent.cateId} not exist")                
            return False        
        
        contentsOrgVO, contentsOrgCategory = self.contentsOrgService.findOrgAndCategory(queueContent.contentOrgId, queueContent.cateId)
        contentsVO = self.generateContentVO(queueContent)
        
        total_start = time.time()  # 전체 처리 시작 시간
         
        try:
            
            #Web 컨텐츠 수집 ##########################################################             
            contentsVO.rawCollectDt = datetime.now()
            self.docker_scraping_logger.info(f"Web 컨텐츠 수집 시작({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}-----------------")
            
            scraping_start = time.time()
            #isSuccess, raw_data = webLoader.loadContents(contentsVO, contentsOrgVO, contentsOrgCategory,driver) 
            
            if contentsOrgCategory.cateId == "B0010":
                isSuccess, title, text = self.trafilauraScraper.get_newbody(contentsVO.url) 
            else: 
                if contentsOrgCategory.collectMethod.upper() == 'onlyPdf'.upper():
                    isSuccess, text = webLoader.loadContents(contentsVO, contentsOrgVO, contentsOrgCategory,driver) 
                elif contentsOrgCategory.collectMethod.upper() == 'textInTag'.upper():
                    isSuccess, title, text = self.trafilauraScraper.get_newbody(contentsVO.url) 
                elif contentsOrgCategory.collectMethod.upper() == 'textInBody'.upper(): 
                    isSuccess, text = webLoader.loadContents(contentsVO, contentsOrgVO, contentsOrgCategory,driver) 
            
            scraping_end = time.time()
            scraping_duration = scraping_end - scraping_start 
            
            
            # Raw 데이터 수집 실패 시 
            if isSuccess == False or text == "" or text == None :
                self.docker_scraping_logger.info(f"Web 컨텐츠 수집 실패({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}")
                contentsVO.rawCollectSucYN = "N"
                contentsVO.contentsRaw = self.generateContentsRaw(contentsVO.title, 
                                                                  contents=text, 
                                                                  errorInfo=self.generateErrorInfo(errorYN="Y", date=contentsVO.rawCollectDt, type=contentsOrgCategory.collectMethod, reason=None))
                
                #이미지 아이디는 무조건 생성한다.      
                contentsVO = self.generate_imageId(contentsVO)
                BaseQueryService.insert_one(contentsVO)  #디버깅 코드 : ContentsService().insert_contents_todebugcollection(contentsVO)           
                ContentsQueueService().deleteQueue(queueContent._id) 
                self.docker_scraping_logger.info(f"Web 컨텐츠 수집 실패 정보 저장({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}")
                return 
            # Raw 데이터 수집 성공 시 
            self.scrapping_cnt_for_once +=1
            contentsVO.rawCollectSucYN = 'Y'
            contentsVO.contentsRaw = self.generateContentsRaw(contentsVO.title, 
                                                              contents=text, 
                                                              errorInfo=None)
            
            # JSON backup: Save ContentsRaw data after scraping
            # JsonBackupUtils.save_contents_raw(contentsVO.contentsRaw, self.docker_scraping_logger)  # Commented out - file was deleted
            
            self.docker_scraping_logger.info(f"Web 컨텐츠 수집 성공({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}")
            
            ONLY_SCRAPPING = False 
            if ONLY_SCRAPPING: 
                contentsVO.metaSucYN = "N"
                contentsVO.metaAnalyzeDt = datetime.now() 
                contentsVO.contentsMeta = ContentsMeta(
                    errorInfo =  self.generateErrorInfo(errorYN="N",date=contentsVO.metaAnalyzeDt ,reason="skip") 
                )   
                pass
            else : 
                
                # #요약, 키워드 추출, 평판분석 ##########################################################            
                contentsVO.metaAnalyzeDt = datetime.now() 
                analysis_start = time.time()
                isSuccess, contentsMetaResult,summary,sentiment,error_ollamaMetaResult, durations = ollamaAnalysis.analysis_main(queueContent=queueContent, content=text, pred_keyword_list=self.keyword_name_list, org_name_list=self.org_name_list, mycontents_logger=self.docker_scraping_logger)            
                analysis_end = time.time()
                analysis_duration = analysis_end - analysis_start
                if isSuccess:
                    contentsVO = self.generateContentsMeta_ollama( contentsVO, contentsMetaResult)
                else:
                    contentsVO = self.generateContentsMeta_ollama( contentsVO, error_ollamaMetaResult)
                # Set durations
                if contentsVO.contentsMeta:
                    contentsVO.contentsMeta.scrapingDuration = scraping_duration
                    contentsVO.contentsMeta.analysisDuration = analysis_duration
                if contentsVO.metaSucYN == "Y":
                    ContentsCollectDailyHistoryService().inc_daily_scrapping_cnt()
                    self.analysis_cnt_for_once += 1
                    self.docker_scraping_logger.info(f"Contents 요약 및 분석 성공({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}")
                else:
                    self.docker_scraping_logger.info(f"컨텐츠 요약 실패 원문 : sumary : {summary} \n sentiments: {sentiment}")
                    self.docker_scraping_logger.info(f"Contents 요약 및 분석 실패({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}")
                #여기서 ollama 또는 nlp 연결하여 본다. 
                
        except Exception as e:   
            tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            self.docker_scraping_logger.error(f'error :  {tb_str}')
         
        #이미지 아이디는 무조건 생성한다.      
        contentsVO = self.generate_imageId(contentsVO)
        total_end = time.time()
        total_duration = total_end - total_start
        if contentsVO.contentsMeta:
            contentsVO.contentsMeta.totalProcessingDuration = total_duration
        try:
            #2025.03.18 콘텐츠 저장되지 않도록 수정 
            if contentsVO and contentsVO.contentsRaw:
                contentsVO.contentsRaw.contents = ""            
            
            # JSON backup: Save final Contents data
            # JsonBackupUtils.save_contents(contentsVO, self.docker_scraping_logger)  # Commented out - file was deleted
            
            BaseQueryService.insert_one(contentsVO)
            
            # Export to JSON after successful insertion
            self.export_content_to_json(contentsVO)
            
            # 2025-12-30 분석 성공한 기사는 분석 대상에서 제외
            if self.delete_queue_after_processing:
                # 분석이 성공한 경우만 제거
                if contentsVO.rawCollectSucYN == "Y" and contentsVO.metaSucYN == "Y":
                    ContentsQueueService().deleteQueue(queueContent._id) 
            self.docker_scraping_logger.info(f"Web 컨텐츠 수집/요약 정보 저장({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}")
        except Exception as e : 
            tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            self.docker_scraping_logger.error(f'error :  {tb_str}')
            self.docker_scraping_logger.info(f"Web 컨텐츠 수집/요약 정보 저장 실패({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}")
            pass 
          
    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # KDN에서 수집한 데이터에 대한 스크래핑 -> 요약, 키워드 추출, 평판, 
    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    def scrapping_for_exist_contents(self,start_date,end_date, is_all:bool): 
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
        if is_all == False:
            contentsVOList:List[ContentsVO] = self.contentsService.findContents_rawCollectSucYN_is_false(-1) 
        else:
            pass  
            #contentsVOList:List[ContentsVO] = self.contentsService.findTodaySucFalseContents(start_date=start_date,end_date=end_date) 


        if(len(contentsVOList) <= 0): 
            return  
                
        self.docker_scraping_logger.info(f"Contents len : {len(contentsVOList)}")
        
        for index, contentsVO in enumerate(contentsVOList): 
            self.scrapping_one_for_exist_contents(contentsVO, webLoader, driver)        
        
        driver.quit()
        
        self.docker_scraping_logger.info("--------------Docker_Scraping(ollama 사용, 기구축 contents) 완료--------------")
        

    def scrapping_one_for_exist_contents(self, contentsVO:ContentsVO, webLoader:WebLoaderV3, driver):
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
            
            if contentsOrgCategory.cateId == "B0010":
                isSuccess, title, text = self.trafilauraScraper.get_newbody(contentsVO.url) 
            else: 
                if contentsOrgCategory.collectMethod.upper() == 'onlyPdf'.upper():
                    isSuccess, text = webLoader.loadContents(contentsVO, contentsOrgVO, contentsOrgCategory,driver) 
                elif contentsOrgCategory.collectMethod.upper() == 'textInTag'.upper():
                    isSuccess, title, text = self.trafilauraScraper.get_newbody(contentsVO.url) 
                elif contentsOrgCategory.collectMethod.upper() == 'textInBody'.upper(): 
                    isSuccess, text = webLoader.loadContents(contentsVO, contentsOrgVO, contentsOrgCategory,driver) 

            # Raw 데이터 수집 실패 시 
            if isSuccess == False or text == "" or text == None :
                self.docker_scraping_logger.info(f"Web 컨텐츠 수집 실패({contentsVO.contentsOrgId},{contentsVO.categoryId}) : {contentsVO.url}")
                return
            
            # Raw 데이터 수집 성공 시 
            contentsVO.rawCollectSucYN = 'Y'
            contentsVO.contentsRaw = self.generateContentsRaw(contentsVO.title, contents=text, errorInfo=None)
            self.contentsService.update_rawCollect(contentsVO)
            self.docker_scraping_logger.info(f"Web 컨텐츠 수집 성공({contentsVO.contentsOrgId},{contentsVO.categoryId}) : {contentsVO.url}")
            
                
        except Exception as e:   
            tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            self.docker_scraping_logger.error(f'error :  {tb_str}')
            self.docker_scraping_logger.info(f"Web 컨텐츠 수집 Exception({contentsVO.contentsOrgId},{contentsVO.categoryId}) : {contentsVO.url} :  {tb_str}")
            
            

    def analysis_for_exist_contents(self,start_date,end_date, is_all:bool): 
        """
        기구축 contents에 요약, 키워드 추출, 평판 분석 메인 홤수 
        Args:
        Returns:
        Example:
        """         
        self.docker_scraping_logger.info("--------------요약, 키워드 추출, 평판 분석 (ollama 사용, 기구축 contents) 시작--------------")
         
        analysisOllama = AnalysisOllamaGenerateCall()
       
        #요약, 사전정의 키워드, 평판등을 ollama를 이용하여 할당한다. 
        if is_all == True:
            contentsVOList:List[ContentsVO] = self.contentsService.findContents_rawCollectSucYN_is_true(-1) 
        else: 
            contentsVOList:List[ContentsVO] = self.contentsService.findSucRawContents(start_date=start_date,end_date=end_date,sucYN="Y") 

        # if(len(contentsVOList) <= 0): 
        #     return  
                
        self.docker_scraping_logger.info(f"Contents len : {len(contentsVOList)}")
        
        for index, contentsVO in enumerate(contentsVOList): 
            self.analysis_one_for_exist_contents(contentsVO, analysisOllama)
        
        self.docker_scraping_logger.info("--------------요약, 키워드 추출, 평판 분석 (ollama 사용, 기구축 contents) 완료--------------")
        


    def new_image_id(self, contentsVO:ContentsVO):
        """
        이미지 id를 다시 할당 
        Args:
        Returns:
        Example:
        """            
        if contentsVO is None or contentsVO.contentsRaw is None or contentsVO.contentsRaw.contents == "":
            self.docker_scraping_logger.info(f"Web 컨텐츠 empty({contentsVO.contentsOrgId},{contentsVO.categoryId}) : {contentsVO.url}")
            return  
        
        try:
            #이미지 id 수정 -----------------------------------------------------------------------------------------------------------------------------------------
            contentsVO = self.generate_imageId(contentsVO)
            self.contentsService.update_imageId(contentsVO)
            self.docker_scraping_logger.info(f"컨텐츠 id 수정 완료 : {contentsVO.url}")
            #평판분석 -------------------------------------------------------------------- 
                
                
        except Exception as e:   
            tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            self.docker_scraping_logger.error(f'error :  {tb_str}')        
                      

    def analysis_one_for_exist_contents(self, contentsVO:ContentsVO, analysisOllama:AnalysisOllamaGenerateCall):
        """
        기구축 contents 하나에 대한 스크래핑, 요약을 처리하는 함수 
        Args:
        Returns:
        Example:
        """              
        if contentsVO is None or contentsVO.contentsRaw is None or contentsVO.contentsRaw.contents == "":
            self.docker_scraping_logger.info(f"Web 컨텐츠 empty({contentsVO.contentsOrgId},{contentsVO.categoryId}) : {contentsVO.url}")
            return  
        
        contentsOrgVO, contentsOrgCategory = self.contentsOrgService.findOrgAndCategory(contentsVO.contentsOrgId, contentsVO.categoryId)       
               
        try:
            text = contentsVO.contentsRaw.contents
            
            #요약, 키워드 추출 -----------------------------------------------------------------------------------------------------------------------------------------            
            contentsVO.metaAnalyzeDt = datetime.now() 
            isSuccess, contentsMetaResult,summary,sentiment, error_ollamaMetaResult = analysisOllama.analysis_main(content=text, pred_keyword_list=self.keyword_name_list, org_name_list=self.org_name_list, mycontents_logger=self.docker_scraping_logger)            

            # if contentsMetaResult.metaSucYN == "Y":
            #     self.docker_scraping_logger.info(f"Contents ollama 응답 성공 ({contentsVO.contentsOrgId},{contentsVO.categoryId}) : {contentsVO.url}")#
            # else:  
            #     self.docker_scraping_logger.info(f"Contents ollama 응답 실패 ({contentsVO.contentsOrgId},{contentsVO.categoryId}) : {contentsVO.url}")
            if isSuccess:
                contentsVO = self.generateContentsMeta_ollama( contentsVO, contentsMetaResult)
            else:
                contentsVO = self.generateContentsMeta_ollama( contentsVO, error_ollamaMetaResult)
                
            if contentsVO.metaSucYN == "Y":
                contentsVO = self.generate_imageId(contentsVO)
                self.contentsService.update_metaAnalyze(contentsVO)
                self.docker_scraping_logger.info(f"Contents 요약 및 분석 성공({contentsVO.contentsOrgId},{contentsVO.categoryId}) : {contentsVO.url}")
            else:
                #self.docker_scraping_logger.info(f"컨텐츠 요약 실패 원문 : sumary : {summary} \n sentiments: {sentiment}")
                self.docker_scraping_logger.info(f"Contents 요약 및 분석 실패({contentsVO.contentsOrgId},{contentsVO.categoryId}) : {contentsVO.url}")
                
            #평판분석 -------------------------------------------------------------------- 
                
                
        except Exception as e:   
            tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            self.docker_scraping_logger.error(f'error :  {tb_str}')            
    
    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Process URLs from today.json and save to contents_backup collection
    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    
    def extract_urls_from_today_json(self, file_path: str = "/app/today.json") -> List[Dict]:
        """
        Extract URLs and metadata from today.json file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract URLs using regex
            url_pattern = r'"url"\s*:\s*"([^"]+)"'
            urls = re.findall(url_pattern, content)
            
            # Extract titles
            title_pattern = r'"title"\s*:\s*"([^"]+)"'
            titles = re.findall(title_pattern, content)
            
            # Extract organization info
            org_id_pattern = r'"contentsOrgId"\s*:\s*"([^"]+)"'
            org_ids = re.findall(org_id_pattern, content)
            
            org_name_pattern = r'"contentsOrgName"\s*:\s*"([^"]+)"'
            org_names = re.findall(org_name_pattern, content)
            
            # Extract category info
            category_id_pattern = r'"categoryId"\s*:\s*"([^"]+)"'
            category_ids = re.findall(category_id_pattern, content)
            
            category_name_pattern = r'"categoryName"\s*:\s*"([^"]+)"'
            category_names = re.findall(category_name_pattern, content)
            
            # Extract publication dates
            pub_dt_pattern = r'"pubDt"\s*:\s*ISODate\("([^"]+)"\)'
            pub_dates = re.findall(pub_dt_pattern, content)
            
            # Combine all data
            articles = []
            for i in range(len(urls)):
                article = {
                    'url': urls[i],
                    'title': titles[i] if i < len(titles) else '',
                    'contentsOrgId': org_ids[i] if i < len(org_ids) else 'A0010',
                    'contentsOrgName': org_names[i] if i < len(org_names) else '한국전력공사(주)',
                    'categoryId': category_ids[i] if i < len(category_ids) else 'B0010',
                    'categoryName': category_names[i] if i < len(category_names) else '네이버 뉴스',
                    'pubDt': pub_dates[i] if i < len(pub_dates) else datetime.now().isoformat()
                }
                articles.append(article)
            
            # Remove duplicates based on URL
            unique_articles = []
            seen_urls = set()
            for article in articles:
                if article['url'] not in seen_urls:
                    unique_articles.append(article)
                    seen_urls.add(article['url'])
            
            self.docker_scraping_logger.info(f"Extracted {len(unique_articles)} unique articles from today.json")
            return unique_articles
            
        except Exception as e:
            self.docker_scraping_logger.error(f"Error extracting URLs from today.json: {e}")
            return []

    def process_articles_from_today_json(self):
        """
        Main method to process all articles from today.json and save to contents_backup
        """
        self.docker_scraping_logger.info("Starting processing of articles from today.json")
        
        # Extract articles from today.json
        articles = self.extract_urls_from_today_json()
        
        if not articles:
            self.docker_scraping_logger.error("No articles found in today.json")
            return
        
        # Initialize components
        webLoader = WebLoaderV3()
        driver = get_driver()
        ollamaAnalysis = AnalysisOllamaGenerateCall()
        
        processed_count = 0
        failed_count = 0
        
        for i, article in enumerate(articles):
            try:
                self.docker_scraping_logger.info(f"Processing article {i+1}/{len(articles)}: {article['title'][:50]}...")
                
                # Create ContentsQueueVO from article data
                queue_content = self.create_queue_content_from_article(article)
                
                # Process the article
                success = self.process_single_article_to_backup(queue_content, webLoader, driver, ollamaAnalysis)
                
                if success:
                    processed_count += 1
                    self.docker_scraping_logger.info(f"Successfully processed: {article['title'][:50]}...")
                else:
                    failed_count += 1
                    self.docker_scraping_logger.error(f"Failed to process: {article['title'][:50]}...")
                    
            except Exception as e:
                failed_count += 1
                self.docker_scraping_logger.error(f"Error processing article {i+1}: {e}")
                traceback.print_exc()
        
        self.docker_scraping_logger.info(f"Processing complete. Success: {processed_count}, Failed: {failed_count}")
        
        # Clean up
        if driver:
            driver.quit()

    def create_queue_content_from_article(self, article: Dict) -> ContentsQueueVO:
        """
        Create ContentsQueueVO from article data
        """
        queue_content = ContentsQueueVO()
        queue_content.url = article['url']
        queue_content.title = article['title']
        queue_content.contentOrgId = article['contentsOrgId']
        queue_content.cateId = article['categoryId']
        queue_content.pubDt = datetime.fromisoformat(article['pubDt'].replace('Z', '+00:00'))
        queue_content.collectDt = datetime.now(pytz.UTC)
        queue_content.collectKeyword = "today_json_processing"
        
        return queue_content

    def process_single_article_to_backup(self, queue_content: ContentsQueueVO, webLoader: WebLoaderV3, driver, ollamaAnalysis: AnalysisOllamaGenerateCall) -> bool:
        """
        Process a single article and save to contents_backup collection
        """
        try:
            # Get organization and category info
            contentsOrgVO, contentsOrgCategory = self.contentsOrgService.findOrgAndCategory(queue_content.contentOrgId, queue_content.cateId)
            
            if not contentsOrgVO or not contentsOrgCategory:
                self.docker_scraping_logger.error(f"Could not find org/category for {queue_content.contentOrgId}/{queue_content.cateId}")
                return False
            
            # Create ContentsVO
            contentsVO = self.generateContentVO(queue_content)
            contentsVO.rawCollectDt = datetime.utcnow()
            
            # Scrape content using Trafilaura
            self.docker_scraping_logger.info(f"Scraping content: {queue_content.url}")
            isSuccess, title, raw_data = self.trafilauraScraper.get_newbody(queue_content.url)
            
            if not isSuccess or not raw_data:
                self.docker_scraping_logger.error(f"Failed to scrape content: {queue_content.url}")
                contentsVO.rawCollectSucYN = "N"
                contentsVO.contentsRaw = self.generateContentsRaw(
                    contentsVO.title, 
                    contents=raw_data or "Scraping failed", 
                    errorInfo=self.generateErrorInfo(errorYN="Y", date=contentsVO.rawCollectDt, type="trafilaura", reason="Scraping failed")
                )
            else:
                contentsVO.rawCollectSucYN = "Y"
                contentsVO.contentsRaw = self.generateContentsRaw(contentsVO.title, contents=raw_data)
            
            # Generate image ID
            contentsVO = self.generate_imageId(contentsVO)
            
            # Perform analysis if scraping was successful
            if contentsVO.rawCollectSucYN == "Y":
                self.docker_scraping_logger.info(f"Performing analysis for: {queue_content.url}")
                contentsVO.metaAnalyzeDt = datetime.utcnow()
                
                try:
                    # Perform analysis
                    is_success, analysis_result = ollamaAnalysis.analysis_main(
                        contentsVO.contentsRaw.contents,
                        self.keyword_name_list,
                        self.org_name_list,
                        self.docker_scraping_logger,
                        queue_content
                    )
                    
                    if is_success and analysis_result:
                        contentsVO.metaSucYN = "Y"
                        contentsVO.contentsMeta = self.generateContentsMeta_ollama(contentsVO, analysis_result)
                    else:
                        contentsVO.metaSucYN = "N"
                        contentsVO.contentsMeta = self.generateContentsMeta(contentsVO, "N", None, self.generateErrorInfo(errorYN="Y", date=contentsVO.metaAnalyzeDt, type="ollama", reason="Analysis failed"))
                        
                except Exception as e:
                    self.docker_scraping_logger.error(f"Analysis failed: {e}")
                    contentsVO.metaSucYN = "N"
                    contentsVO.contentsMeta = self.generateContentsMeta(contentsVO, "N", None, self.generateErrorInfo(errorYN="Y", date=contentsVO.metaAnalyzeDt, type="ollama", reason="Analysis failed"))
            else:
                contentsVO.metaSucYN = "N"
                contentsVO.contentsMeta = self.generateContentsMeta(contentsVO, "N", None, self.generateErrorInfo(errorYN="Y", date=contentsVO.metaAnalyzeDt, type="scraping", reason="Scraping failed"))
            
            # Save to contents_backup collection
            self.save_to_backup_collection(contentsVO)
            
            return True
            
        except Exception as e:
            self.docker_scraping_logger.error(f"Error processing article: {e}")
            traceback.print_exc()
            return False

    def save_to_backup_collection(self, contentsVO: ContentsVO):
        """
        Save ContentsVO to contents_backup collection
        """
        try:
            # Convert ContentsVO to dictionary
            contents_dict = contentsVO.to_mongo()
            
            # Add backup metadata
            contents_dict['backup_created_at'] = datetime.utcnow()
            contents_dict['backup_source'] = 'today_json_processing'
            
            # Insert into backup collection
            result = self.contents_backup_collection.insert_one(contents_dict)
            
            self.docker_scraping_logger.info(f"Saved to contents_backup collection with ID: {result.inserted_id}")
            
        except Exception as e:
            self.docker_scraping_logger.error(f"Error saving to backup collection: {e}")
            raise
        
    def export_content_to_json(self, contentsVO: ContentsVO):
        """
        Export a single processed content to JSON file with pretty formatting
        """
        def serialize_for_json(obj):
            """재귀적으로 datetime과 ObjectId를 JSON 직렬화 가능한 형태로 변환"""
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, ObjectId):
                return str(obj)
            elif isinstance(obj, dict):
                return {k: serialize_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [serialize_for_json(item) for item in obj]
            else:
                return obj
        
        try:
            if not self.export_to_json:
                return
                
            # Convert ContentsVO to dictionary
            content_dict = contentsVO.to_mongo()
            
            # 재귀적으로 모든 datetime과 ObjectId 변환
            content_dict = serialize_for_json(content_dict)
            
            # Create filename with timestamp and URL hash
            url_hash = str(hash(contentsVO.url))[-8:]  # Last 8 chars of hash
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            # 모델 이름을 파일명에 추가
            model_name = CONF.OLLAMA_MODEL.replace(':', '-').replace('/', '-')  # 특수문자 치환
            filename = f"{model_name}_content_{timestamp}_{url_hash}.json"
            filepath = os.path.join(self.json_export_dir, filename)
            
            # Write to JSON file with pretty formatting
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(content_dict, f, ensure_ascii=False, indent=2)
            
            self.docker_scraping_logger.info(f"Exported content to JSON: {filepath}")
            
        except Exception as e:
            self.docker_scraping_logger.error(f"Failed to export content to JSON: {e}")
        
if __name__ == "__main__":
    
    
    contentsScrapingOllamaTrafilaura = ContentsScrapingOllamaTrafilaura()
    
    # Regular scraping from contents_queue
    # contentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama()
    
    # Process URLs from today.json and save to contents_backup collection
    # contentsScrapingOllamaTrafilaura.process_articles_from_today_json()
    
    # Other methods
    #contentsScrapingOllamaTrafilaura.scrapping_for_exist_contents()
    # contentsScrapingOllamaTrafilaura.analysis_for_exist_contents()
    contentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama()

    