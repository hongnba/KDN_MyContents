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

from ksubscribe_share.logger import Logger
from ksubscribe_server.models.contentsMetaResult import ContentsMetaResult
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsMeta, SentimentInfo
from ksubscribe_share.db.dbmodelV2.llmAnalysisMeta import LLMAnalysisMeta
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsMeta
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService

from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.predefineKeywordService import PredefineKeywordService
from ksubscribe_share.db.service.contentsService import ContentsService
from ksubscribe_server.analysis.analysis_ollama_base import AnalysisOllamaBase
import ksubscribe_share.config as CONF


class AnalysisOllamaGenerateCall_RAG(AnalysisOllamaBase):

    def __init__(self):
        self.chat_ollama =  ChatOllama(model = CONF.OLLAMA_MODEL,
                                       base_url= CONF.OLLAMA_URL, 
                                       format="json") 
        
    def analysis_main(self, content, pred_keyword_list, org_name_list, mycontents_logger:logging.Logger) -> tuple[bool, ContentsMetaResult]:
        """Ollama 연계하여 분석 ( 요약분석, 평판분석 )
        """        
        try:
            contentsMetaResult = ContentsMetaResult()
            contentsMetaResult.contentsMeta.method = "ollama"
            new_question_summary = self.question_summary.replace("pred_keywords_from_db", pred_keyword_list).replace("[contents]",content)
            result_summary = self.chat_ollama._client.generate(prompt=new_question_summary,format="json")
            result_summary_json = self.json_load(result_summary)
            summary_success = self.summary_to_ollamaModel(result_summary_json, contentsMetaResult) 
            contentsMetaResult.summarySucYN = "Y" if summary_success else "N"
            mycontents_logger.debug(f"요약분석 소요시간 : {self.nanoseconds_to_seconds(result_summary.total_duration)} 초 소요")

            new_question_sentiment = self.question_sentiment.replace("org_name_list_from_db", org_name_list).replace("[contents]",content)
            result_sentiment = self.chat_ollama._client.generate(prompt=new_question_sentiment,format="json")
            result_sentiment_json = self.json_load(result_sentiment)
            sentiment_success = self.sentiment_to_ollamaModel(result_sentiment_json, contentsMetaResult) 
            contentsMetaResult.sentimentSucYN = "Y" if sentiment_success else "N"
            mycontents_logger.debug(f"평판분석 소요시간 : {self.nanoseconds_to_seconds(result_sentiment.total_duration)} 초 소요")
            
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


    def json_load(self, result, mycontents_logger:logging.Logger): 
        """Ollama 분석 결과의 json 로드 
        """          
        try:
            result_analysis_resp = result.response.replace("`","")
            result_analysis_resp = result_analysis_resp.replace("json","")
            result_analysis_resp = result_analysis_resp.replace("\n","")
            result_analysis_resp = json.loads(result_analysis_resp) 
            return True
        except Exception as e :
            # json 으로 던져도 안오는 경우 있음 .
            mycontents_logger.error(str(e))
            return False 


    def summary_to_ollamaModel(self,result_summary, contentsMetaResult:ContentsMetaResult, mycontents_logger:logging.Logger) -> bool:
        """Ollama 분석 결과의 json --> summary 모델 변환 
        """          
        
        try:
            
            keyword = result_summary["keyword"]
            if keyword is not None and isinstance(keyword,list): 
                    contentsMetaResult.contentsMeta.keywords = keyword
                    
            predkeywords = result_summary["predkeywords"]
            if predkeywords is not None and isinstance(predkeywords,dict):
                    contentsMetaResult.contentsMeta.predKeywords = predkeywords

            short_summary = result_summary["short_summary"]
            if short_summary is not None and isinstance(short_summary,str):
                    contentsMetaResult.contentsMeta.shortSummary = short_summary
                    
            long_summary = result_summary["long_summary"]
            if long_summary is not None:
                if isinstance(long_summary,str):
                    contentsMetaResult.contentsMeta.longSummary = long_summary

            llmAnalysisMeta = LLMAnalysisMeta()        
            try:
                # llmAnalysisVO.contents_id = contentsId
                # llmAnalysisVO.analyze_type = "ollama"
                # llmAnalysisVO.response_metadata_model = response_metadata["model"] if response_metadata["model"] is not None else ""
                # llmAnalysisVO.response_metadata_createdDt = response_metadata["created_at"] if response_metadata["model"] is not None else None
                # llmAnalysisVO.response_metadata_done = response_metadata["done"] if response_metadata["model"] is not None else False
                # llmAnalysisVO.response_metadata_doneReason = response_metadata["done_reason"] if response_metadata["model"] is not None else ""
                # llmAnalysisVO.response_metadata_totalDuration = response_metadata["total_duration"] if response_metadata["model"] is not None else 0
                # llmAnalysisVO.response_metadata_loadDuration = response_metadata["load_duration"] if response_metadata["model"] is not None else 0
                # llmAnalysisVO.response_metadata_promptEvalCount = response_metadata["prompt_eval_count"] if response_metadata["model"] is not None else 0
                # llmAnalysisVO.response_metadata_promptEvalDuration = response_metadata["prompt_eval_duration"] if response_metadata["model"] is not None else 0
                # llmAnalysisVO.response_metadata_evalCount = response_metadata["eval_count"] if response_metadata["model"] is not None else 0
                # llmAnalysisVO.response_metadata_evalDuration = response_metadata["eval_duration"] if response_metadata["model"] is not None else 0
                # llmAnalysisVO.usage_metadata_inputToken = usage_metadata["input_tokens"] if response_metadata["model"] is not None else 0
                # llmAnalysisVO.usage_metadata_outputToken = usage_metadata["output_tokens"] if response_metadata["model"] is not None else 0
                # llmAnalysisVO.usage_metadata_totalToken = usage_metadata["total_tokens"] if response_metadata["model"] is not None else 0
                llmAnalysisMeta.regDt = datetime.now(timezone.utc)                
            except Exception as e: 
                pass        
            contentsMetaResult.contentsMeta.llmSummaryMeta = llmAnalysisMeta
            
            return True
        
        except Exception as e :
            mycontents_logger.error(str(e))
            return False 



    def sentiment_to_ollamaModel(self,result_sentiment, contentsMetaResult:ContentsMetaResult, mycontents_logger:logging.Logger) -> bool:
        """Ollama 분석 결과의 json --> sentiment 모델 변환 
        """          
        
        try:
            
            sentiments = result_sentiment["sentiments"]
            contentsMetaResult.contentsMeta.sentiments = []        
            
            if sentiments is not None and isinstance(sentiments, list):
                #organization = sentiments["organization"]
                for sentiment in sentiments:
                    sentiment_info = SentimentInfo()
                    sentiment_info.orgName= sentiment["organization"]
                    sentiment_info.orgId = ContentsOrgService().get_orgId_by_synonym(sentiment_info.orgName)
                    sentiment_info.reason= sentiment["Reason"]
                    sentiment_info.positiveRatio= sentiment["positiveRatio"]
                    sentiment_info.negativeRatio= sentiment["negativeRatio"]
                    sentiment_info.neutralRatio= sentiment["neutralRatio"]
                    sentiment_info.positiveKeywords = sentiment["positiveKeywords"]
                    sentiment_info.negativeKeywords = sentiment["negativeKeywords"]
                    sentiment_info.positiveReason=sentiment["positiveReason"]
                    sentiment_info.negativeReason =sentiment["negativeReason"]   
                    contentsMetaResult.contentsMeta.sentiments.append(sentiment_info)                     

            llmAnalysisMeta = LLMAnalysisMeta()        
            try:
                # llmAnalysisVO.contents_id = contentsId
                # llmAnalysisVO.analyze_type = "ollama"
                # llmAnalysisVO.response_metadata_model = response_metadata["model"] if response_metadata["model"] is not None else ""
                # llmAnalysisVO.response_metadata_createdDt = response_metadata["created_at"] if response_metadata["model"] is not None else None
                # llmAnalysisVO.response_metadata_done = response_metadata["done"] if response_metadata["model"] is not None else False
                # llmAnalysisVO.response_metadata_doneReason = response_metadata["done_reason"] if response_metadata["model"] is not None else ""
                # llmAnalysisVO.response_metadata_totalDuration = response_metadata["total_duration"] if response_metadata["model"] is not None else 0
                # llmAnalysisVO.response_metadata_loadDuration = response_metadata["load_duration"] if response_metadata["model"] is not None else 0
                # llmAnalysisVO.response_metadata_promptEvalCount = response_metadata["prompt_eval_count"] if response_metadata["model"] is not None else 0
                # llmAnalysisVO.response_metadata_promptEvalDuration = response_metadata["prompt_eval_duration"] if response_metadata["model"] is not None else 0
                # llmAnalysisVO.response_metadata_evalCount = response_metadata["eval_count"] if response_metadata["model"] is not None else 0
                # llmAnalysisVO.response_metadata_evalDuration = response_metadata["eval_duration"] if response_metadata["model"] is not None else 0
                # llmAnalysisVO.usage_metadata_inputToken = usage_metadata["input_tokens"] if response_metadata["model"] is not None else 0
                # llmAnalysisVO.usage_metadata_outputToken = usage_metadata["output_tokens"] if response_metadata["model"] is not None else 0
                # llmAnalysisVO.usage_metadata_totalToken = usage_metadata["total_tokens"] if response_metadata["model"] is not None else 0
                LLMAnalysisMeta.regDt = datetime.now(timezone.utc)                
            except Exception as e: 
                pass    
                
            contentsMetaResult.contentsMeta.llmSentimentMeta = llmAnalysisMeta
            
            return True
        
        except Exception as e :
            mycontents_logger.error(str(e))
            return False 
    

    def to_error_ollamaModel(self) -> ContentsMetaResult:
        
        ollamaModel = ContentsMetaResult()
        ollamaModel.contentsMeta = None
        ollamaModel.metaSucYN = "N" 
        ollamaModel.metaAnalyzeDt = datetime.now(timezone.utc)
        return ollamaModel

     

if __name__ =="__main__":
    
    analysisOllamaGenerateCall_rag = AnalysisOllamaGenerateCall_RAG()
    analysisOllamaGenerateCall_rag.analysis_main()
    
    pass 

