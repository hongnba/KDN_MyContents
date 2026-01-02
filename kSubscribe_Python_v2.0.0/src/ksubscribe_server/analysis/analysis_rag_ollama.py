from langchain_community.chat_models import ChatOllama

from openai import OpenAI
import traceback
from datetime import datetime, timezone
import logging 
from langchain_ollama import ChatOllama
import ksubscribe_share.config as CONF
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
from typing import Tuple, Dict

from ksubscribe_server.models.ollamaModel import OllamaModel
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsMeta, SentimentInfo
from ksubscribe_share.db.dbmodelV2.llmAnalysisVO import LLMAnalysisVO
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService

class AnalysisRagOllama:


    question = f"""
    다음 문장에서 기사를 추출하고 아래 형식에 맞춰 JSON 객체 구조로 정확히 일치시켜서 응답해줘. JSON 객체의 구조는 다음과 같아. {{로 시작해서 }}로 끝나야해, "를 빼먹지 말고 꼭 넣어줘
    {{
        "keyword": ["주요 키워드1", "주요 키워드2", "주요 키워드3"],
        "predkeywords":  사전정의 키워드 목록인 [pred_keywords_from_db] 단어 리스트에서 기사와 유사도가 높은 단어를 3개 추출하여 "{{"단어1": "단어1유사도점수", "단어2": "단어2유사도점수", "단어3": "단어3유사도점수" }}" 처럼 응답해,
        "short_summary": "한줄 기사 요약",
        "long_summary": "세줄 기사 요약",
        "sentiments": [
            {{
                "orgName": "관련된 기관의 이름 (예: [org_name_list_from_db] 중 일치하는 기관 이름 하나, 기관마다 별도의 항목으로 나열)",
                "positiveRatio": "기관에 대한 긍정적인 비율 (float형 숫자, % 없이)",
                "negativeRatio": "기관에 대한 부정적인 비율 (float형 숫자, % 없이)",
                "neutralRatio": "기관에 대한 중립적인 비율 (float형 숫자, % 없이)",
                "positiveReason": "긍정 비율 판단 근거 (문장 형식)",
                "negativeReason": "부정 비율 판단 근거 (문장 형식)",
                "positiveKeywords": ["긍정키워드1", "긍정키워드2", "긍정키워드3"],
                "negativeKeywords": ["부정키워드1", "부정키워드2", "부정키워드3"]
            }},
            {{
                "orgName": "또 다른 관련된 기관의 이름",
                "positiveRatio": "기관에 대한 긍정적인 비율 (float형 숫자, % 없이)",
                "negativeRatio": "기관에 대한 부정적인 비율 (float형 숫자, % 없이)",
                "neutralRatio": "기관에 대한 중립적인 비율 (float형 숫자, % 없이)",
                "positiveReason": "긍정 비율 판단 근거 (문장 형식)",
                "negativeReason": "부정 비율 판단 근거 (문장 형식)",
                "positiveKeywords": ["긍정키워드1", "긍정키워드2", "긍정키워드3"],
                "negativeKeywords": ["부정키워드1", "부정키워드2", "부정키워드3"]
            }}
        ]
    }}
    """

    question_summary = f"""
    다음 HTML에서 기사를 추출하고 아래 형식에 맞춰 JSON 객체로 응답해줘 (\n, \r\n, \t 제거). JSON 객체의 구조는 다음과 같아:
    {{
        "keyword": ["주요 키워드1", "주요 키워드2", "주요 키워드3"],
        "predkeywords":  사전정의 키워드 목록인 [pred_keywords_from_db] 중에서 기사와 유사도가 높은 키워드를 3개 분석하고 유사도 순으로 3개를, "{{"키워드1": "유사도점수", "키워드2": "유사도점수", "키워드3": "유사도점수"}}" 형태로 만들어줘,
        "short_summary": "한줄 기사 요약",
        "long_summary": "세줄 기사 요약"
    }}
    """

    def __init__(self):
        # 하드코딩된 기존 설정 (보관용 주석):
        # self.chat_ollama =  ChatOllama(model="EEVE-Korean-10.8B")  #/llama-3-Korean-Bllossom-8B-gguf-Q4_K_M:latest

        # 설정 파일의 값을 사용하도록 변경
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
    
    def nanoseconds_to_seconds(nanoseconds):
        # 나노초를 초로 변환
        return nanoseconds / 1_000_000_000    

        
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
        
        
    def to_ollamaModel(self, contentsId:str, invoke_result:BaseMessage) -> OllamaModel:
        
        ollamaModel = OllamaModel()
        content = None
        try:
            invoke_content = self.fix_json(invoke_result.content)
            content = json.loads(invoke_content)
            ollamaModel.contentsMeta = self.parse_content(content)
            #ollamaModel.contentsMeta = ContentsMeta.from_mongo(content)
        except Exception as e: 
            pass
        
        usage_metadata = invoke_result.usage_metadata
        response_metadata = invoke_result.response_metadata
        
        llmAnalysisVO = LLMAnalysisVO()        
        try:
            llmAnalysisVO.contents_id = contentsId
            llmAnalysisVO.analyze_type = "ollama"
            llmAnalysisVO.response_metadata_model = response_metadata["model"] if response_metadata["model"] is not None else ""
            llmAnalysisVO.response_metadata_createdDt = response_metadata["created_at"] if response_metadata["model"] is not None else None
            llmAnalysisVO.response_metadata_done = response_metadata["done"] if response_metadata["model"] is not None else False
            llmAnalysisVO.response_metadata_doneReason = response_metadata["done_reason"] if response_metadata["model"] is not None else ""
            llmAnalysisVO.response_metadata_totalDuration = response_metadata["total_duration"] if response_metadata["model"] is not None else 0
            llmAnalysisVO.response_metadata_loadDuration = response_metadata["load_duration"] if response_metadata["model"] is not None else 0
            llmAnalysisVO.response_metadata_promptEvalCount = response_metadata["prompt_eval_count"] if response_metadata["model"] is not None else 0
            llmAnalysisVO.response_metadata_promptEvalDuration = response_metadata["prompt_eval_duration"] if response_metadata["model"] is not None else 0
            llmAnalysisVO.response_metadata_evalCount = response_metadata["eval_count"] if response_metadata["model"] is not None else 0
            llmAnalysisVO.response_metadata_evalDuration = response_metadata["eval_duration"] if response_metadata["model"] is not None else 0
            llmAnalysisVO.usage_metadata_inputToken = usage_metadata["input_tokens"] if response_metadata["model"] is not None else 0
            llmAnalysisVO.usage_metadata_outputToken = usage_metadata["output_tokens"] if response_metadata["model"] is not None else 0
            llmAnalysisVO.usage_metadata_totalToken = usage_metadata["total_tokens"] if response_metadata["model"] is not None else 0
            llmAnalysisVO.regDt = datetime.now(timezone.utc)
        except Exception as e: 
            pass        
        ollamaModel.llmAnalysisVO = llmAnalysisVO
        
        
        if llmAnalysisVO.response_metadata_done:
            ollamaModel.metaSucYN = "Y"            
            ollamaModel.metaAnalyzeDt = llmAnalysisVO.response_metadata_createdDt
        else :
            ollamaModel.metaSucYN = "N" 
            ollamaModel.metaAnalyzeDt = None
        
        return ollamaModel


    def to_error_ollamaModel(self) -> OllamaModel:
        
        ollamaModel = OllamaModel()
        ollamaModel.contentsMeta = None
        ollamaModel.llmAnalysisVO = None
        ollamaModel.metaSucYN = "N" 
        ollamaModel.metaAnalyzeDt = datetime.now(timezone.utc)
      
                  
    def analysis(self, raw_data, pred_keyword_list, org_name_list, mycontents_logger:logging.Logger, contentsId:str) ->  Tuple[bool, OllamaModel]:

        try:
            
            new_question = self.question.replace("pred_keywords_from_db", pred_keyword_list).replace("org_name_list_from_db", org_name_list)
            #new_question = self.question_summary.replace("pred_keywords_from_db", pred_keyword_list)
            
            messages=[
                {"role": "system", "content": new_question},
                {"role": "user", "content": f"{raw_data}"},
            ]
            llm_question = self.messages_to_prompt(messages)
                            
            invoke_result = self.chat_ollama.invoke(llm_question)            
            ollamaModel :OllamaModel = self.to_ollamaModel(contentsId, invoke_result) 
            mycontents_logger.debug(f"소요시간 : {ollamaModel.llmAnalysisVO.response_metadata_evalDuration }, predict_result : {invoke_result}")
            return True, ollamaModel

        except Exception as e: 
            #trackback logging
            tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            mycontents_logger.error(f"Exception occurred: {e}, Args: {e.args}, Traceback: {tb_str}")

            error_ollamaModel :OllamaModel = self.to_error_ollamaModel(invoke_result) 
            return False, error_ollamaModel



if __name__ == "__main__":
    pass

