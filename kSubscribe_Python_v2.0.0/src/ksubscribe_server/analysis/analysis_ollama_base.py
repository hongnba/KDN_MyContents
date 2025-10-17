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
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService

from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.predefineKeywordService import PredefineKeywordService
from ksubscribe_share.db.service.contentsService import ContentsService
 
        


class AnalysisOllamaBase:

    def nanoseconds_to_seconds(self, nanoseconds):
        # 나노초를 초로 변환
        return nanoseconds / 1_000_000_000    
    
    
    question = f""" 
        "contents" = [contents]
        위의 HTML에서 기사를 추출하고 아래 형식에 맞춰 JSON 객체로 응답해줘. JSON 객체의 구조는 다음과 같아
        답변은 주석없이 json데이터만 줘. "contents"는 다시 반환할 필요 없어.
    {{
        "keyword" : [주요 키워드1, 주요 키워드2, 주요 키워드3],
        "predkeywords":  [pred_keywords_from_db] 중 가장 유사도가 높은 키워드 순으로 3개만, "{{"키워드1": "유사도점수", "키워드2": "유사도점수", "키워드3": "유사도점수"}}" 형태로 만들어줘",
        "short_summary" : "한줄 기사 요약",
        "long_summary" : "500자로 기사 요약, long_summary는 자세한 정보까지 요약에 포함되어야 해.",
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
        "long_summary" : "500자로 기사 요약, long_summary는 자세한 정보까지 요약에 포함되어야 해.",
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
        "long_summary" : "500자로 기사 요약, long_summary는 자세한 정보까지 요약에 포함되어야 해.",
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

    # 추가 "long_summary는 자세한 정보까지 요약에 포함되어야 해." 20250218
    # 2025.03.06 : prompt 수정, 임형준, 500자로 기사 요약=> 5줄 이상, react에서 keyword까지 출력하도록 전달(to김주아)
    # 2025.03.13 : prompt 수정, 삭제 함. "predkeywords":  사전정의 키워드 목록인 [pred_keywords_from_db] 중에서 기사와 유사도가 높은 키워드를 3개 분석하고 유사도 순으로 3개를, "{{"키워드1": "유사도점수", "키워드2": "유사도점수", "키워드3": "유사도점수"}}" 형태로 만들어줘,        
    # question_summary = f"""
    # contents : [contents]
    # 위의 기사를 분석하여 아래 형식에 맞춰 JSON 객체로 응답해줘 (\n, \r\n, \t 제거). JSON 객체의 구조는 다음과 같아:
    # keyword에는 핵심키워드를 추출해서 넣어줘. 
    # {{
    #     "keyword": ["주요 키워드1", "주요 키워드2", "주요 키워드3"],
    #     "short_summary": "한줄 기사 요약",
    #     "long_summary": "5줄 이상으로 기사 요약, long_summary는 자세한 정보까지 요약에 포함되어야 해."
    # }}
    # """ 
    
    # 20251013 리자: 프롬프트 수정: 기관 입장에서 ..? 
    question_summary = f"""
    contents : [contents]
    organization : [organization]
    위의 기사를 분석하여 아래 형식에 맞춰 JSON 객체로 응답해줘 (\n, \r\n, \t 제거). JSON 객체의 구조는 다음과 같아:
    {{
        "short_summary": "한줄 기사 요약",
        "long_summary": "5줄 이상으로 기사 요약, long_summary는 자세한 정보까지 요약에 포함되어야 해. organization을 중심으로 요약해줘."
    }}
    """ 
    ###"short_summary": "한줄 기사 요약",
        ##"long_summary": "5줄 이상으로 기사 요약, long_summary는 자세한 정보까지 요약에 포함되어야 해."
       # "category_reason": 반환한 category별로 이유를 설명해줘 dictionary 형태로.
    
    # 추가
    # ~Ratio : 0~1사이의 float 형태로 출력해줘 --> 2025.03.03 최미화 질문 : 왜 넣은거죠? 
    # 2025.03.03 : Prompt 수정, 최미화, 기관 이름이 명확이 추출되도록 수정함 
    # 2025.03.10 : Prompt 수정, 최미화, 긍정키워드, 부정키워드 추출 방법 기술 추가함. 
    question_sentiment = f"""
    contents : [contents]
    위 기사를 분석하여 아래 JSON 객체 구조에 정확히 맞춰서 응답해 줘. organization에는 하나의 기관만 넣고  하나의 기관에 대해서 positiveRatio~negativeKeywords 정보를 만들어줘.
    여러 기관과 관련이 있으면 organization에 기관을 하나 추가하고 그에 맞는 positiveRatio~negativeKeywords 정보를 추가해줘. 
    기사에 기관명, 기관명 약자 등이 언급된 경우에만 관련 기관으로 판단해줘. 해당 기관이 관련있다는 근거는 orginizationReason에 추가해줘.
    {{
        "sentiments" :  [{{
            "organization" : "위 기사가 [org_name_list_from_db] 기관 중 관련된 기사이면 가장 유사도가 높은 기관 순으로 기관명을 알려줘. 리스트에 있는 기관명과 동일한 것만 찾아.",
            "positiveRatio": "기사 내용이 기관에 대한 긍정적인 비율 (%), 주석 달지말고 비율만 알려줘. %없이 0~100사이의 float 형태로 출력해 ",
            "negativeRatio": "기사 내용이 기관에 대한 부정적인 비율 (%), 주석 달지말고 비율만 알려줘. %없이 0~100사이의 float 형태로 출력해 ",
            "neutralRatio": "기사 내용이 기관에 대한 중립적인 비율 (%), 주석 달지말고 비율만 알려줘. %없이 0~100사이의 float 형태로 출력해 ",
            "reason": "긍정과 부정 비율 판단 근거.",
            "positiveReason": "긍정 비율 판단 근거 (문장 형식),",
            "negativeReason": "부정 비율 판단 근거 (문장 형식)",
            "positiveKeywords": ["긍정키워드1", "긍정키워드2", "긍정키워드3"]  전체 기사에서 의미를 파악해서 문맥이 있는 긍정키워드를 추출해줘. 문맥있는 표현이면 좋겠어. ,
            "negativeKeywords": ["부정키워드1", "부정키워드2", "부정키워드3"]  전체 기사에서 의미를 파악해서 문맥이 있는 부정키워드를 추출해줘. 문맥있는 표현이면 좋겠어. ,
    		"orginizationReason" : "해당 기관이 관련있다는 근거"            
        }}]
    }} 
    """    
    
    # 20251013 리자: 프롬프트 3)분리
    question_sentiment_ratio = f"""
    기사 : [contents]
    기관 : [organization] (이 기관은 [synonyms]로도 불립니다.)
    위 기사에서 해당 기관 또는 그 별칭([synonyms])이 언급된 부분을 중심으로 감성 분석을 수행해 줘.
    기관에 대한 언급 중 긍정 / 부정 / 중립의 비율을 추정해서 아래 JSON 형식으로만 답변해.

        {{
            "positiveRatio": "기관 언급 중 긍정적 내용의 비율 (0~100, float, % 기호 없이)",
            "neutralRatio": "기관 언급 중 중립적 내용의 비율 (0~100, float, % 기호 없이)",
            "negativeRatio": "기관 언급 중 부정적 내용의 비율 (0~100, float, % 기호 없이)"
        }}

        세 비율의 합은 100이 되어야 해. 주석이나 설명은 넣지 마.
    """
    
    # question_negative_ratio = f"""
    # contents : [contents]
    # organization : [organization]
   
    
    # """
    
    # question_neutral_ratio = f"""
    # contents : [contents]
    # organization : [organization]
   
    
    # """
    
    #all three reasons using predictions as input;
    # question_sentiment_ratio => question_reason
    
    sentiment_reason = f"""
    기사 : [contents]
    기관 : [organization] (이 기관은 [synonyms]로도 불립니다.)
    
    해당 기관을 대상으로 기사를 분석된 감성 비율은 다음과 같아:
        - 긍정: [positiveRatio]
        - 부정: [negativeRatio]

        이 비율을 판단한 이유와 주요 키워드를 작성해줘.
        출력은 아래 JSON 형식으로 해.

        {{
            "reason": "긍정과 부정 비율을 종합적으로 판단한 근거 (한 문단)",
            "positiveReason": "긍정 비율 판단 근거 (문장 형식)",
            "negativeReason": "부정 비율 판단 근거 (문장 형식)",
        
        }}
    
    """
    
    sentiment_keywords = f"""
    기사 : [contents]
    기관 : [organization] (이 기관은 [synonyms]로도 불립니다.)
    
    이 기사는 여러 주제를 다룰 수 있지만, 
        **오직 해당 기관([organization])의 이미지, 평판, 또는 대중 인식에 영향을 미치는 내용만** 분석해 줘.

        기관과 직접적으로 관련된 **긍정적인 요인**과 **부정적인 요인**을 찾아 아래 JSON 형식으로 정리해 줘.
        단순한 단어나 기사 전반의 키워드가 아니라, 
        기관의 평판(이미지)에 영향을 주는 문맥 있는 표현을 뽑아야 해. 
        (예: "기술 혁신", "성과 향상", "비리 의혹", "경영 악화" 등)

        {{
            "positiveKeywords": ["긍정 키워드1", "긍정 키워드2", "긍정 키워드3"],
            "negativeKeywords": ["부정 키워드1", "부정 키워드2", "부정 키워드3"]
        }}

        출력 시:
        - JSON만 출력해. 
        - 주석, 설명, 문장형 해석은 절대 넣지 마.

    """
    
    
    

    # question_summary 이전에 db_keyword_list와 비교하여 검증 20250429 mcst
    question_verify = f"""
[Step 1] 다음 기사(contents)와 db_keyword_list를 제공합니다.
- contents: [contents]
- db_keyword_list: [pred_keywords_from_db]

[Step 2] 아래 요구사항에 따라 JSON 객체로만 답변해 주세요. 출력 시 (\n, \r\n, \t 등) 특수문자는 모두 제거합니다.

JSON 형식:
{{
    "ai_keyword": 기사(contents)에서 주요 이슈나 주제를 추출하여 핵심 키워드를 리스트로 작성합니다. 문맥을 반영한 표현을 사용하세요.
    "db_keyword_list": 제공한 db_keyword_list를 그대로 넣습니다.
    "related": ai_keyword와 db_keyword_list를 비교하여, 1개 이상 의미적으로 관련이 있으면 true, 전혀 관련이 없으면 false로 설정하세요.
    "reason": related가 true일 경우, db_keyword_list 안에서 관련된 최대 10개의 키워드를 선택하여 리스트로 작성하세요.
}}

[특별한 규칙]
- reason은 반드시 db_keyword_list 안에서만 선택해야 합니다. (ai_keyword에서 추출하면 절대 안 됩니다)
- 관련된 db_keyword_list 항목이 하나도 없으면, related는 반드시 false로 설정하세요.
- 절대 ai_keyword 항목에서 reason을 뽑지 마세요. db_keyword_list만 사용하세요.

[최종 조건]
- 출력은 반드시 위 JSON 구조를 정확히 따라야 합니다.
- 설명이나 추가 문장 없이 JSON만 출력하세요.
"""
    