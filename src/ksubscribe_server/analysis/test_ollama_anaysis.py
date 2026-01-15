


#from langchain_community.chat_models import ChatOllama
import requests
from openai import OpenAI
import traceback
import pandas as pd 
from datetime import datetime, timezone
import logging 
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama.chat_models import ChatOllama 
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    BaseMessage,
    BaseMessageChunk,
    HumanMessage,
    convert_to_messages,
    message_chunk_to_message,
) 

from urllib.parse import urlparse
import json
from typing import Tuple, Dict,List

from ksubscribe_share.logger import Logger
from ksubscribe_server.models.contentsMetaResult import ContentsMetaResult, ContentsMeta
from ksubscribe_server.analysis.analysis_ollama_generate import AnalysisOllamaGenerateCall
from docker_collect.driver_utils import get_driver
from docker_scraping.web_loader import WebLoaderV3


from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsMeta, SentimentInfo
from ksubscribe_share.db.dbmodelV2.llmAnalysisMeta import LLMAnalysisMeta
from ksubscribe_share.db.dbmodelV2.naverScrappingInfoVO import NaverScrappingInfoVO
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService 
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.predefineKeywordService import PredefineKeywordService
from ksubscribe_share.db.service.contentsService import ContentsService 
from ksubscribe_share.db.service.naverScrappingService import NaverScrappingService 
from ksubscribe_share.db.service.baseQueryService import BaseQueryService
from ksubscribe_share.db.service.contentsCollectDailyHistoryService import ContentsCollectDailyHistoryService
import ksubscribe_share.config as CONF
from dataclasses import dataclass
from datetime import time

@dataclass
class OllamaTest:
    url : str = None
    metaData:ContentsMeta = None
    result : str = None
    duration : str = None

class OllamaTester:
    def __init__(self):
        self.analysis = AnalysisOllamaGenerateCall()
        self.ollama_test_logger = Logger().setup_logger("ollama_tester_logger")

    def test_case_1(self):
        """
        설명 넣을 것 
        Args:
            OOO : 설명 
        Returns:
            result_list([]): 설명 
        """        
        ollama_test_logger = Logger().setup_logger("Ollama Test Logger").setLevel(logging.INFO)
        result_list = []
        sentiments_result = []
        summary_result = []
        
        cnt = 0
        # 1. test data read ( index 0~ 9까지 )
        test_data = self.read_test_data()
        start_index = 0
        end_index = 10
        contents_list = test_data['contents'][start_index:end_index]
        url_list = test_data['url'][start_index:end_index]
        
        # 2. 기관 리스트, 키워드 리스트         
        org_list = CommCodeService().get_org_name_list()
        keywords = PredefineKeywordService().getKeywordList()
        org_name_list = []
        keyword_name_list = []    
        for org in org_list: 
            org_name_list.append(org["codeName"])
        for keyword in keywords:
            keyword_name_list.append(keyword)
        separator = ", "  # 구분자 정의
        org_name_list = separator.join(org_name_list)    
        keyword_name_list = separator.join(keyword_name_list)  
        # 3. ContentsQueue의 데이터 하나씩 분석 시작
        model = AnalysisOllamaGenerateCall()     
        for index, content in enumerate(contents_list):
            cnt+=1
            url = url_list[index]
            # 3-1. contents.metadata.sentitments 분석 
            new_question = model.question_sentiment.replace("pred_keywords_from_db", keyword_name_list).replace("org_name_list_from_db", org_name_list)
            new_question = new_question.replace("[contents]",content)
            result_analysis_sentiment = model.chat_ollama._client.generate(
                model ="hf.co/MLP-KTLim/llama-3-Korean-Bllossom-8B-gguf-Q4_K_M:latest",#hf.co/MLP-KTLim/llama-3-Korean-Bllossom-8B-gguf-Q4_K_M:latest "llama-3-Korean-Bllossom-8B-Q4_K_M"
                prompt=new_question ,
                format="json")
            if result_analysis_sentiment.total_duration:
                print(f"sentiments 소요시간 : {result_analysis_sentiment.total_duration/1000000000} 초 소요") 
            # 3-1. contents.metadata.summary 분석
            new_question = model.question_summary.replace("pred_keywords_from_db", keyword_name_list).replace("org_name_list_from_db", org_name_list)
            new_question = new_question.replace("[contents]",content)
            result_analysis_summary = model.chat_ollama._client.generate(
                model ="lama-3-Korean-Bllossom-8B-Q4_K_M",
                prompt=new_question ,
                format="json")
            if result_analysis_summary.total_duration:
                print(f"summary 소요시간 : {result_analysis_summary.total_duration/1000000000} 초 소요") 
            # 4. 결과 출력 
            #result = AnalysisOllamaGenerateCall().to_ollamaModel_V3(sentiments_result= result_analysis_sentiment,summary_result= result_analysis_summary)
            #result_list.append(result) 
            sentiments_result.append(result_analysis_sentiment)
            summary_result.append(result_analysis_summary)
            pass 
        #result_list
        #print(f"컨텐츠 분석 종료. try : {cnt} ,결과 {len(result_list)}개")

    # 본문만<->전체 body 
    def test_case_2(self):
        """
        설명 넣을 것 
        Args:
            OOO : 설명 
        Returns:
            OOO: 설명 
        """             
        test_contents = None       
           
        # 1. contents (url은 body tag인 데이터) 
        #test_org_id, test_cate_id = "A0015","B0010"
        test_url = 'https://www.cstimes.com/news/articleView.html?idxno=630782'
        test_contents = ContentsService().findByURL(test_url)
     
        # 2. scrapping 실행
        driver = get_driver()
        driver.set_page_load_timeout(60)
        driver.get(test_url)
        webloader = WebLoaderV3()
        input_text_body = webloader.find_text_in_html(driver)

        # 3. tag 변경해서 scrapping        
        tag,tag_value,element = "id","article-view-content-div","div"
        input_text_tag = webloader.find_text_in_tag(tag,tag_value,element,driver)

        if not (input_text_tag and input_text_body):
            print("scrapping 실패")
            return 
        
        # 4. analysis 비교 
        org_list = CommCodeService().get_org_name_list()
        keywords = PredefineKeywordService().getKeywordList()
        org_name_list = []
        keyword_name_list = []    
        for org in org_list:
            org_name_list.append(org["codeName"])
        for keyword in keywords:
            keyword_name_list.append(keyword)
        separator = ", "  # 구분자 정의
        pred_keyword_list = separator.join(org_name_list)    
        org_name_list = separator.join(keyword_name_list)  

        content = input_text_body
        result_body = self.analysis_demo(content=content,pred_keyword_list=pred_keyword_list,org_name_list=org_name_list,mycontents_logger=self.ollama_test_logger)
        content = input_text_tag
        result_tag = self.analysis_demo(content=content,pred_keyword_list=pred_keyword_list,org_name_list=org_name_list,mycontents_logger=self.ollama_test_logger)
        
        
        print("*"*60)
        print(result_body.contentsMeta)
        print("*"*60)
        print(result_tag.contentsMeta)

        pass 
    
    
    
    def analysis_demo(self, content, pred_keyword_list, org_name_list, mycontents_logger:logging.Logger): 
        """
        설명 넣을 것 
        Args:
            OOO : 설명 
        Returns:
            OOO: 설명 
        """             

        # 3. ContentsQueue의 데이터 하나씩 분석 시작
        model = AnalysisOllamaGenerateCall()      
        new_question = model.question_sentiment.replace("pred_keywords_from_db", pred_keyword_list).replace("org_name_list_from_db", org_name_list)
        new_question = new_question.replace("[contents]",content)
        
        
        result_analysis_sentiment = model.chat_ollama._client.generate(
            model ="hf.co/MLP-KTLim/llama-3-Korean-Bllossom-8B-gguf-Q4_K_M:latest",
            prompt=new_question ,
            format="json")
        if result_analysis_sentiment.total_duration:
            print(f"sentiments 소요시간 : {result_analysis_sentiment.total_duration/1000000000} 초 소요") 
            
        # 3-1. contents.metadata.summary 분석
        new_question = model.question_summary.replace("pred_keywords_from_db", pred_keyword_list).replace("org_name_list_from_db", org_name_list)
        new_question = new_question.replace("[contents]",content)
        
        result_analysis_summary = model.chat_ollama._client.generate(
            model ="hf.co/MLP-KTLim/llama-3-Korean-Bllossom-8B-gguf-Q4_K_M:latest",
            prompt=new_question ,
            format="json")
        model.chat_ollama.invoke() # -> post ~~~/api/invoke
        model.chat_ollama._client.generate()# post ~~~/api/generate
        if result_analysis_summary.total_duration:
            print(f"summary 소요시간 : {result_analysis_summary.total_duration/1000000000} 초 소요") 
            
        # 4. 결과 출력 
        result = AnalysisOllamaGenerateCall().to_ollamaModel(sentiments_result= result_analysis_sentiment,summary_result= result_analysis_summary)
        return result
    

    def analysis_demo_main_V2():
        pass 
     

    def analysis_demo_v2(self, content, pred_keyword_list, org_name_list, mycontents_logger:logging.Logger):
        try: 
            contentsMetaResult = ContentsMetaResult()
            contentsMetaResult.contentsMeta.method = "ollama"
            summary_start = time.time()
            new_question_summary = self.question_summary.replace("pred_keywords_from_db", pred_keyword_list).replace("[contents]",content)
            result_summary = self.chat_ollama._client.generate(
                                    model=CONF.OLLAMA_MODEL,
                                    prompt=new_question_summary,
                                    format="json")
            summary_end = time.time()
            is_success, result_summary_json = self.json_load(result_summary, mycontents_logger) 
            summary_success = self.summary_to_ollamaModel(result_summary, result_summary_json, contentsMetaResult,  mycontents_logger) 
            contentsMetaResult.summarySucYN = "Y" if summary_success else "N"
            mycontents_logger.info(f"요약분석 소요시간 : {summary_end-summary_start} 초 소요")

            new_question_sentiment = self.question_sentiment.replace("org_name_list_from_db", org_name_list).replace("[contents]",content)
            sentiment_start = time.time()
            result_sentiment = self.chat_ollama._client.generate(
                                    model=CONF.OLLAMA_MODEL,
                                    prompt=new_question_sentiment,
                                    format="json")
            sentiment_end = time.time()
            is_success, result_sentiment_json = self.json_load(result_sentiment,mycontents_logger)
            #prompt_tokens = count_tokens(new_question_sentiment)
            #response_tokens = count_tokens(result_sentiment["response"])
            sentiment_success = self.sentiment_to_ollamaModel(result_sentiment, result_sentiment_json, contentsMetaResult,  mycontents_logger) 
            contentsMetaResult.sentimentSucYN = "Y" if sentiment_success else "N"
            mycontents_logger.info(f"평판분석 소요시간 : {sentiment_end-sentiment_start} 초 소요")
            
            #요약만 성공해도 성공으로 처리                        
            contentsMetaResult.metaSucYN = "Y" if summary_success else "N"
            contentsMetaResult.metaAnalyzeDt = datetime.now(timezone.utc)  
            
            return True, contentsMetaResult

        except Exception as e: 
            #trackback logging
            tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            mycontents_logger.error(f"Exception occurred: {e}, Args: {e.args}, Traceback: {tb_str}")

            error_ollamaModel :ContentsMetaResult = self.to_error_ollamaModel() 
            return False, error_ollamaModel


    # 현재 contents에 수집된 기사 사이트 도메인(text in body인 곳만)
    # 추가 : 현재 800개 이상 발견되었습니다.(20250206 기준)
    def search_naver_newsdomain(self):
        """
        네이버 뉴스 도메일 읽어서, DB에 넣기 
        Args:
            OOO : 설명 
        Returns:
            OOO: 설명 
        """             
        domain_list = ContentsService().find_naver_newdomain() 
        print("\n".join(domain_list))
        print(len(domain_list))
        
        NaverScrappingService().upsert_naver_newsdomain(domain_list)
    
    def search_naver_newsdomain_exampleUrl(self):
        """
        네이버 뉴스 도메인 하나당 하나의 예제 url 출력 
        Args:
        Returns:
            List[NaverScrappingInfoVO]: 도메인 정보 전체 반환  
        """             
        domain_list:List[NaverScrappingInfoVO] = NaverScrappingService().find_all_naver_newsdomain()
        
        for domain in domain_list:
            print(domain.domain)
            #url = ContentsService().find_first_url_by_domain(domain.domain)
            #print(url)
        

    def generate_test_data():
        contents = ContentsService().find_sorted_contents(limit_cnt=10)
        #contents_raws = [content["contentsRaw"]['contents'] for content in contents]
        data_dict = {"url": [],
                    "contents" : []}
        
        for content in contents:
            data_dict["url"].append(content['url'])
            data_dict["contents"].append(content['contentsRaw']['contents'])
            
        with open("test_data_for_ollama.json", "w",encoding="utf-8") as json_file:
            json.dump(data_dict, json_file, ensure_ascii=False,indent =4)    
        print("generate test data done...")
    
    def read_test_data(self):
        with open("test_data_for_ollama.json", "r",encoding="utf-8") as json_file:
            data = json.load(json_file) 
        return data 



def dict2pd(data_dict):
#
# data  =   { 
#               "column_1" : "data_1"
#               "column_2" : "data_2"
#           }
#  ---------------------
# |     |column_1|column_2|
# |     | data_1 | data_2 |
# |     |        |
# |     |        |

    pass 

def main():
    OllamaTester().test_case_1()

    pass 
if __name__ == "__main__":
    main()
    #OllamaTester().search_naver_newsdomain_exampleUrl()
    pass 