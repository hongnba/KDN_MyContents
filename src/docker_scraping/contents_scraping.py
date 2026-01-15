import sys
import traceback
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from bson import ObjectId
import json
from typing import List
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
from ksubscribe_server.analysis.analysis_ollama import AnalysisOllama


from ksubscribe_share.logger import Logger
from typing import Dict
from ksubscribe_server.models.ollamaModel import OllamaModel
from docker_scraping.web_loader import WebLoaderV3
class CustomScrapException(Exception):
    def __init__(self, message):
        super().__init__(message)

def time_now():
    return datetime.now(timezone(timedelta(hours=9)))

class ContentsScraping:

    '''
        Trafilaura을 사용하여 스크래핑하기 전에 구현한 코드, 현재 사용하지 않음. 
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
    
    def crawl_without_analyze(self):
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
            self.crawl_without_analyze_one(contentsQueueVO, webLoader, driver, summaryAnalysis)      
        driver.quit()


        pass 

    def crawl_without_analyze_one(self, queueContent:ContentsQueueVO, webLoader:WebLoaderV3, driver, summaryAnalysis):
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
            contentsVO.rawCollectDt = datetime.utcnow() #
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
            contentsVO.metaAnalyzeDt = datetime.utcnow() 
            #isSuccess, result_analysis = summaryAnalysis.analysis(content=raw_data, pred_keyword_list=self.keyword_name_list, org_name_list=self.org_name_list, mycontents_logger=self.docker_scraping_logger)
            isSuccess = False
            result_analysis  = {"error_data": "Ollama Disconnect"} 
            contentsVO = self.generateContentsMeta_version2(isSuccess, contentsVO, result_analysis) 
            self.docker_scraping_logger.info(f"Contents 요약 실패({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}")
   
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
    
    
        pass 

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
    def crawl_and_analyze_ollama(self):
        self.docker_scraping_logger.info("--------------Docker_Scraping 시작--------------")

        webLoader = WebLoaderV3()
        driver = get_driver()
        
        summaryAnalysis = AnalysisOllama()
        # 수집한 콘텐츠 가져오기
        queueContents: List[ContentsQueueVO] = self.contentsQueueService.find_all()
 
        if(len(queueContents) <= 0): 
            return  
        self.docker_scraping_logger.info(f"Queue range : {len(queueContents)}")
        for index, contentsQueueVO in enumerate(queueContents):  
            self.crawl_and_analyze_one_ollama(contentsQueueVO, webLoader, driver, summaryAnalysis)      
        driver.quit()
            
        self.docker_scraping_logger.info("--------------Docker_Scraping 완료 --------------")
        pass 
    def crawl_and_analyze_one_ollama(self, queueContent:ContentsQueueVO, webLoader:WebLoaderV3, driver, summaryAnalysis:AnalysisOllama):
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
            contentsVO.rawCollectDt = datetime.utcnow()
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
            contentsVO.metaAnalyzeDt = datetime.utcnow() 
            isSuccess, result_analysis = summaryAnalysis.analysis(content=raw_data, pred_keyword_list=self.keyword_name_list, org_name_list=self.org_name_list, mycontents_logger=self.docker_scraping_logger)

            contentsVO = self.generateContentsMeta_ollama( contentsVO, result_analysis)
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
            contentsVO.rawCollectDt = datetime.utcnow()
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
            contentsVO.metaAnalyzeDt = datetime.utcnow() 
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
    
    
    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    def scrapping_only_for_olddata(self): 
         
        self.docker_scraping_logger.info("--------------Docker_Scraping(ollama 사용, 기구축 contents) 시작--------------")
         
        webLoader = WebLoaderV3()
        driver = get_driver()
        analysisOllama = AnalysisOllama()
       
        #요약, 사전정의 키워드, 평판등을 ollama를 이용하여 할당한다. 
        contentsVOList:List[ContentsVO] = self.contentsService.findContents_olddata(10) 
        if(len(contentsVOList) <= 0): 
            return  
                
        self.docker_scraping_logger.info(f"Queue range : {len(contentsVOList)}")
        
        for index, contentsVO in enumerate(contentsVOList): 
            self.scrapping_one_for_olddata(contentsVO, webLoader, driver, analysisOllama)        
        
        driver.quit()
        
        self.docker_scraping_logger.info("--------------Docker_Scraping(ollama 사용, 기구축 contents) 완료--------------")
        
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
    

    def scrapping_one_for_olddata(self, contentsVO:ContentsVO, webLoader:WebLoaderV3, driver, analysisOllama:AnalysisOllama):
        
        if contentsVO is None:
            return  
        
        contentsOrgVO, contentsOrgCategory = self.contentsOrgService.findOrgAndCategory(contentsVO.contentsOrgId, contentsVO.categoryId)       
               
        try:
            
            #Web 컨텐츠 수집 ##########################################################             
            contentsVO.rawCollectDt = datetime.now()
            self.docker_scraping_logger.info(f"Web 컨텐츠 수집 시작({contentsVO.contentsOrgId},{contentsVO.categoryId}) : {contentsVO.url}-----------------")
            isSuccess, raw_data = webLoader.loadContents(contentsVO, contentsOrgVO, contentsOrgCategory,driver) 
            #isSuccess, raw_data = self.test_raw()

            # Raw 데이터 수집 실패 시 
            if isSuccess == False or raw_data == "" or raw_data == None :
                self.docker_scraping_logger.info(f"Web 컨텐츠 수집 실패({contentsVO.contentsOrgId},{contentsVO.categoryId}) : {contentsVO.url}")
                return
            
            # Raw 데이터 수집 성공 시 
            contentsVO.rawCollectSucYN = 'Y'
            contentsVO.contentsRaw = self.generateContentsRaw(contentsVO.title, contents=raw_data, errorInfo=None)
            self.contentsService.update_rawCollect(contentsVO)
            self.docker_scraping_logger.info(f"Web 컨텐츠 수집 성공({contentsVO.contentsOrgId},{contentsVO.categoryId}) : {contentsVO.url}")
            
            
            #요약, 키워드 추출, 평판분석 ##########################################################            
            contentsVO.metaAnalyzeDt = datetime.now()
            contentsId = str(contentsVO._id)
            isSuccess, ollamaModel = analysisOllama.analysis(raw_data, pred_keyword_list=self.keyword_name_list, org_name_list=self.org_name_list, mycontents_logger=self.docker_scraping_logger, contentsId=contentsId)                        
            ollamaModel.contentsMeta.llmAnalysisVO = ollamaModel.llmAnalysisVO
            
            if ollamaModel.metaSucYN == "Y" and ollamaModel.contentsMeta is not None:
                self.contentsService.update_ollama_metaAnalyze(contentsVO._id, ollamaModel.contentsMeta)
                self.docker_scraping_logger.info(f"ollama 요약 성공({contentsOrgVO.orgId},{contentsOrgCategory.cateId}) : {contentsVO.url}")
            else:
                self.docker_scraping_logger.info(f"ollama 요약 실패({contentsOrgVO.orgId},{contentsOrgCategory.cateId}) : {contentsVO.url}")
                
                
        except Exception as e:   
            tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            self.docker_scraping_logger.error(f'error :  {tb_str}')
        
        
        # #이미지 아이디는 무조건 생성한다.      
        # contentsVO = self.generate_imageId(contentsVO)
        # BaseQueryService.insert_one(contentsVO)
        # ContentsQueueService().deleteQueue(queueContent._id) 
        # self.docker_scraping_logger.info(f"Contents DB 저장({queueContent.contentOrgId},{queueContent.cateId}) : {queueContent.url}")
        
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
    def generateContentsMeta_ollama(self,contentsVO:ContentsVO,ollama_result: OllamaModel):
        if ollama_result.metaSucYN == False:
            contentsVO.metaSucYN = "N"
            contentsVO.contentsMeta = ContentsMeta(
                errorInfo =  self.generateErrorInfo(errorYN="Y",date=contentsVO.metaAnalyzeDt ,reason=ollama_result["error_data"]) 
            )   
            return contentsVO
        pass 
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
            for key,value in contentsVO.contentsMeta.predKeywords.items():    
                contentsVO.imageId = ContentsImageService().recommendKeywordImage(key)
                if contentsVO.imageId is not None:
                    break     

            #타이틀과 유사도측정하여 이미지 할당 
            if contentsVO.imageId is None:
                title = contentsVO.title
                predefineKeyword = PredefineKeywordService().getKeywordList()
                bestKeywordList= SimularityChecker().best_keyword_of_title(title, predefineKeyword)
                if bestKeywordList is not None or len(bestKeywordList) > 0:
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
            sentimentInfo.positveRatio = data.get('positiveRatio', None)
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




if __name__ == "__main__":
    
    ollamaModel = OllamaModel()
    dontentsScraping = ContentsScraping()  
    dontentsScraping.crawl_without_analyze() 

    