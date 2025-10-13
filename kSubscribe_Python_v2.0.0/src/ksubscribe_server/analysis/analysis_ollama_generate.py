#from langchain_community.chat_models import ChatOllama
import requests
from openai import OpenAI
import traceback
import pandas as pd 
from datetime import datetime, timezone
import logging 
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
#from langchain_ollama.chat_models import ChatOllama 
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    BaseMessage,
    BaseMessageChunk,
    HumanMessage,
    convert_to_messages,
    message_chunk_to_message,
) 
import json
from typing import Tuple, Dict,List
from ollama import GenerateResponse
import time
import re
import tiktoken 

from ksubscribe_share.logger import Logger
from ksubscribe_server.models.contentsMetaResult import ContentsMetaResult
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsMeta, SentimentInfo
from ksubscribe_share.db.dbmodelV2.llmAnalysisMeta import LLMAnalysisMeta
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsMeta
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService
from ksubscribe_share.db.service.articleKeywordsService import ArticleKeywordsService
from ksubscribe_share.db.mariadb_model.articleKeywordsVO import ArticleKeywordsVO

from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.predefineKeywordService import PredefineKeywordService
from ksubscribe_share.db.service.contentsService import ContentsService
from ksubscribe_server.similarity.simularity_check import SimularityChecker
from ksubscribe_server.analysis.analysis_ollama_base import AnalysisOllamaBase
import ksubscribe_share.config as CONF
from pydantic import BaseModel, PrivateAttr, model_validator
def count_tokens(text: str, model: str = "llama3"):
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))
 
class AnalysisOllamaGenerateCall(AnalysisOllamaBase):

    def __init__(self):
        self.chat_ollama =  ChatOllama(model = CONF.OLLAMA_MODEL,
                                       base_url= CONF.OLLAMA_URL, 
                                       format="json") 
        #self.chat_ollama._client = PrivateAttr(default=None)  # type: ignore
        
        self.keywords = PredefineKeywordService().getKeywordList()
        # 202504101 임형준 : ollama client timeout 조건 추가
        self.chat_ollama.client_kwargs["timeout"] = 20
        self.chat_ollama._set_clients()
        self.contentsQueueService = ContentsQueueService()
        
    #25.03.13 당문간 _test함수 유지     
    def analysis_main_test(self, title,content, pred_keyword_list, org_name_list, mycontents_logger:logging.Logger): #-> tuple[bool, ContentsMetaResult]:
        """Ollama 연계하여 분석 ( 요약분석, 평판분석 )
        """        
        try: 
            contentsMetaResult = ContentsMetaResult()
            contentsMetaResult.contentsMeta.method = "ollama"
            summary_start = time.time()
            
            #pred_keyword_list = [item + " 기술"  for item in pred_keyword_list]
            
            new_question_summary = self.question_summary.replace("pred_keywords_from_db", pred_keyword_list).replace("[contents]",content)
            result_summary = self.chat_ollama._client.generate(
                                    model=CONF.OLLAMA_MODEL,
                                    prompt=new_question_summary,
                                    format="json")
            
            summary_end = time.time()
            _,data = self.json_load(result_summary, mycontents_logger) 
            SimularityChecker().best_keyword_of_summary(data["short_summary"],self.keywords)
            SimularityChecker().best_keyword_of_summary(data["long_summary"],self.keywords)
            
            #print(result_summary.response) 
            return True, contentsMetaResult,result_summary,None  ,None  

        except Exception as e: 
            #trackback logging
            tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            mycontents_logger.error(f"Exception occurred: {e}, Args: {e.args}, Traceback: {tb_str}")

            error_ollamaMetaResult :ContentsMetaResult = self.to_error_ollamaModel() 
            return False, None, None, None, error_ollamaMetaResult


    def analysis_main(self, content, pred_keyword_list, org_name_list, mycontents_logger:logging.Logger, queueContent:ContentsQueueVO): #-> tuple[bool, ContentsMetaResult]:
        """Ollama 연계하여 분석 ( 요약분석, 평판분석 )
        """        
        try: 
            contentsMetaResult = ContentsMetaResult()
            contentsMetaResult.contentsMeta.method = "ollama"
            
            # 사전질의(주어진 db 키워드와 ai추출 키워드를 추출 및 비교)를 통한 키워드 검증로직 추가 20250429 mcst
            verify_start = time.time()
            pre_question_verify = self.question_verify.replace("pred_keywords_from_db", pred_keyword_list).replace("[contents]",content)
            result_verify = self.chat_ollama._client.generate(
                                    model=CONF.OLLAMA_MODEL,
                                    prompt=pre_question_verify,
                                    format="json")
            is_success_keywords, result_verify_json = self.json_load(result_verify, mycontents_logger)  
            related = result_verify_json['related']  # True : 관련성 있음, False : 관련성 없음
            
            #20251013 리자: 프롬프트 2)에서 키워드 삭제에 따른 변경:
            ai_keywords = result_verify_json["ai_keyword"]
                        
            verify_end = time.time()
            mycontents_logger.info(f"분석대상 사전검증 소요시간 : {verify_end-verify_start} 초 소요")
                        
            summary_start = time.time()
            #pred_keyword_list = [item + " 기술"  for item in pred_keyword_list]
            # 
            new_question_summary = self.question_summary.replace("pred_keywords_from_db", pred_keyword_list).replace("[contents]",content)
            result_summary = self.chat_ollama._client.generate(
                                    model=CONF.OLLAMA_MODEL,
                                    prompt=new_question_summary,
                                    format="json")
            
            summary_end = time.time()
            is_success, result_summary_json = self.json_load(result_summary, mycontents_logger)  
            
            # pred_keywords = SimularityChecker().best_keyword_of_summary(result_summary_json["short_summary"],self.keywords)
            # db키워드와 관련성이 없으면 키워드 추출하지 않음
            if related:
                keywords_verify = result_verify_json['reason']  # db_keyword_list 중 관련 키워드 최대 3개
                if isinstance(keywords_verify, list) and len(keywords_verify) > 0:
                    pred_keywords = SimularityChecker().best_keyword_of_summary(result_summary_json["short_summary"],keywords_verify) # 전체 키워드가 아닌 검증된 키워들 통해 유사도 검증 20250429 mcst
                else :
                    pred_keywords = None
                    mycontents_logger.info(f"키워드 추출대상 아님")        
            else:
                pred_keywords = None
                mycontents_logger.info(f"키워드 추출대상 아님")
                
            #LIZA: add article keywords (25.10.02)
            article_keywords = result_verify_json["ai_keyword"]
            
            article = ArticleKeywordsVO(
                orgId=queueContent.contentOrgId,
                keywords=pred_keywords,
                ai_keywords=article_keywords,
                success=is_success_keywords,
                url=queueContent.url
            )

            inserted_id = ArticleKeywordsService.insert_one(article)
            mycontents_logger.info(f"Inserted row id: {inserted_id}")
        
            
            summary_success = self.summary_to_ollamaModel_v2(result_summary, result_summary_json, contentsMetaResult, pred_keywords, ai_keywords, mycontents_logger) 
            contentsMetaResult.summarySucYN = "Y" if summary_success else "N"
            mycontents_logger.info(f"요약분석 소요시간 : {summary_end-summary_start} 초 소요")

            ### sentiment part!
            # 20251013 리자: 프롬프트 3)분리 --> 반복 x 3
            # orgId로 기관 이름 + 약어 등 조회
            orgId = queueContent.contentOrgId    
            orgName, combined_keywords = ContentsOrgService().getOrgNameAndKeywords(queueContent.contentOrgId)
            new_question_sentiment_ratio = self.question_sentiment_ratio.replace("[organization]", str(orgName) if orgName else "").replace("[contents]",content)
            if combined_keywords and isinstance(combined_keywords, list):
                synonyms_str = ", ".join(str(item) for item in combined_keywords)
                new_question_sentiment_ratio = new_question_sentiment_ratio.replace("[synonyms]", synonyms_str)
            else:
                new_question_sentiment_ratio = new_question_sentiment_ratio.replace("[synonyms]", str(orgName) if orgName else "") #if synonyms is empty, use orgName
            
            ### Log each time separately???
            sentiment_start = time.time()
            #3-1) ratio 추출
            result_sentiment_ratio = self.chat_ollama._client.generate(
                                    model=CONF.OLLAMA_MODEL,
                                    prompt=new_question_sentiment_ratio,
                                    format="json")
            # sentiment_end = time.time()
            is_success, result_sentiment_ratio_json = self.json_load(result_sentiment_ratio, mycontents_logger) 
            positiveRatio = self.str_to_double(result_sentiment_ratio_json.get("positiveRatio", "0"))
            negativeRatio = self.str_to_double(result_sentiment_ratio_json.get("negativeRatio", "0"))
            
            #3-2) reason 추출
            new_question_sentiment_reason = self.question_sentiment_reason.replace("[organization]", str(orgName) if orgName else "").replace("[contents]",content)
            if combined_keywords and isinstance(combined_keywords, list):
                synonyms_str = ", ".join(str(item) for item in combined_keywords)
                new_question_sentiment_reason = new_question_sentiment_reason.replace("[synonyms]", synonyms_str)
            else:
                new_question_sentiment_reason = new_question_sentiment_reason.replace("[synonyms]", str(orgName) if orgName else "") #if synonyms is empty, use orgName
            new_question_sentiment_reason = new_question_sentiment_reason.replace("[positiveRatio]", str(positiveRatio)).replace("[negativeRatio]", str(negativeRatio))
            
            result_sentiment_reason = self.chat_ollama._client.generate(
                                    model=CONF.OLLAMA_MODEL,
                                    prompt=new_question_sentiment_reason,
                                    format="json")
            is_success, result_sentiment_reason_json = self.json_load(result_sentiment_reason, mycontents_logger) 
            
            #3-3) keywords 추출
            new_question_sentiment_keywords = self.question_sentiment_keywords.replace("[organization]", str(orgName) if orgName else "").replace("[contents]",content)
            if combined_keywords and isinstance(combined_keywords, list):
                synonyms_str = ", ".join(str(item) for item in combined_keywords)
                new_question_sentiment_keywords = new_question_sentiment_keywords.replace("[synonyms]", synonyms_str)
            else:
                new_question_sentiment_keywords = new_question_sentiment_keywords.replace("[synonyms]", str(orgName) if orgName else "") #if synonyms is empty, use orgName
            new_question_sentiment_keywords = new_question_sentiment_keywords.replace("[positiveRatio]", str(positiveRatio)).replace("[negativeRatio]", str(negativeRatio))
            
            result_sentiment_keywords = self.chat_ollama._client.generate(
                                    model=CONF.OLLAMA_MODEL,
                                    prompt=new_question_sentiment_keywords,
                                    format="json")
            is_success, result_sentiment_keywords_json = self.json_load(result_sentiment_keywords, mycontents_logger) 
            
            
            #sentiment_success = self.sentiment_to_ollamaModel_v2(result_sentiment_ratio, result_sentiment_ratio_json, contentsMetaResult,  mycontents_logger) 
            
            #20251013 리자: assemble from separate prompts
            sentiment_separated_success = self.assemble_sentiment_to_ollamaModel_v2(queueContent, orgName, result_sentiment_ratio, result_sentiment_ratio_json, result_sentiment_reason, result_sentiment_reason_json, result_sentiment_keywords, result_sentiment_keywords_json, contentsMetaResult,  mycontents_logger) 
            contentsMetaResult.sentimentSucYN = "Y" if sentiment_separated_success else "N"
            sentiment_end = time.time()
            mycontents_logger.info(f"평판분석 소요시간 : {sentiment_end-sentiment_start} 초 소요")
            
            #요약만 성공해도 성공으로 처리                        
            contentsMetaResult.metaSucYN = "Y" if summary_success else "N"
            contentsMetaResult.metaAnalyzeDt = datetime.now(timezone.utc)  
            
            return True, contentsMetaResult,result_summary,result_sentiment,None 

        except Exception as e: 
            #trackback logging
            tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            mycontents_logger.error(f"Exception occurred: {e}, Args: {e.args}, Traceback: {tb_str}")

            error_ollamaMetaResult :ContentsMetaResult = self.to_error_ollamaModel() 
            return False, None, None, None, error_ollamaMetaResult



    def json_load(self, result, mycontents_logger:logging.Logger): 
        """Ollama 분석 결과의 json 로드 
        """          
        try:
            result_analysis_resp = result.response.replace("`","")
            result_analysis_resp = result_analysis_resp.replace("json","")
            result_analysis_resp = result_analysis_resp.replace("\n","")
            result_analysis_resp = json.loads(result_analysis_resp) 
            return True, result_analysis_resp
        except Exception as e :
            # json 으로 던져도 안오는 경우 있음 .
            mycontents_logger.error(str(e))
            return False, None


    def summary_to_ollamaModel_v2(self,result_summary:GenerateResponse, result_summary_json, contentsMetaResult:ContentsMetaResult, pred_kewords:dict, ai_keywords:list, mycontents_logger:logging.Logger) -> bool:
        """Ollama 분석 결과의 json --> summary 모델 변환 
        """          
        try:
            
            #20251013 리자: 프롬프트 2)에서 키워드 삭제에 따른 변경:
            # keyword = result_summary_json["keyword"]
            # if keyword is not None and isinstance(keyword,list): 
            #     contentsMetaResult.contentsMeta.keywords = keyword
            keyword = ai_keywords
            if keyword is not None and isinstance(keyword,list): 
                contentsMetaResult.contentsMeta.keywords = keyword
                    
            predkeywords = pred_kewords #pre-defined keywords
            if predkeywords is not None and isinstance(predkeywords,dict):
                contentsMetaResult.contentsMeta.predKeywords = self.nomalize_keywords(predkeywords)

            short_summary = result_summary_json["short_summary"]
            if short_summary is not None and isinstance(short_summary,str):
                contentsMetaResult.contentsMeta.shortSummary = short_summary
                    
            long_summary = result_summary_json["long_summary"]
            if long_summary is not None:
                if isinstance(long_summary,str):
                    contentsMetaResult.contentsMeta.longSummary = long_summary

            contentsMetaResult.contentsMeta.llmSummaryMeta = None
            
            return True
        
        except Exception as e :
            mycontents_logger.error(str(e))
            return False 

    def summary_to_ollamaModel(self,result_summary:GenerateResponse, result_summary_json, contentsMetaResult:ContentsMetaResult, mycontents_logger:logging.Logger) -> bool:
        """Ollama 분석 결과의 json --> summary 모델 변환 
        """          
        
        try:
            
            keyword = result_summary_json["keyword"]
            if keyword is not None and isinstance(keyword,list): 
                contentsMetaResult.contentsMeta.keywords = keyword
                    
            predkeywords = result_summary_json["predkeywords"]
            if predkeywords is not None and isinstance(predkeywords,dict):
                contentsMetaResult.contentsMeta.predKeywords = self.nomalize_keywords(predkeywords)

            short_summary = result_summary_json["short_summary"]
            if short_summary is not None and isinstance(short_summary,str):
                contentsMetaResult.contentsMeta.shortSummary = short_summary
                    
            long_summary = result_summary_json["long_summary"]
            if long_summary is not None:
                if isinstance(long_summary,str):
                    contentsMetaResult.contentsMeta.longSummary = long_summary

            llmAnalysisMeta = LLMAnalysisMeta()        
            #total_tokens = prompt_tokens + response_tokens

            try:
                # llmAnalysisMeta.contents_id = contentsId
                llmAnalysisMeta.analyze_type = "ollama"
                llmAnalysisMeta.response_metadata_model = result_summary.model if result_summary.model is not None else ""
                # llmAnalysisMeta.response_metadata_createdDt = result_summary.created_at if result_summary.created_at is not None else ""
                # llmAnalysisMeta.response_metadata_done = result_summary.done if result_summary.done is not None else False
                # llmAnalysisMeta.response_metadata_doneReason = result_summary.done_reason if result_summary.done_reason is not None else ""
                # llmAnalysisMeta.response_metadata_totalDuration = result_summary.total_duration if result_summary.total_duration is not None else ""
                # llmAnalysisMeta.response_metadata_loadDuration = result_summary.load_duration if result_summary.load_duration is not None else ""
                # llmAnalysisMeta.response_metadata_promptEvalCount = result_summary.prompt_eval_count if result_summary.prompt_eval_count is not None else ""
                # llmAnalysisMeta.response_metadata_promptEvalDuration = result_summary.prompt_eval_duration if result_summary.prompt_eval_duration is not None else ""
                # llmAnalysisMeta.response_metadata_evalCount = result_summary.eval_count if result_summary.eval_count is not None else ""
                # llmAnalysisMeta.response_metadata_evalDuration = result_summary.eval_duration if result_summary.eval_duration is not None else ""
                #llmAnalysisMeta.usage_metadata_inputToken = prompt_tokens if prompt_tokens is not None else 0
                #llmAnalysisMeta.usage_metadata_outputToken = response_tokens if response_tokens is not None else 0
                #llmAnalysisMeta.usage_metadata_totalToken = total_tokens if total_tokens is not None else 0
                #llmAnalysisMeta.regDt = datetime.now(timezone.utc)                
            except Exception as e: 
                pass        
            contentsMetaResult.contentsMeta.llmSummaryMeta = llmAnalysisMeta
            
            return True
        
        except Exception as e :
            mycontents_logger.error(str(e))
            return False 


    def extract_double(s):
        match = re.search(r"-?\d+\.\d+|-?\d+", s)  # 소수점 포함 숫자 찾기
        try:
            return float(match.group()) if match else None
        except Exception as e :
            return 0.0

    def extract_int(s):
        match = re.search(r"-?\d+\.\d+|-?\d+", s)  # 소수점 포함 숫자 찾기
        try:
            return int(match.group()) if match else None
        except Exception as e :
            return 0

    def str_to_double(self, strvalue): 
        try:
            return float(strvalue)
        except Exception as e :
            return self.extract_double(strvalue)  # 실패 시 extract_double 호출
    def str_to_int(self, strvalue): 
        try:
            return int(strvalue)
        except Exception as e :
            return self.extract_int(strvalue)  # 실패 시 extract_double 호출

    def nomalize_sentiment(self, positiveRatio, negativeRatio,neutralRatio): 
        sum = positiveRatio + negativeRatio + neutralRatio 
        if not (sum== 100):
            positiveRatio = positiveRatio/sum * 100
            negativeRatio = negativeRatio/sum * 100
            neutralRatio = neutralRatio/sum * 100
            positiveRatio = round(positiveRatio)
            negativeRatio = round(negativeRatio)
            neutralRatio  = round(neutralRatio)

        return  positiveRatio, negativeRatio, neutralRatio
        
    
    def nomalize_keywords(self,keyword_list:dict):
        sum = 0
        result_dict = {}
        for keyword,value in keyword_list.items():
            value = self.str_to_double(value)
            result_dict[keyword] = value
            sum += value 
        
        return  result_dict


    def assemble_sentiment_to_ollamaModel_v2(self, queueContent:ContentsQueueVO, orgName:str, result_sentiment_ratio:GenerateResponse, result_sentiment_ratio_json, result_sentiment_reason:GenerateResponse, result_sentiment_reason_json, result_sentiment_keywords:GenerateResponse, result_sentiment_keywords_json, contentsMetaResult:ContentsMetaResult, mycontents_logger:logging.Logger) -> bool:
        """Ollama 분석 3개의 결과의 json을 통합하여 --> sentiment 모델 변환"""           
        try:
            contentsMetaResult.contentsMeta.sentiments = []
            singleSentimentInfo = SentimentInfo()
            singleSentimentInfo.orgName = orgName
            singleSentimentInfo.orgId = queueContent.contentOrgId
            singleSentimentInfo.positiveRatio = self.str_to_double(result_sentiment_ratio_json.get("positiveRatio", "0"))
            singleSentimentInfo.negativeRatio = self.str_to_double(result_sentiment_ratio_json.get("negativeRatio", "0"))
            singleSentimentInfo.neutralRatio = self.str_to_double(result_sentiment_ratio_json.get("neutralRatio", "0"))
            # Safe handling for list fields
            positiveKeywords = result_sentiment_keywords_json.get("positiveKeywords", [])
            singleSentimentInfo.positiveKeywords = positiveKeywords if isinstance(positiveKeywords, list) else []
            
            negativeKeywords = result_sentiment_keywords_json.get("negativeKeywords", [])
            singleSentimentInfo.negativeKeywords = negativeKeywords if isinstance(negativeKeywords, list) else []
            
            # Safe handling for string fields
            singleSentimentInfo.positiveReason = str(result_sentiment_reason_json.get("positiveReason", ""))
            singleSentimentInfo.negativeReason = str(result_sentiment_reason_json.get("negativeReason", ""))
            singleSentimentInfo.reason = str(result_sentiment_reason_json.get("reason", ""))
            contentsMetaResult.contentsMeta.sentiments.append(singleSentimentInfo) 
            return True
        except Exception as e :
            mycontents_logger.error(str(e))
            return False 

    def sentiment_to_ollamaModel_v2(self,result_sentiment:GenerateResponse, result_sentiment_json, contentsMetaResult:ContentsMetaResult, mycontents_logger:logging.Logger) -> bool:
        """Ollama 분석 결과의 json --> sentiment 모델 변환"""           
        try:            
            sentiments = result_sentiment_json["sentiments"]
            contentsMetaResult.contentsMeta.sentiments = []        
            
            if sentiments is not None and isinstance(sentiments, list):
                #organization = sentiments["organization"]
                for sentiment in sentiments:
                    sentiment_info = SentimentInfo()
                    #sentiment = self.validation_check_sentiment(sentiment)
                    if sentiment["organization"] == None:
                        sentiment_info.orgName = ""
                    elif isinstance(sentiment["organization"],list):
                        if len(sentiment["organization"]) == 1:
                            if isinstance(sentiment["organization"][0],str):
                                sentiment_info.orgName= sentiment["organization"][0]        
                            else: 
                                sentiment_info.orgName = ""   
                        else: 
                            sentiment_info.orgName = ""
                    elif isinstance(sentiment["organization"],str):
                        sentiment_info.orgName= sentiment["organization"]
                    else:
                        raise Exception(f"올라마의 답변이 잘못되었습니다. (orgName : {sentiment['organization']})")
                    
                    if sentiment_info.orgName:
                        sentiment_info.orgId = ContentsOrgService().get_orgId_by_synonym(sentiment_info.orgName)
                    else :
                        sentiment_info.orgId = ""
                    sentiment_info.reason= sentiment.get("reason", "") 

                    positiveRatioStr = self.str_to_double(sentiment.get("positiveRatio", "")) 
                    negativeRatioStr = self.str_to_double(sentiment.get("negativeRatio", "") )
                    neutralRatioStr = self.str_to_double(sentiment.get("neutralRatio", "") )

                    positiveRatio, negativeRatio, neutralRatio = self.nomalize_sentiment(positiveRatioStr, negativeRatioStr, neutralRatioStr)

                    sentiment_info.positiveRatio = positiveRatio
                    sentiment_info.negativeRatio = negativeRatio  
                    sentiment_info.neutralRatio = neutralRatio 
                     
                    sentiment_info.positiveKeywords = sentiment.get("positiveKeywords", "") 
                    if not isinstance(sentiment_info.positiveKeywords,list):                        
                        sentiment_info.positiveKeywords = [""]
                    sentiment_info.negativeKeywords = sentiment.get("negativeKeywords", "") 
                    if not isinstance(sentiment_info.negativeKeywords,list):                        
                        sentiment_info.negativeKeywords = [""] 

                    sentiment_info.positiveReason= sentiment.get("positiveReason", "")     
                    if not isinstance(sentiment_info.positiveReason,str):
                        sentiment_info.positiveReason = ""
                    
                    sentiment_info.negativeReason = sentiment.get("negativeReason", "") 
                    if not isinstance(sentiment_info.negativeReason,str):
                        sentiment_info.negativeReason = ""
                    
                    contentsMetaResult.contentsMeta.sentiments.append(sentiment_info)                     
                
            contentsMetaResult.contentsMeta.llmSentimentMeta = None
            
            return True
        
        except Exception as e :
            mycontents_logger.error(str(e))
            return False 
    

    def sentiment_to_ollamaModel(self,result_sentiment:GenerateResponse, result_sentiment_json, contentsMetaResult:ContentsMetaResult, mycontents_logger:logging.Logger) -> bool:
        """Ollama 분석 결과의 json --> sentiment 모델 변환"""           
        try:            
            sentiments = result_sentiment_json["sentiments"]
            contentsMetaResult.contentsMeta.sentiments = []        
            
            if sentiments is not None and isinstance(sentiments, list):
                #organization = sentiments["organization"]
                for sentiment in sentiments:
                    sentiment_info = SentimentInfo()
                    #sentiment = self.validation_check_sentiment(sentiment)
                    if sentiment["organization"] == None:
                        sentiment_info.orgName = ""
                    elif isinstance(sentiment["organization"],list):
                        if len(sentiment["organization"]) == 1:
                            if isinstance(sentiment["organization"][0],str):
                                sentiment_info.orgName= sentiment["organization"][0]        
                            else: 
                                sentiment_info.orgName = ""   
                        else: 
                            sentiment_info.orgName = ""
                    elif isinstance(sentiment["organization"],str):
                        sentiment_info.orgName= sentiment["organization"]
                    else:
                        raise Exception(f"올라마의 답변이 잘못되었습니다. (orgName : {sentiment['organization']})")
                    
                    if sentiment_info.orgName:
                        sentiment_info.orgId = ContentsOrgService().get_orgId_by_synonym(sentiment_info.orgName)
                    else :
                        sentiment_info.orgId = ""
                    sentiment_info.reason= sentiment.get("reason", "") 

                    positiveRatioStr = self.str_to_double(sentiment.get("positiveRatio", "")) 
                    negativeRatioStr = self.str_to_double(sentiment.get("negativeRatio", "") )
                    neutralRatioStr = self.str_to_double(sentiment.get("neutralRatio", "") )

                    positiveRatio, negativeRatio, neutralRatio = self.nomalize_sentiment(positiveRatioStr, negativeRatioStr, neutralRatioStr)

                    sentiment_info.positiveRatio = positiveRatio
                    sentiment_info.negativeRatio = negativeRatio  
                    sentiment_info.neutralRatio = neutralRatio 
                     
                    sentiment_info.positiveKeywords = sentiment.get("positiveKeywords", "") 
                    if not isinstance(sentiment_info.positiveKeywords,list):                        
                        sentiment_info.positiveKeywords = [""]
                    sentiment_info.negativeKeywords = sentiment.get("negativeKeywords", "") 
                    if not isinstance(sentiment_info.negativeKeywords,list):                        
                        sentiment_info.negativeKeywords = [""] 

                    sentiment_info.positiveReason= sentiment.get("positiveReason", "")     
                    if not isinstance(sentiment_info.positiveReason,str):
                        sentiment_info.positiveReason = ""
                    
                    sentiment_info.negativeReason = sentiment.get("negativeReason", "") 
                    if not isinstance(sentiment_info.negativeReason,str):
                        sentiment_info.negativeReason = ""
                    
                    contentsMetaResult.contentsMeta.sentiments.append(sentiment_info)                     

            llmAnalysisMeta = LLMAnalysisMeta()     
            #total_tokens = prompt_tokens + response_tokens
               
            try:
                # llmAnalysisVO.contents_id = contentsId
                llmAnalysisMeta.analyze_type = "ollama"
                llmAnalysisMeta.response_metadata_model = result_sentiment.model if result_sentiment.model is not None else ""
                # llmAnalysisMeta.response_metadata_createdDt = result_sentiment.created_at if result_sentiment.created_at is not None else ""
                # llmAnalysisMeta.response_metadata_done = result_sentiment.done if result_sentiment.done is not None else False
                # llmAnalysisMeta.response_metadata_doneReason = result_sentiment.done_reason if result_sentiment.done_reason is not None else ""
                # llmAnalysisMeta.response_metadata_totalDuration = result_sentiment.total_duration if result_sentiment.total_duration is not None else ""
                # llmAnalysisMeta.response_metadata_loadDuration = result_sentiment.load_duration if result_sentiment.load_duration is not None else ""
                # llmAnalysisMeta.response_metadata_promptEvalCount = result_sentiment.prompt_eval_count if result_sentiment.prompt_eval_count is not None else ""
                # llmAnalysisMeta.response_metadata_promptEvalDuration = result_sentiment.prompt_eval_duration if result_sentiment.prompt_eval_duration is not None else ""
                # llmAnalysisMeta.response_metadata_evalCount = result_sentiment.eval_count if result_sentiment.eval_count is not None else ""
                # llmAnalysisMeta.response_metadata_evalDuration = result_sentiment.eval_duration if result_sentiment.eval_duration is not None else ""
                #llmAnalysisMeta.usage_metadata_inputToken = prompt_tokens if prompt_tokens is not None else 0
                #llmAnalysisMeta.usage_metadata_outputToken = response_tokens if response_tokens is not None else 0
                #llmAnalysisMeta.usage_metadata_totalToken = total_tokens if total_tokens is not None else 0
                llmAnalysisMeta.regDt = datetime.now(timezone.utc)                
            except Exception as e: 
                pass    
                
            contentsMetaResult.contentsMeta.llmSentimentMeta = llmAnalysisMeta
            
            return True
        
        except Exception as e :
            mycontents_logger.error(str(e))
            return False 
    
    
        
    def validation_check_sentiment(self,sentiment):
        reason = sentiment.get("reason", "") 
        if not isinstance(reason,str):
            reason = "" 
        # positiveRatio = sentiment.get("positiveRatio", "") 
        # if not isinstance(positiveRatio,str):
        #     if isinstance(positiveRatio,str):
        # 1. typecheck
        # 2.  0 ~ 9 in str
        negativeRatio = sentiment.get("negativeRatio", "") 
        if not isinstance(reason,str):
            reason = ""
        neutralRatio = sentiment.get("neutralRatio", "") 
        if not isinstance(reason,str):
            reason = ""
        positiveKeywords = sentiment.get("positiveKeywords", "") 
        if not isinstance(reason,str):
            reason = ""
        negativeKeywords = sentiment.get("negativeKeywords", "") 
        if not isinstance(reason,str):
            reason = ""
        positiveReason = sentiment.get("positiveReason", "") 
        if not isinstance(reason,str):
            reason = ""
        negativeReason = sentiment.get("negativeReason", "") 
        if not isinstance(reason,str):
            reason = ""
        pass 
    
    def to_error_ollamaModel(self) -> ContentsMetaResult:
        
        ollamaModel = ContentsMetaResult()
        ollamaModel.contentsMeta = None
        ollamaModel.metaSucYN = "N" 
        ollamaModel.metaAnalyzeDt = datetime.now(timezone.utc)
        return ollamaModel
  
if __name__ =="__main__":
    
    analysisOllamaGenerateCall = AnalysisOllamaGenerateCall()
    analysisOllamaGenerateCall.analysis_main()
    
    pass 