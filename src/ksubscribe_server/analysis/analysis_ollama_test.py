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
 
        


class AnalysisOllamaTest:


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

    def pred_keyword_list(self):
        keyword = ["AI", "플랫폼", "데이터", "에너지", "전력"]
        keyword_str = ",".join(keyword)
        return keyword_str
    
    def org_name_list(self):
        org = ["한전KDN", "산업통상자원부", "한국전력공사"]
        org_str = ",".join(org)
        return org_str


    def __init__(self):
        #self.chat_ollama =  ChatOllama(model="eeve-korean",base_url="http://10.100.12.67:11434") 
        self.chat_ollama =  ChatOllama(model="hf.co/MLP-KTLim/llama-3-Korean-Bllossom-8B-gguf-Q4_K_M:latest",base_url="http://192.168.1.191:11434") 
         #/llama-3-Korean-Bllossom-8B-gguf-Q4_K_M:latest

    def analysis(self):#, contentsId:str
        try:
            
            pred_keyword_list = self.pred_keyword_list()
            org_name_list = self.org_name_list()
            isSuccess, content = self.test_raw()
            new_question = self.question.replace("pred_keywords_from_db", pred_keyword_list)
            new_question = new_question.replace("org_name_list_from_db", org_name_list)
            new_question = new_question.replace("[contents]",content)
 
            ollama_result = self.chat_ollama._client.generate( 
                model ="hf.co/MLP-KTLim/llama-3-Korean-Bllossom-8B-gguf-Q4_K_M:latest",
                #model ="eeve-korean:latest",
                prompt=new_question ,
                format="json")
            
            print(f"1 : {ollama_result}")

            result_analysis_resp = ollama_result.response.replace("`","")
            result_analysis_resp = result_analysis_resp.replace("json","")
            result_analysis_resp = result_analysis_resp.replace("\n","")
            result_analysis_resp = json.loads(result_analysis_resp)

            print(f"2 : {result_analysis_resp}")

            print(f"소요시간 : {ollama_result.total_duration/1000000000} 초 소요")

        except Exception as e: 
            #trackback logging
            tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            print(f"Exception occurred: {e}, Args: {e.args}, Traceback: {tb_str}")


if __name__ =="__main__":
    analysisOllamaTest = AnalysisOllamaTest()
    analysisOllamaTest.analysis()
    pass 

