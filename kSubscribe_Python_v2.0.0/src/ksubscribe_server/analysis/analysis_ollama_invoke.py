#from langchain_community.chat_models import ChatOllama
import requests
from openai import OpenAI
import traceback
import pandas as pd 
from datetime import datetime, timezone
import logging 
from langchain_ollama import ChatOllama
import ksubscribe_share.config as CONF
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
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService

from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.predefineKeywordService import PredefineKeywordService
from ksubscribe_share.db.service.contentsService import ContentsService
from ksubscribe_server.analysis.analysis_ollama_base import AnalysisOllamaBase


class AnalysisOllamaInvokeCall(AnalysisOllamaBase):

    def __init__(self):
        # 하드코딩된 기존 설정 (보관용 주석):
        # self.chat_ollama =  ChatOllama(model="EEVE-Korean-10.8B",base_url="http://192.168.1.191:11434")
        # /llama-3-Korean-Bllossom-8B-gguf-Q4_K_M:latest

        # 현재는 설정 파일의 값을 사용하도록 변경
        self.chat_ollama = ChatOllama(model=CONF.OLLAMA_MODEL, base_url=CONF.OLLAMA_URL)

    def messages_to_prompt(self, messages):
        prompt = []
        for msg in messages:
            if msg["role"] == "system":
                prompt.append(f"System: {msg['content']}")
            elif msg["role"] == "user":
                prompt.append(f"User: {msg['content']}")
        return "\n".join(prompt)

    def _convert_to_int(self, value):
        """
        값을 float으로 변환, 변환이 불가능한 경우 None 반환
        """
        try:
            if value is not None:
                return int(value)
        except (ValueError, TypeError):
            return 0
        return None      
    
 
    def fix_json(self, json_string):
        # 문자열의 앞뒤를 검사하여 { } 추가
        if not json_string.strip().startswith("{"):
            json_string = "{" + json_string.strip()
        if not json_string.strip().endswith("}"):
            json_string = json_string.strip() + "}"
        return json_string

    def parse_content(self, result_analysis):
        contentsMeta = ContentsMeta()

        try:
            keyword = result_analysis["keyword"]
            if keyword is not None and isinstance(keyword, list):
                contentsMeta.keywords = keyword                
                
            predkeywords = result_analysis["predkeywords"]
            if predkeywords is not None and isinstance(predkeywords, Dict):
                contentsMeta.predKeywords = predkeywords                
                
            short_summary = result_analysis["short_summary"]
            if short_summary is not None and isinstance(short_summary, str):
                contentsMeta.shortSummary = short_summary                

            long_summary = result_analysis["long_summary"]
            if long_summary is not None and isinstance(long_summary, str):
                contentsMeta.longSummary = long_summary                

            sentiments = result_analysis["sentiments"]
            contentsMeta.sentiments = []
            if sentiments is not None and isinstance(sentiments, list):
                
                for sentiment in sentiments : 
                    sentimentInfo = SentimentInfo()                            
                    sentimentInfo.orgName = sentiment["orgName"]
                    sentimentInfo.orgId = ContentsOrgService().get_orgId_by_synonym(sentimentInfo.orgName)
                    sentimentInfo.positiveRatio = sentimentInfo._convert_to_float(sentiment["positiveRatio"])
                    sentimentInfo.negativeRatio = sentimentInfo._convert_to_float(sentiment["negativeRatio"]) 
                    sentimentInfo.neutralRatio = sentimentInfo._convert_to_float(sentiment["neutralRatio"])   
                    sentimentInfo.positiveReason = sentiment["positiveReason"]
                    sentimentInfo.negativeReason = sentiment["negativeReason"]
                    sentimentInfo.reason = f"{sentimentInfo.positiveReason}, {sentimentInfo.negativeReason}"
                    positiveKeywords = sentiment["positiveKeywords"] 
                    if positiveKeywords is None:
                        positiveKeywords = sentiment["positiveKeyword"] 
                    sentimentInfo.positiveKeywords = positiveKeywords
                    negativeKeywords = sentiment["negativeKeywords"] 
                    if negativeKeywords is None:
                        positiveKeywords = sentiment["negativeKeyword"] 
                    sentimentInfo.negativeKeywords = negativeKeywords
                    contentsMeta.sentiments.append(sentimentInfo)      
        except Exception as e: 
            pass
        
        return contentsMeta
        
    def to_ollamaModel(self, contentsId:str, invoke_result:BaseMessage) -> ContentsMetaResult:
        
        contentsMetaResult = ContentsMetaResult()
        content = None
        try:
            invoke_content = self.fix_json(invoke_result.content)
            content = json.loads(invoke_content)
            contentsMetaResult.contentsMeta = self.parse_content(content)
            #ollamaModel.contentsMeta = ContentsMeta.from_mongo(content)
        except Exception as e: 
            pass
        
        usage_metadata = invoke_result.usage_metadata
        response_metadata = invoke_result.response_metadata
        
        llmAnalysisMeta = LLMAnalysisMeta()        
        try:
            llmAnalysisMeta.contents_id = contentsId
            llmAnalysisMeta.analyze_type = "ollama"
            llmAnalysisMeta.response_metadata_model = response_metadata["model"] if response_metadata["model"] is not None else ""
            llmAnalysisMeta.response_metadata_createdDt = response_metadata["created_at"] if response_metadata["model"] is not None else None
            llmAnalysisMeta.response_metadata_done = response_metadata["done"] if response_metadata["model"] is not None else False
            llmAnalysisMeta.response_metadata_doneReason = response_metadata["done_reason"] if response_metadata["model"] is not None else ""
            llmAnalysisMeta.response_metadata_totalDuration = response_metadata["total_duration"] if response_metadata["model"] is not None else 0
            llmAnalysisMeta.response_metadata_loadDuration = response_metadata["load_duration"] if response_metadata["model"] is not None else 0
            llmAnalysisMeta.response_metadata_promptEvalCount = response_metadata["prompt_eval_count"] if response_metadata["model"] is not None else 0
            llmAnalysisMeta.response_metadata_promptEvalDuration = response_metadata["prompt_eval_duration"] if response_metadata["model"] is not None else 0
            llmAnalysisMeta.response_metadata_evalCount = response_metadata["eval_count"] if response_metadata["model"] is not None else 0
            llmAnalysisMeta.response_metadata_evalDuration = response_metadata["eval_duration"] if response_metadata["model"] is not None else 0
            llmAnalysisMeta.usage_metadata_inputToken = usage_metadata["input_tokens"] if response_metadata["model"] is not None else 0
            llmAnalysisMeta.usage_metadata_outputToken = usage_metadata["output_tokens"] if response_metadata["model"] is not None else 0
            llmAnalysisMeta.usage_metadata_totalToken = usage_metadata["total_tokens"] if response_metadata["model"] is not None else 0
            llmAnalysisMeta.regDt = datetime.now(timezone.utc)
        except Exception as e: 
            pass        
        
        
        if llmAnalysisMeta.response_metadata_done:
            contentsMetaResult.metaSucYN = "Y"            
            contentsMetaResult.metaAnalyzeDt = contentsMetaResult.response_metadata_createdDt
        else :
            contentsMetaResult.metaSucYN = "N" 
            contentsMetaResult.metaAnalyzeDt = None
        
        contentsMetaResult.contentsMeta.llmSummaryMeta = llmAnalysisMeta

        return contentsMetaResult


    def to_error_ollamaModel(self) -> ContentsMetaResult:
        
        contentsMetaResult = ContentsMetaResult()
        contentsMetaResult.contentsMeta = None
        contentsMetaResult.metaSucYN = "N" 
        contentsMetaResult.metaAnalyzeDt = datetime.now(timezone.utc)
        return contentsMetaResult

     
    # local ollama
    def analysis_main(self, raw_data, pred_keyword_list, org_name_list, mycontents_logger:logging.Logger, contentsId:str) ->  Tuple[bool, ContentsMetaResult]:

        try:
            
            new_question = self.question.replace("pred_keywords_from_db", pred_keyword_list).replace("org_name_list_from_db", org_name_list)
            #new_question = self.question_summary.replace("pred_keywords_from_db", pred_keyword_list)
            
            messages=[
                {"role": "system", "content": new_question},
                {"role": "user", "content": f"{raw_data}"},
            ]
            llm_question = self.messages_to_prompt(messages)
            # 원격 호출로 변경 필요

            #-----------------
            invoke_result = self.chat_ollama.invoke(llm_question)            
            contentsMetaResult :ContentsMetaResult = self.to_ollamaModel(contentsId, invoke_result) 
            mycontents_logger.debug(f"소요시간 : {contentsMetaResult.contentsMeta.llmSummaryMeta.response_metadata_evalDuration }, predict_result : {invoke_result}")
            return True, contentsMetaResult

        except Exception as e: 
            #trackback logging
            tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            mycontents_logger.error(f"Exception occurred: {e}, Args: {e.args}, Traceback: {tb_str}")

            error_ollamaModel :ContentsMetaResult = self.to_error_ollamaModel(invoke_result) 
            return False, error_ollamaModel


if __name__ =="__main__":
    pass 

