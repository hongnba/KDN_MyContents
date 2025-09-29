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

class DockerCollectMain:
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
        
    def distribute(self):
        self.docker_collect_logger.info("--------------Docker_Collect 시작--------------")

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
            # if contentsOrg.orgId != "A0030":
            #     continue       
            for category in contentsOrg.categoryList:    
                result = None
                test_cnt+=1
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
                        result = get_kps_news(driver, contentsOrg, category)  
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
                    try:
                        self.contentCollectErrorService.insert_error(
                            collect_dt =collect_datetime, 
                            org_id =contentsOrg.orgId, 
                            reg_dt =regDt,
                            reg_id ="admin",
                            edit_dt =contentsOrg.editDt,
                            edit_id ="admin",   
                            error_info = error_info,          
                            cate_id = category.cateId,      
                        )
                    except Exception as e:
                        self.docker_collect_logger.error(e)


                self.total_cnt += 1      
 
        driver.quit()
        print(test_cnt)        
        self.docker_collect_logger.info("--------------Docker_Collect 종료--------------")


if __name__ == "__main__":
    main = DockerCollectMain()
    main.distribute()
 
