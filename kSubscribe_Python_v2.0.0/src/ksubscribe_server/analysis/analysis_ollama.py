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
from ksubscribe_server.models.ollamaModel import OllamaModel
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsMeta, SentimentInfo
from ksubscribe_share.db.dbmodelV2.llmAnalysisVO import LLMAnalysisVO
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService

from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.predefineKeywordService import PredefineKeywordService
from ksubscribe_share.db.service.contentsService import ContentsService
 
        


class AnalysisOllama:
  #여러기관이 나왔을 경우에는 리스트로 반환해",
    
    # question = f"""
    # 다음 HTML에서 기사를 추출하고 아래 형식에 맞춰 JSON 객체로 응답해줘. JSON 객체의 구조는 다음과 같아
    # {{
    #     "keyword" : [주요 키워드1, 주요 키워드2, 주요 키워드3],
    #     "predkeywords":  [pred_keywords_from_db] 중 가장 유사도가 높은 키워드 순으로 3개만, "{{"키워드1": "유사도점수", "키워드2": "유사도점수", "키워드3": "유사도점수"}}" 형태로 만들어줘",
    #     "short_summary" : "한줄 기사 요약",
    #     "long_summary" : "세줄 기사 요약",
    #     "sentiment" :  {{
    #         "organization" : "위 기사가 [org_name_list_from_db] 기관 중 관련된 기사이면 가장 유사도가 높은 기관 순으로 기관명을 알려줘. 리스트에 있는 기관명과 동일한 것만 찾아",
    #         "positiveRatio": "기사 내용이 기관에 대한 긍정적인 비율 (%), 주석 달지말고 비율만 알려줘. 기관 순서에 맞게 리스트 형식으로 반환해줘, %없이 출력해 ",
    #         "negativeRatio": "기사 내용이 기관에 대한 부정적인 비율 (%), 주석 달지말고 비율만 알려줘. 기관 순서에 맞게 리스트 형식으로 반환해줘, %없이 출력해 ",
    #         "neutralRatio": "기사 내용이 기관에 대한 중립적인 비율 (%), 주석 달지말고 비율만 알려줘. 기관 순서에 맞게 리스트 형식으로 반환해줘, %없이 출력해 ",
    #         "reason": "긍정과 부정 비율 판단 근거. organization 개수대로 순서에 맞게 리스트 형식으로 반환해줘",
    #     }}
    # }} 
    # """       

    question = f""" 
        "contents" = [contents]
        위의 HTML에서 기사를 추출하고 아래 형식에 맞춰 JSON 객체로 응답해줘. JSON 객체의 구조는 다음과 같아
        답변은 주석없이 json데이터만 줘. "contents"는 다시 반환할 필요 없어.
    {{
        "keyword" : [주요 키워드1, 주요 키워드2, 주요 키워드3],
        "predkeywords":  [pred_keywords_from_db] 중 가장 유사도가 높은 키워드 순으로 3개만, "{{"키워드1": "유사도점수", "키워드2": "유사도점수", "키워드3": "유사도점수"}}" 형태로 만들어줘",
        "short_summary" : "한줄 기사 요약",
        "long_summary" : "세줄 기사 요약",
        "sentiments" :  {{
            "organization" : "위 기사가 [org_name_list_from_db] 기관 중 관련된 기사이면 가장 유사도가 높은 기관 순으로 기관명을 알려줘. 리스트에 있는 기관명과 동일한 것만 찾아. 리스트 형식으로 반환해줘",
            "positiveRatio": "기사 내용이 기관에 대한 긍정적인 비율 (%), 주석 달지말고 비율만 알려줘. organization의 개수와 동일한 크기를 가진 리스트 형식으로 반환해줘, %없이 출력해 ",
            "negativeRatio": "기사 내용이 기관에 대한 부정적인 비율 (%), 주석 달지말고 비율만 알려줘.  organization의 개수와 동일한 크기를 가진 리스트 형식으로 반환해줘, %없이 출력해 ",
            "neutralRatio": "기사 내용이 기관에 대한 중립적인 비율 (%), 주석 달지말고 비율만 알려줘.  organization의 개수와 동일한 크기를 가진 리스트 형식으로 반환해줘, %없이 출력해 ",
            "reason": "긍정과 부정 비율 판단 근거(문장 형식).  organization의 개수와 동일한 크기를 가진 리스트 형식으로 반환해줘",
            "positiveReason": "긍정 비율 판단 근거 (문장 형식)",
            "negativeReason": "부정 비율 판단 근거 (문장 형식)",
            "positiveKeywords": ["긍정키워드1", "긍정키워드2", "긍정키워드3"],
            "negativeKeywords": ["부정키워드1", "부정키워드2", "부정키워드3"]
        }}
    }} 
    
    """
    answer_template = f"""
    {{
        "keyword" : [주요 키워드1, 주요 키워드2, 주요 키워드3],
        "predkeywords":  [pred_keywords_from_db] 중 가장 유사도가 높은 키워드 순으로 3개만, "{{"키워드1": "유사도점수", "키워드2": "유사도점수", "키워드3": "유사도점수"}}" 형태로 만들어줘",
        "short_summary" : "한줄 기사 요약",
        "long_summary" : "세줄 기사 요약",
        "sentiment" :  {{
            "organization" : "위 기사가 [org_name_list_from_db] 기관 중 관련된 기사이면 가장 유사도가 높은 기관 순으로 기관명을 알려줘. 리스트에 있는 기관명과 동일한 것만 찾아. 리스트 형식으로 반환해줘",
            "positiveRatio": "기사 내용이 기관에 대한 긍정적인 비율 (%), 주석 달지말고 비율만 알려줘. organization의 개수와 동일한 크기를 가진 리스트 형식으로 반환해줘, %없이 출력해 ",
            "negativeRatio": "기사 내용이 기관에 대한 부정적인 비율 (%), 주석 달지말고 비율만 알려줘.  organization의 개수와 동일한 크기를 가진 리스트 형식으로 반환해줘, %없이 출력해 ",
            "neutralRatio": "기사 내용이 기관에 대한 중립적인 비율 (%), 주석 달지말고 비율만 알려줘.  organization의 개수와 동일한 크기를 가진 리스트 형식으로 반환해줘, %없이 출력해 ",
            "reason": "긍정과 부정 비율 판단 근거(문장 형식).  organization의 개수와 동일한 크기를 가진 리스트 형식으로 반환해줘",
            "positiveReason": "긍정 비율 판단 근거 (문장 형식)",
            "negativeReason": "부정 비율 판단 근거 (문장 형식)",
            "positiveKeywords": ["긍정키워드1", "긍정키워드2", "긍정키워드3"],
            "negativeKeywords": ["부정키워드1", "부정키워드2", "부정키워드3"]
        }}
    }} """
    question_new = f"""
    다음 HTML에서 기사를 추출하고 아래 형식에 맞춰 JSON 객체로 응답해줘. JSON 객체의 구조는 다음과 같아
    {{
        "keyword" : [주요 키워드1, 주요 키워드2, 주요 키워드3],
        "predkeywords":  [pred_keywords_from_db] 중 가장 유사도가 높은 키워드 순으로 3개만, "{{"키워드1": "유사도점수", "키워드2": "유사도점수", "키워드3": "유사도점수"}}" 형태로 만들어줘",
        "short_summary" : "한줄 기사 요약",
        "long_summary" : "세줄 기사 요약",
        "sentiment" :  {{
            "organization" : "위 기사가 [org_name_list_from_db] 기관 중 관련된 기사이면 가장 유사도가 높은 기관 순으로 기관명을 알려줘. 리스트에 있는 기관명과 동일한 것만 찾아. 리스트 형식으로 반환해줘",
            "positiveRatio": "기사 내용이 기관에 대한 긍정적인 비율 (%), 주석 달지말고 비율만 알려줘. organization의 개수와 동일한 크기를 가진 리스트 형식으로 반환해줘, %없이 출력해 ",
            "negativeRatio": "기사 내용이 기관에 대한 부정적인 비율 (%), 주석 달지말고 비율만 알려줘.  organization의 개수와 동일한 크기를 가진 리스트 형식으로 반환해줘, %없이 출력해 ",
            "neutralRatio": "기사 내용이 기관에 대한 중립적인 비율 (%), 주석 달지말고 비율만 알려줘.  organization의 개수와 동일한 크기를 가진 리스트 형식으로 반환해줘, %없이 출력해 ",
            "reason": "긍정과 부정 비율 판단 근거.",
            "positiveReason": "긍정 비율 판단 근거 (문장 형식),",
            "negativeReason": "부정 비율 판단 근거 (문장 형식)",
            "positiveKeywords": ["긍정키워드1", "긍정키워드2", "긍정키워드3"],
            "negativeKeywords": ["부정키워드1", "부정키워드2", "부정키워드3"]
        }}
    }} 
    """    

    question_summary = f"""
    contents : [contents]
    위의 HTML에서 기사를 추출하고 아래 형식에 맞춰 JSON 객체로 응답해줘 (\n, \r\n, \t 제거). JSON 객체의 구조는 다음과 같아:
    {{
        "keyword": ["주요 키워드1", "주요 키워드2", "주요 키워드3"],
        "predkeywords":  사전정의 키워드 목록인 [pred_keywords_from_db] 중에서 기사와 유사도가 높은 키워드를 3개 분석하고 유사도 순으로 3개를, "{{"키워드1": "유사도점수", "키워드2": "유사도점수", "키워드3": "유사도점수"}}" 형태로 만들어줘,
        "short_summary": "한줄 기사 요약",
        "long_summary": "세줄 기사 요약"
    }}
    """

    question_sentiment = f"""
    contents : [contents]
    위의 HTML에서 기사를 추출하고 아래 형식에 맞춰 JSON 객체로 응답해줘. JSON 객체의 구조는 다음과 같아
    {{
        "sentiments" :  [{{
            "organization" : "위 기사가 [org_name_list_from_db] 기관 중 관련된 기사이면 가장 유사도가 높은 기관 순으로 기관명을 알려줘. 리스트에 있는 기관명과 동일한 것만 찾아.",
            "positiveRatio": "기사 내용이 기관에 대한 긍정적인 비율 (%), 주석 달지말고 비율만 알려줘. %없이 출력해 ",
            "negativeRatio": "기사 내용이 기관에 대한 부정적인 비율 (%), 주석 달지말고 비율만 알려줘. %없이 출력해 ",
            "neutralRatio": "기사 내용이 기관에 대한 중립적인 비율 (%), 주석 달지말고 비율만 알려줘.   %없이 출력해 ",
            "reason": "긍정과 부정 비율 판단 근거.",
            "positiveReason": "긍정 비율 판단 근거 (문장 형식),",
            "negativeReason": "부정 비율 판단 근거 (문장 형식)",
            "positiveKeywords": ["긍정키워드1", "긍정키워드2", "긍정키워드3"],
            "negativeKeywords": ["부정키워드1", "부정키워드2", "부정키워드3"]
        }}]
    }} 
    """    
    def __init__(self):
        self.chat_ollama =  ChatOllama(model="EEVE-Korean-10.8B",base_url="http://10.99.2.71:11434") 
         #/llama-3-Korean-Bllossom-8B-gguf-Q4_K_M:latest

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
        
    def parse_content_V3(self,result_analysis):
        contentsMeta = ContentsMeta()

        try:
            # keyword = result_analysis["keyword"]
            # if keyword is not None and isinstance(keyword, list):
            #     contentsMeta.keywords = keyword   
            #     print(contentsMeta.keywords)             
                
            # predkeywords = result_analysis["predkeywords"]
            # if predkeywords is not None and isinstance(predkeywords, Dict):
            #     contentsMeta.predKeywords = predkeywords                
            #     print(contentsMeta.predKeywords )             
            # short_summary = result_analysis["short_summary"]
            # if short_summary is not None and isinstance(short_summary, str):
            #     contentsMeta.shortSummary = short_summary                
            #     print(contentsMeta.shortSummary )             
            # long_summary = result_analysis["long_summary"]
            # if long_summary is not None and isinstance(long_summary, str):
            #     contentsMeta.longSummary = long_summary                      
            #     print(contentsMeta.longSummary )    
                        
            sentiments = result_analysis["sentiments"]
            contentsMeta.sentiments = []        
            
            if sentiments is not None and isinstance(sentiments, list):
                #organization = sentiments["organization"]
                for sentiment in sentiments:
                    sentiment_info = SentimentInfo()
                    sentiment_info.orgName= sentiment["organization"]

                    sentiment_info.reason= sentiment["Reason"]
                    sentiment_info.positiveRatio= sentiment["positiveRatio"]
                    sentiment_info.negativeRatio= sentiment["negativeRatio"]
                    sentiment_info.neutralRatio= sentiment["neutralRatio"]
                    sentiment_info.positiveKeywords = sentiment["positiveKeywords"]
                    sentiment_info.negativeKeywords = sentiment["negativeKeywords"]

                    sentiment_info.positiveReason=sentiment["positiveReason"]
                    sentiment_info.negativeReason =sentiment["negativeReason"]   
                    contentsMeta.sentiments.append(sentiment_info) 
            print(contentsMeta)
                      
        except Exception as e:
            # TODO : logger 추가
            pass
        
        return contentsMeta
    
    def parse_content_V2(self,result_analysis):
        contentsMeta = ContentsMeta()

        try:
            keyword = result_analysis["keyword"]
            if keyword is not None and isinstance(keyword, list):
                contentsMeta.keywords = keyword   
                print(contentsMeta.keywords)             
                
            predkeywords = result_analysis["predkeywords"]
            if predkeywords is not None and isinstance(predkeywords, Dict):
                contentsMeta.predKeywords = predkeywords                
                print(contentsMeta.predKeywords )             
            short_summary = result_analysis["short_summary"]
            if short_summary is not None and isinstance(short_summary, str):
                contentsMeta.shortSummary = short_summary                
                print(contentsMeta.shortSummary )             
            long_summary = result_analysis["long_summary"]
            if long_summary is not None and isinstance(long_summary, str):
                contentsMeta.longSummary = long_summary                      
                print(contentsMeta.longSummary )    
                        
            sentiments = result_analysis["sentiments"]
            contentsMeta.sentiments = []        
            
            if sentiments is not None and isinstance(sentiments, dict):
                organization = sentiments["organization"]
                if organization is not None and isinstance(organization, list):
                    for index, item in enumerate(organization):
                        sentimentInfo = SentimentInfo()                  
                        org = ContentsOrgService().findOrgbyName(sentiments["organization"][index])  
                        sentimentInfo.orgName = sentiments["organization"][index]
                        if org:
                            sentimentInfo.orgId = org.orgId
                        else:
                            sentimentInfo.orgId = "unknow organization"
                        sentimentInfo.positiveRatio =sentiments["positiveRatio"][index]
                        sentimentInfo.negativeRatio =sentiments["negativeRatio"][index]
                        sentimentInfo.neutralRatio  =sentiments["neutralRatio"][index]
                        # 프롬프트 정리 필요 : list 개수안맞음 
                        #sentimentInfo.positiveReason=sentiments["positiveReason"][index]
                        #sentimentInfo.negativeReason =sentiments["negativeReason"][index]
                        sentimentInfo.reason = sentiments["reason"][index]
                        # if sentiments["positiveKeywords"][index]:
                        #     sentimentInfo.positiveKeywords = sentiments["positiveKeywords"][index]
                        # if sentiments["negativeKeywords"][index]:
                        #     sentimentInfo.positiveKeywords = sentiments["negativeKeywords"][index]     
                        contentsMeta.sentiments.append(sentimentInfo) 
            print(contentsMeta)
                      
        except Exception as e:
            # TODO : logger 추가
            pass 
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
        return ollamaModel

        
    def to_ollamaModel_V2(self,ollama_result):
        ollamaModel = OllamaModel()
        try:
            result_analysis_resp = ollama_result.response.replace("`","")
            result_analysis_resp = result_analysis_resp.replace("json","")
            result_analysis_resp = result_analysis_resp.replace("\n","")
            result_analysis_resp = json.loads(result_analysis_resp)
            print(result_analysis_resp)
            # TODO : V2로 교체 할것
            contentsMeta = self.parse_content_V3(result_analysis_resp)

            ollamaModel.contentsMeta = contentsMeta
        except Exception as e :
            # json 으로 던져도 안오는 경우 있음 .
            return False , str(e)

        llmAnalysisVO = LLMAnalysisVO()        
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
            llmAnalysisVO.regDt = datetime.now(timezone.utc)
        except Exception as e: 
            pass        
        ollamaModel.llmAnalysisVO = llmAnalysisVO
        
        
        if ollama_result.done:
            ollamaModel.metaSucYN = "Y"            
            ollamaModel.metaAnalyzeDt = llmAnalysisVO.response_metadata_createdDt
        else :
            ollamaModel.metaSucYN = "N" 
            ollamaModel.metaAnalyzeDt = None
        
        return True,ollamaModel

    def to_ollamaModel_V3(self,sentiments_result,summary_result):

        ollama_model = OllamaModel()
        # 1. parse sentiment 
        sentiment_resp = sentiments_result.response
        sentiment_resp = sentiment_resp.replace("`","")
        sentiment_resp = sentiment_resp.replace("json","")
        sentiment_resp = sentiment_resp.replace("\n","")
        sentiment_resp = json.loads(sentiment_resp)
        ollama_model = self.parse_sentiments(sentiment_resp,ollama_model)
        # 2, parse summary 
        
        summary_resp = summary_result.response
        summary_resp = summary_resp.replace("`","")
        summary_resp = summary_resp.replace("json","")
        summary_resp = summary_resp.replace("\n","")
        summary_resp = json.loads(summary_resp)
        ollama_model = self.parse_summary(summary_resp,ollama_model)
        return ollama_model
    def parse_sentiments(self,sentiments,ollama_model:OllamaModel):
        contents_meta = ContentsMeta()
        contents_meta.sentiments = []#SentimentInfo()
        if sentiments["sentiments"]:
            sentiments= sentiments["sentiments"]
            if isinstance(sentiments,list):
                for sentiment in sentiments:
                    sentiment_info = SentimentInfo()
                    try:
                        if sentiment["organization"] is not None:
                            sentiment_info.orgName = sentiment["organization"] 
                        if sentiment["positiveRatio"] is not None:
                            sentiment_info.positiveRatio = sentiment["positiveRatio"]
                        if sentiment["negativeRatio"] is not None:
                            sentiment_info.negativeRatio = sentiment["negativeRatio"]
                        if sentiment["neutralRatio"] is not None:
                            sentiment_info.neutralRatio = sentiment["neutralRatio"]
                        if sentiment["positiveReason"] is not None:
                            sentiment_info.positiveReason = sentiment["positiveReason"]
                        if sentiment["negativeReason"] is not None:
                            sentiment_info.negativeReason = sentiment["negativeReason"]
                        if sentiment["positiveKeywords"] is not None:
                            sentiment_info.positiveKeywords = sentiment["positiveKeywords"]
                        if sentiment["negativeKeywords"] is not None:
                            sentiment_info.negativeKeywords = sentiment["negativeKeywords"]
                        if sentiment["reason"] is not None:
                            sentiment_info.reason = sentiment["reason"]
                                
                    except Exception as e :
                        print(f"(def parse sentiment)파싱 실패 !!!!!!!{e}")
                    contents_meta.sentiments.append(sentiment_info)
        ollama_model.contentsMeta =contents_meta

        return ollama_model
     
    def parse_summary(self,summary,ollama_model:OllamaModel):
        if ollama_model.contentsMeta is None:
            ollama_model.contentsMeta = ContentsMeta()
        try:
            if summary["keyword"] is not None:
                if isinstance(summary["keyword"],list):
                    ollama_model.contentsMeta.keywords = summary["keyword"]
            if summary["predkeywords"] is not None:
                if isinstance(summary["predkeywords"],dict):
                    ollama_model.contentsMeta.predKeywords = summary["predkeywords"] 

            if summary["short_summary"] is not None:
                if isinstance(summary["short_summary"],str):
                    ollama_model.contentsMeta.shortSummary = summary["short_summary"]
            if summary["long_summary"] is not None:
                if isinstance(summary["short_summary"],str):
                    ollama_model.contentsMeta.longSummary = summary["long_summary"]
        except Exception as e :
                print(f"(def parse summary)파싱 실패 !!!!!!!{e}")
        return ollama_model
    def analysis(self, content, pred_keyword_list, org_name_list, mycontents_logger:logging.Logger):#, contentsId:str
        try:
            
            # 
            new_question = self.question.replace("pred_keywords_from_db", pred_keyword_list).replace("org_name_list_from_db", org_name_list)
            new_question = new_question.replace("[contents]",content)
 
            result_analysis = self.chat_ollama._client.generate( 
                model ="hf.co/MLP-KTLim/llama-3-Korean-Bllossom-8B-gguf-Q4_K_M:latest",
                prompt=new_question ,
                format="json")
            #template=self.answer_template
            
            ollama_model_result = self.to_ollamaModel_V2(result_analysis) 
 
            mycontents_logger.debug(f"소요시간 : {result_analysis.total_duration/1000000000} 초 소요")
            return True, ollama_model_result

        except Exception as e: 
            #trackback logging
            tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            mycontents_logger.error(f"Exception occurred: {e}, Args: {e.args}, Traceback: {tb_str}")

            error_ollamaModel :OllamaModel = self.to_error_ollamaModel(ollama_model_result) 
            return False, error_ollamaModel

    # local ollama
    def analysis_old(self, raw_data, pred_keyword_list, org_name_list, mycontents_logger:logging.Logger, contentsId:str) ->  Tuple[bool, OllamaModel]:

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
            ollamaModel :OllamaModel = self.to_ollamaModel(contentsId, invoke_result) 
            mycontents_logger.debug(f"소요시간 : {ollamaModel.llmAnalysisVO.response_metadata_evalDuration }, predict_result : {invoke_result}")
            return True, ollamaModel

        except Exception as e: 
            #trackback logging
            tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            mycontents_logger.error(f"Exception occurred: {e}, Args: {e.args}, Traceback: {tb_str}")

            error_ollamaModel :OllamaModel = self.to_error_ollamaModel(invoke_result) 
            return False, error_ollamaModel

 


 

def main():
    pass 

if __name__ =="__main__":
    main() 
    pass 

