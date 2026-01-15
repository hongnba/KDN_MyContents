# -*- coding: utf-8 -*-
############################################################################
# KDN crawl.py 를 mongodb 버전으로 변환한 것 
############################################################################

import os
import sys  

from ksubscribe_share.logger import Logger
import json
from typing import Dict, List
import ssl
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd
import pymongo
from sqlalchemy import create_engine
import urllib.request
import re
#from sklearn.feature_extraction.text import TfidfVectorizer
from dateutil.parser import parse
import warnings
import pickle

from datetime import date, datetime, timedelta
from docker_collect.driver_utils import get_driver
from docker_collect.error_handler import ErrorHandler,OpenAPIErrorHandler,SeleniumErrorHandler
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO, ContentsOrgCategory
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.service.contentsCollectHistoryService import ContentsCollectHistoryService
from ksubscribe_share.db.service.contentsCollectErrorService import ContentsCollectErrorService
from ksubscribe_share.db.service.contentsCollectDailyHistoryService import ContentsCollectDailyHistoryService
from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService
from docker_collect.rss_collector import get_contents_by_rss
from docker_collect.openapi_collector import get_g2b_nara, get_naver_news
from docker_collect.selenium_collector import get_contents_by_selenium_main, get_kepco_news, get_koen_news, get_kps_news
import pytz
warnings.filterwarnings("ignore")
ssl._create_default_https_context=ssl._create_unverified_context
today = date.today().strftime("%Y%m%d")

class DockerCollectTesterMain:
    contentCollectErrorService = ContentsCollectErrorService()
    contentsOrgService = ContentsOrgService()
    dailyHistoryService = ContentsCollectDailyHistoryService()
    success_cnt = 0 
    fail_cnt = 0 
    total_cnt = 0 
    

    def __init__(self):
        self.collect_dt =  datetime.utcnow().replace(tzinfo=pytz.utc)
        logger = Logger()
        self.docker_collect_logger = logger.setup_logger(logger.docker_collect_logger_name)
    
        pass

    def distribute_A0030_test(self):

        # dailycollecthistory가 없으면 생성
        self.dailyHistoryService.isExist()
        #[개발해야함]사용자가 가입한 나라장터 카테고리 키워드를 검색해서 g2b_keywords에 넣음. ==> 나라장터만 특별히 쿼리하고 있음. 
        g2b_keywords = self.contentsOrgService.findOrgKeywords("A0004") 
        #[개발해야함]기관 카테고리 정보를 가져옴  
        contentsOrgList = ContentsOrgService().find_all(); 
        # # test
        # for contentsOrg in contentsOrgList :
        #     for cate in contentsOrg.categoryList:
        #         cate.lastSucYMD = cate.lastSucYMD - timedelta(days=1)
        driver = get_driver()
        test_cnt = 0
        for contentsOrg in contentsOrgList:            
            if contentsOrg.orgId != "A0030":
                continue
            for category in contentsOrg.categoryList:    
                result = None

                collect_datetime = datetime.utcnow().replace(tzinfo=pytz.utc)
                err_handler = ErrorHandler() 
                
                # SELENIUM 
                if category.COL_METHOD == "C0003":  
                    #한국전력공사(주) and 보도자료
                    if contentsOrg.orgId == "A0010" and category.cateId == "B0001" : 
                        result = get_kepco_news(driver, contentsOrg, category) 
                    #한국남동발전(주) and 보도자료
                    elif contentsOrg.orgId == "A0014" and category.cateId == "B0001" : 
                        result = get_koen_news(driver, contentsOrg, category)                      
                    #한전KPS(주) and 보도자료
                    elif contentsOrg.orgId == "A0020" and category.cateId == "B0001" : 
                        result = get_koen_news(driver, contentsOrg, category)  
                    #그외 
                    else: 
                        result = get_contents_by_selenium_main(driver, contentsOrg, category)
                    
                    err_handler.set_processor(SeleniumErrorHandler())   

                # RSS
                elif category.COL_METHOD == "C0001": 
                    reulst = get_contents_by_rss(contentsOrg, category)
                    
                # OPEN API
                else: 
                    #나라장터 and 입찰정보 
                    if contentsOrg.orgId == "A0004" and category.cateId == "B0005" : 
                        result =get_g2b_nara(contentsOrg, category, g2b_keywords) 
                        err_handler.set_processor(OpenAPIErrorHandler())   
                    #그외 
                    else: 
                        result = get_naver_news("A0026", contentsOrg, category)
                        err_handler.set_processor(OpenAPIErrorHandler())                       
                if not result:
                    continue    
                      
                if result["success"]:
                    self.success_cnt +=1  
                else :
                    # result["error"] = fail_helper(result["success"])
                    error_info = err_handler.handle(result["error"])
                    regDt = datetime.utcnow().replace(tzinfo=pytz.utc)
                    self.fail_cnt += 1
                    self.contentCollectErrorService.insert_error(
                        collect_dt =collect_datetime, 
                        org_id =contentsOrg.orgId, 
                        reg_dt =regDt,
                        reg_id =contentsOrg.regId,
                        edit_dt =contentsOrg.editDt,
                        edit_id =contentsOrg.editId,   
                        error_info = error_info,          
                        cate_id = category.cateId,      
                    )  
                self.total_cnt += 1      
 
        driver.quit()

    def distribute_A0004_B0005_test(self):

        #[개발해야함]사용자가 가입한 나라장터 카테고리 키워드를 검색해서 g2b_keywords에 넣음. ==> 나라장터만 특별히 쿼리하고 있음. 
        g2b_keywords = self.contentsOrgService.findOrgKeywords("A0004")
        g2b_keywords = [keyword for keyword in g2b_keywords if keyword not in (None, "")]

        #[개발해야함]기관 카테고리 정보를 가져옴  
        contentsOrg = self.contentsOrgService.findNaraOrg()

        for category in contentsOrg.categoryList:                 
            if contentsOrg.orgId == "A0004" and category.cateId == "B0005" : 
                get_g2b_nara(contentsOrg, category, g2b_keywords)                     

    def distribute_A0016_B0001_test(self):

        driver = get_driver()
        contentsOrgVO, category = self.contentsOrgService.findOrgAndCategory("A0016", "B0001")
        result = get_contents_by_selenium_main(driver, contentsOrgVO, category)
        driver.quit()
    
    def distribute_A0026_B0010_test(self):
        driver = get_driver()
        contentsOrgVO, category = self.contentsOrgService.findOrgAndCategory("A0026", "B0010")
        result = get_naver_news(driver,contentsOrgVO,category)
        driver.quit()
        pass 

    def load_test_answer(self): 
        # 저장된 JSON 파일 경로
        file_path = "docker_collect/test/test_input.json"

        # JSON 파일 읽기
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data
        
    def list_to_dict(self,test_data):
        result_dict = {}
        for data in test_data:
            result_dict[(data["orgId"],data["cateId"])] = data
        return result_dict
        
    def distribute_test(self):
        test_data = self.load_test_answer()
        g2b_keywords = self.contentsOrgService.findOrgKeywords("A0004") 
        contents_org_list = ContentsOrgService().find_all()
        test_data = self.list_to_dict(test_data)
        err_handler = ErrorHandler()
        for contentsOrg in contents_org_list:
            for category in contentsOrg.categoryList:
                
                url = category.collectUrlInfo
                # last_suc 다음 날짜부터 오늘까지의 날짜 리스트 생성
                key = (contentsOrg.orgId,category.cateId)
                if not test_data in key:
                    test_sucYMD = datetime.strptime("20250119","%Y%m%d")
                    category.lastSucYMD = (test_sucYMD - timedelta(days=1)).strftime("%Y%m%d")
                else:
                    test_sucYMD =datetime.strptime(test_data[key]["testDt"],"%Y%m%d")
                    category.lastSucYMD = (test_sucYMD - timedelta(days=1)).strftime("%Y%m%d")
                #category.lastSucYMD = test_data[key]["testDt"]
                if isinstance(category.lastSucYMD,str):
                    category.lastSucYMD = datetime(category.lastSucYMD)
                driver = get_driver()
                if category.COL_METHOD == "C0003":  
                    #한국전력공사(주) and 보도자료
                    if contentsOrg.orgId == "A0010" and category.cateId == "B0001" : 
                        result = get_kepco_news(driver, contentsOrg, category) 
                    #한국남동발전(주) and 보도자료
                    elif contentsOrg.orgId == "A0014" and category.cateId == "B0001" : 
                        result = get_koen_news(driver, contentsOrg, category)                      
                    #한전KPS(주) and 보도자료
                    elif contentsOrg.orgId == "A0020" and category.cateId == "B0001" : 
                        result = get_koen_news(driver, contentsOrg, category)  
                    #그외 
                    else: 
                        result = get_contents_by_selenium_main(driver, contentsOrg, category)
                    
                    err_handler.set_processor(SeleniumErrorHandler())   

                # RSS
                elif category.COL_METHOD == "C0001": 
                    reulst = get_contents_by_rss(contentsOrg, category)
                    
                # OPEN API
                else: 
                    #나라장터 and 입찰정보 
                    if contentsOrg.orgId == "A0004" and category.cateId == "B0005" : 
                        result =get_g2b_nara(contentsOrg, category, g2b_keywords) 
                        err_handler.set_processor(OpenAPIErrorHandler())   
                    #그외 
                    else: 
                        result = get_naver_news("A0026", contentsOrg, category)
                        err_handler.set_processor(OpenAPIErrorHandler())
    
    def check_result(self):
        
        test_data = self.load_test_answer()
        test_data = self.list_to_dict(test_data)
        contentsQueue = ContentsQueueService().find_all()
        result_dict = {}
        # 1. 결과 카운팅
        for queueContent in contentsQueue:
            key = (queueContent.contentOrgId,queueContent.cateId)
            if key in result_dict:
                result_dict[key] +=1
            else : 
                result_dict[key] = 1
        # 2. 정답확인
        for key,result in result_dict.items():
            print(key)
            if test_data[key]["articleCount"] == result:
                continue 
            print("not matching result cnt")
            pass 
    def check_collect_history(self):
        ContentsCollectHistoryService()
        pass 

if __name__ == "__main__":
    #Logger("--------------Docker_Collect 시작--------------")
    main = DockerCollectTesterMain()
    main.distribute_test()
    #Logger("--------------Docker_Collect 종료--------------")
 
