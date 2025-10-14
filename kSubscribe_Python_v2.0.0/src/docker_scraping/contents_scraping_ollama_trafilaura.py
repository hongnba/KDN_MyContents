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
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO, ContentsOrgCategory
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.dbmodel.news import News
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
from ksubscribe_share.db.dbmodelV2.predefineKeywordVO import PredefineKeywordVO
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.service.predefineKeywordService import PredefineKeywordService
from ksubscribe_share.db.service.statsService import StatsService
from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService
from ksubscribe_share.db.service.baseQueryService import BaseQueryService
from ksubscribe_share.db.service.contentsImageService import ContentsImageService
from ksubscribe_share.db.data_migration.data_validator import data_validator
from docker_scraping.web_loader import WebLoaderV3
from docker_scraping.contents_scraping_base import ContentsScrapingBase, CustomScrapException, time_now
from docker_scraping.ai_scraping.trafilaura import TrafilauraScraper
from ksubscribe_share.db.service.originalContentsService import OriginalContentsService
from ksubscribe_share.db.dbmodelV2.originalContentsVO import OriginalContentsVO

class ContentsScrapingOllamaTrafilaura(ContentsScrapingBase):
    '''        
        현재 사용하는 매우 중요한 코드 
        Trafilaura을 사용하여 스크래핑하는 코드 - 현재 이 클래스를 이용하여 스크래핑하고 있음.
    '''
    commCodeService = CommCodeService()
    contentsOrgService = ContentsOrgService()
    contentsQueueService = ContentsQueueService()    
    contentsService = ContentsService()
    statsService = StatsService()
    originalContentsService = OriginalContentsService()
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
    
    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Contents_queue 데이터에 대한 스크래핑 -> 요약, 키워드 추출, 평판, 
    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    
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
        
        # Calculate statistics for all organizations after processing
        self._calculate_organization_stats()
        
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
                isSuccess, contentsMetaResult,summary,sentiment,error_ollamaMetaResult = ollamaAnalysis.analysis_main(title=queueContent.title,content=text, pred_keyword_list=self.keyword_name_list, org_name_list=self.org_name_list, mycontents_logger=self.docker_scraping_logger)            
                #isSuccess, contentsMetaResult,summary,sentiment,error_ollamaMetaResult = ollamaAnalysis.analysis_main(content=text, pred_keyword_list=self.keyword_name_list, org_name_list=self.org_name_list, mycontents_logger=self.docker_scraping_logger)            
        #         if isSuccess:
        #             contentsVO = self.generateContentsMeta_ollama( contentsVO, contentsMetaResult)
        #         else:
        #             contentsVO = self.generateContentsMeta_ollama( contentsVO, error_ollamaMetaResult)
        #         if contentsVO.metaSucYN == "Y":
        #             ContentsCollectDailyHistoryService().inc_daily_scrapping_cnt()
        #             self.analysis_cnt_for_once += 1
        #             self.docker_scraping_logger.info(f"Contents 요약 및 분석 성공({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}")
        #         else:
        #             self.docker_scraping_logger.info(f"컨텐츠 요약 실패 원문 : sumary : {summary} \n sentiments: {sentiment}")
        #             self.docker_scraping_logger.info(f"Contents 요약 및 분석 실패({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}")
        #         #여기서 ollama 또는 nlp 연결하여 본다. 
                
        except Exception as e:   
            pass 
            #tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            #self.docker_scraping_logger.error(f'error :  {tb_str}')
         
        # #이미지 아이디는 무조건 생성한다.      
        # contentsVO = self.generate_imageId(contentsVO)
        # try:
        #     BaseQueryService.insert_one(contentsVO)
        #     ContentsQueueService().deleteQueue(queueContent._id) 
        #     self.docker_scraping_logger.info(f"Web 컨텐츠 수집/요약 정보 저장({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}")
        # except Exception as e : 
        #     tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
        #     self.docker_scraping_logger.error(f'error :  {tb_str}')
        #     self.docker_scraping_logger.info(f"Web 컨텐츠 수집/요약 정보 저장 실패({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}")
        #     pass 

    
    def crawl_and_analyze_one_ollama(self, queueContent:ContentsQueueVO, webLoader:WebLoaderV3, driver, ollamaAnalysis:AnalysisOllamaGenerateCall):
        """ contents_queue에서 읽은 하나의 url에 대한 스크래핑 및 분석 
        """
        if queueContent is None:
            return  
        if ContentsService().isExistContents(queueContent.url):
            self.docker_scraping_logger and self.docker_scraping_logger.info(f"이미 ContentsDB에 존재하는 contents입니다. {queueContent.url}")
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
            
            #LIZA: add original contents (25.10.02)
            
            logg
        
            originalContentsVO = OriginalContentsVO(
                contentOrgId=queueContent.contentOrgId,
                cateId=queueContent.cateId,
                title=contentsVO.title,
                contents=text,
                url=queueContent.url,
                pubDt=contentsVO.pubDt,
                collectDt=contentsVO.rawCollectDt,
                succeeded=isSuccess
            )
            self.originalContentsService.insertOne(originalContentsVO)
            self.docker_scraping_logger.info(f"Original Contents 저장 완료({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}")
            
            contentsVO.rawCollectSucYN = 'Y'
            contentsVO.contentsRaw = self.generateContentsRaw(contentsVO.title, 
                                                              contents=text, 
                                                              errorInfo=None)
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
                isSuccess, contentsMetaResult,summary,sentiment,error_ollamaMetaResult = ollamaAnalysis.analysis_main(content=text, pred_keyword_list=self.keyword_name_list, org_name_list=self.org_name_list, mycontents_logger=self.docker_scraping_logger, queueContent=queueContent)            
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
            tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            self.docker_scraping_logger.error(f'error :  {tb_str}')
         
        #이미지 아이디는 무조건 생성한다.      
        contentsVO = self.generate_imageId(contentsVO)
        try:
            #2025.03.18 콘텐츠 저장되지 않도록 수정 
            if contentsVO and contentsVO.contentsRaw:
                contentsVO.contentsRaw.contents = ""            
            
            BaseQueryService.insert_one(contentsVO)
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
    
    def _calculate_organization_stats(self):
        """Calculate statistics for all organizations after content processing"""
        try:
            self.docker_scraping_logger.info("Starting statistics calculation for all organizations...")
            
            # Get all organizations
            all_orgs = self.contentsOrgService.find_all()
            
            for org in all_orgs:
                if not org.orgId:
                    continue
                    
                try:
                    self.docker_scraping_logger.info(f"Processing stats for organization: {org.orgName} ({org.orgId})")
                    
                    # Always recalculate daily stats
                    self.docker_scraping_logger.info(f"  - Calculating daily stats for {org.orgName}")
                    self.statsService.count_for_period(org.orgId, 'day')
                    
                    # Check if weekly stats need recalculation
                    existing_weekly = self.statsService.get_for_period(org.orgId, 'week')
                    should_recalculate_weekly = True
                    
                    if existing_weekly and existing_weekly.last_calculate_date:
                        time_since_last_weekly = datetime.utcnow() - existing_weekly.last_calculate_date
                        if time_since_last_weekly < timedelta(days=7):
                            should_recalculate_weekly = False
                            self.docker_scraping_logger.info(f"  - Weekly stats for {org.orgName} are up to date (last calculated: {existing_weekly.last_calculate_date})")
                    
                    if should_recalculate_weekly:
                        self.docker_scraping_logger.info(f"  - Calculating weekly stats for {org.orgName}")
                        self.statsService.count_for_period(org.orgId, 'week')
                    
                    # Check if monthly stats need recalculation
                    existing_monthly = self.statsService.get_for_period(org.orgId, 'month')
                    should_recalculate_monthly = True
                    
                    if existing_monthly and existing_monthly.last_calculate_date:
                        time_since_last_monthly = datetime.utcnow() - existing_monthly.last_calculate_date
                        if time_since_last_monthly < timedelta(days=30):
                            should_recalculate_monthly = False
                            self.docker_scraping_logger.info(f"  - Monthly stats for {org.orgName} are up to date (last calculated: {existing_monthly.last_calculate_date})")
                    
                    if should_recalculate_monthly:
                        self.docker_scraping_logger.info(f"  - Calculating monthly stats for {org.orgName}")
                        self.statsService.count_for_period(org.orgId, 'month')
                        
                except Exception as e:
                    self.docker_scraping_logger.error(f"Error calculating stats for organization {org.orgName} ({org.orgId}): {e}")
                    continue
            
            self.docker_scraping_logger.info("Statistics calculation completed for all organizations.")
            
        except Exception as e:
            self.docker_scraping_logger.error(f"Error in statistics calculation process: {e}")
        
        
if __name__ == "__main__":
    
    
    contentsScrapingOllamaTrafilaura = ContentsScrapingOllamaTrafilaura()
    #contentsScrapingOllamaTrafilaura.scrapping_for_exist_contents()
    # contentsScrapingOllamaTrafilaura.analysis_for_exist_contents()
    contentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama()

    