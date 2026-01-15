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
    
    # ==================================================================================
    # [Active Prompts] 실제 서비스에서 사용 중인 프롬프트 정의 : 20251217 유헌수 프롬프트 수정
    # ==================================================================================


    # 1. [검증] 기사와 키워드 연관성 검증
    question_verify = f"""
    Reasoning: high
    # Valid channels: analysis, final

    너는 뉴스 기사와 사전 정의된 키워드 간의 연관성을 검증하는 '데이터 매칭 전문가'다.
    아래 [기사]의 핵심 주제를 파악하고, 제공된 [DB 키워드 리스트]와 매칭되는 항목이 있는지 검증해라.

    ### [검증 가이드라인]
    1. **주제 파악**: 기사 내용을 분석하여 핵심 이슈를 나타내는 'AI 키워드'를 먼저 추출해라.
    2. **매칭 확인**: 추출한 'AI 키워드'와 [DB 키워드 리스트]를 비교하여, 의미적으로 연결되는 항목이 있는지 확인해라.
    3. **엄격한 선택 규칙**:
       - `reason` 필드에는 **반드시 [DB 키워드 리스트]에 포함된 단어만** 기재해야 한다.
       - 기사 본문에 있는 단어라도 [DB 키워드 리스트]에 없다면 `reason`에 넣지 마라.
    4. **결과 판정**:
       - 연관된 키워드가 1개 이상이면 `related`를 `true`로 설정해라.
       - 연관된 키워드가 전혀 없으면 `related`를 `false`로 설정해라.

    ### [기사]
    [contents]

    ### [DB 키워드 리스트]
    [pred_keywords_from_db]

    ### [출력 형식]
    반드시 아래 JSON 포맷으로만 응답해라. 주석, 설명은 절대 포함하지 마라.

    {{
        "ai_keyword": ["기사에서 추출한 핵심 주제 키워드 리스트"],
        "db_keyword_list": ["입력받은 DB 키워드 리스트 그대로 반환"],
        "related": true 또는 false,
        "reason": ["DB 키워드 리스트 중 기사와 연관된 단어들 (최대 10개)"]
    }}
    """


    # 2. [요약] 기관 관점 요약
    question_summary = f"""
    Reasoning: high
    # Valid channels: analysis, final

    너는 전문적인 뉴스 분석 및 요약 전문가다.
    아래 [기사]를 정밀 분석하여 [대상 기관]의 관점에서 핵심 내용을 요약해라.

    ### [요약 가이드라인]
    1. **기관 중심**: 기사 전체 내용 중 [대상 기관]과 관련된 이슈를 중심으로 요약해라.
    2. **길이 준수**: 'long_summary'는 반드시 5줄 이상으로 작성하여 세부적인 정보까지 포함해라.
    3. **언어 제약**: 생각(Reasoning)은 자유롭게 하되, **최종 답변(JSON 값)은 반드시 한국어**로 작성해라. (조사, 서술어 포함)
    4. **명칭 처리**: 요약문 내에서 기관명을 언급할 때는 기사에 나온 실제 명칭을 사용해라. 만약 기사에서 명칭을 찾을 수 없다면 '해당 기관'이라고 지칭해라. 절대 '[organization]'이라는 텍스트를 그대로 출력하지 마라.
    5. **포맷팅**: JSON 값에는 불필요한 줄바꿈 문자(\\n)나 특수문자를 포함하지 말고 자연스러운 문장으로 이어 써라.

    ### [기관]
    기관: [organization]

    ### [기사]
    [contents]

    ### [출력 형식]
    반드시 아래 JSON 포맷으로만 응답해라. 주석, 설명은 절대 포함하지 마라.

    {{
        "short_summary": "반드시 [대상 기관]을 주어로 하여, 해당 기관의 핵심 행위나 사건을 한 줄로 요약",
        "long_summary": "5줄 이상으로 기사 요약. [대상 기관]을 중심으로 자세한 정보 포함."
    }}
    """ 


    # 3. [감성 분석 통합] 감성 비율 및 근거 분석 (CoT 적용)
    question_sentiment_integrated = f"""
    Reasoning: high
    # Valid channels: analysis, final

    너는 냉철한 '기업 평판 리스크 분석가'다.
    아래 [기사]를 정밀 분석하여 [대상 기관] 입장에서의 감성 비율을 계산하고, 그 근거를 논리적으로 서술해라.

    ### [분석 프로세스]
    1. **심층 분석 및 근거 작성 (Step 1)**: 
       - 기사 전체의 논조와 기관에 미치는 영향을 분석하여 **종합적인 판단 근거**를 작성해라.
       - 그 후, 긍정적 요소, 부정적 요소, 중립적 요소 각각에 대해 **구체적인 이유**를 반드시 작성해라. (해당 요소가 미미하더라도 왜 미미한지, 혹은 왜 없는지라도 작성해야 함)
    2. **비율 산정 (Step 2)**: 
       - 위에서 작성한 근거들의 강도를 비교하여 긍정/부정/중립 비율을 수치화해라.
       - 세 비율의 합은 반드시 100이 되어야 한다.

    ### [대상 기관]
    이름: [organization]
    (동의어: [synonyms])

    ### [기사]
    [contents]

    ### [출력 형식]
    반드시 아래 JSON 포맷으로만 응답해라. 주석, 설명은 절대 포함하지 마라.
    **반드시 모든 'Reason' 필드를 먼저 작성하고, 마지막에 'Ratio'를 기재해라.**

    {{
        "reason": "감성 비율을 판단하게 된 종합적인 근거 (한 문단)",
        "positiveReason": "긍정적 측면에 대한 구체적 근거 (반드시 작성, null 금지)",
        "negativeReason": "부정적 측면에 대한 구체적 근거 (반드시 작성, null 금지)",
        "neutralReason": "중립적 측면에 대한 구체적 근거 (반드시 작성, null 금지)",
        "positiveRatio": "기관에 대해 긍정적으로 작성됐다는 비율 (0~100, float, % 기호 없이)",
        "neutralRatio": "기관에 대해 중립적으로 작성됐다는 비율 (0~100, float, % 기호 없이)",
        "negativeRatio": "기관에 대해 부정적으로 작성됐다는 비율 (0~100, float, % 기호 없이)"
    }}
    """


    # 5. [감성 키워드] 문맥 기반 키워드 추출 및 분류
    sentiment_keywords = f"""
    Reasoning: high
    # Valid channels: analysis, final

    너는 뉴스 기사에서 특정 기관의 평판에 영향을 미치는 핵심 키워드를 추출하는 '평판 분석 전문가'다.
    아래 [기사]를 정밀 분석하여 [대상 기관]과 관련된 키워드를 먼저 중복된 것을 제거 한 채 추출해라
    그 이후, 감성별로 분류해라.

    ### [분석 가이드라인]
    1. **대상 한정**: 타 기관에 대한 내용은 철저히 배제하고, 오직 [대상 기관]의 평판/이미지와 관련된 표현만 추출해라.
    2. **상호 배타성(Mutually Exclusive)**: 하나의 키워드는 오직 하나의 카테고리(긍정, 부정, 중립)에만 속해야 한다.
       - 만약 어떤 키워드가 '긍정'이나 '부정'으로 분류된다면, 절대 '중립'에 포함시키지 마라.
       - 우선순위: 긍정/부정 > 중립. (감성이 뚜렷하면 중립에서 제외)
    3. **문맥 고려**:
       - **긍정**: 기관의 이미지를 실질적으로 향상시키는 내용 (단, '개선 촉구'나 '타 기관 우위' 비교는 제외).
       - **부정**: 기관의 이미지를 실질적으로 저하시키는 내용.
       - **중립**: 기관과 관련되나 평판에 영향이 없는 단순 사실(일정, 통계, 공고 등).
    4. **키워드 형태**: 문맥을 반영한 구체적인 표현(예: "혁신적 성과", "예산 낭비")으로 추출해라.
    5. **언어**: JSON의 모든 값은 반드시 한국어로 작성해라.

    ### [대상 기관]
    이름: [organization]
    (동의어: [synonyms])

    ### [기사]
    [contents]

    ### [출력 형식]
    반드시 아래 JSON 포맷으로만 응답해라. 주석, 설명은 절대 포함하지 마라.

    {{
        "positiveKeywords": ["긍정 키워드1", "긍정 키워드2", ...],
        "negativeKeywords": ["부정 키워드1", "부정 키워드2", ...],
        "neutralKeywords": ["중립 키워드1", "중립 키워드2", ...]
    }}
    """
    
    
    # 유헌수 2026-01-08 [워드클라우드용 키워드 정제] 프롬프트 추가
    # 6. [워드클라우드용 키워드 정제] 문장형 키워드를 간결한 키워드로 정제
    question_refine_keywords_for_wordcloud = f"""
    Reasoning: high
    # Valid channels: analysis, final
    
    너는 '워드클라우드용 키워드 정제 전문가'다.
    아래 [원본 키워드 리스트]는 뉴스 기사에서 맥락을 포함하여 추출된 키워드들이다. 
    이것들을 워드클라우드 시각화에 적합하도록 **핵심 의미만 남기고 간결하게 정제**해라.
    
    ### [정제 가이드라인]
    1. **핵심 의미 보존 (가장 중요)**:
      - 키워드를 줄이더라도 **긍정/부정의 원인**이 되는 핵심 단어는 남겨야 한다.
      - 예: "안전 매뉴얼 강화 요구" (부정) → "매뉴얼 강화 요구" (O), "안전 매뉴얼" (X, 단순 중립 명사가 됨)
      - 예: "영업 이익 적자 전환" (부정) → "적자 전환" (O), "영업 이익" (X)
    2. **불필요한 정보 제거**:
      - **기관명 제거**: [organization] 및 동의어([synonyms])는 삭제해라. 
      - **수치/날짜 제거**: "3.8% 상승", "44억 원" → "상승", "예산" 등 개념으로 변경.
      - **조사/어미 제거**: 명사형 또는 명사구로 끝맺어라.

    3. **길이 최적화**:
      - 가능한 2~4단어 이내의 명사구로 만들어라.
      - 문장형은 핵심 키워드로 요약해라.

    4. **중복 통합**:
      - 의미가 같은 키워드는 하나로 통일해라. (예: "주가 급등", "주식 상승" → "주가 상승")

    ### [대상 기관]
    이름: [organization]
    (동의어: [synonyms])

    ### [원본 키워드 리스트]
    [keywords_list]

    ### [출력 형식]
    반드시 아래 JSON 포맷으로만 응답해라. 
    주석이나 `STEP` 구분 없이 **오직 JSON만** 출력해라.

    {{
       "refinedKeywords": ["정제된 키워드1", "정제된 키워드2", ...]
    }}
    """
    
    # 유헌수 2026-01-09 [상세 요약] 프롬프트 추가
    # 7. Consolidated detail summary prompt (replaces previous 1~5 formats)
    question_detail_summary = f"""
    Reasoning: high
    # Valid channels: analysis, final

    너는 전문적인 뉴스 분석 및 요약 전문가다.
    아래 [기사]를 심층적으로 분석하여 [기관]의 관점에서 `detail_summary`를 생성해라. 이 프롬프트는 기사의 문장 수가 10문장 이상인 경우에만 호출되어야 한다.

    ### [기관]
    기관: [organization]

    ### [기사]
    [contents]

    ### 길이 제약
    - 생성할 문장 수는 최소 [min_sentences]문장, 최대 [max_sentences]문장으로 제한한다.
    - (계산식) 최소: min(5, 문장수/3), 최대: max(10, 문장수/2) — 실제 값은 호출 시 정수로 전달된다.

    ### 작성 지침
    1. **기관 중심**: 기사 전체 내용 중 [기관]과 관련된 이슈를 중심으로 요약해라.
    2. **상세 분석**: 기사의 핵심 사건, 배경, 결과 등을 빠짐없이 포함하여 작성해라. 단순한 사실 나열보다는 인과관계가 드러나도록 서술해라.
    3. **명칭 처리**: 요약문 내에서 기관명을 언급할 때는 기사에 나온 실제 명칭을 사용해라. 만약 기사에서 명칭을 찾을 수 없다면 '해당 기관'이라고 지칭해라. 절대 '[organization]'이라는 텍스트를 그대로 출력하지 마라.
    4. **언어 제약**: 생각(Reasoning)은 자유롭게 하되, **최종 답변(JSON 값)은 반드시 한국어**로 작성해라. (조사, 서술어 포함)
    5. **포맷팅**: JSON 값에는 불필요한 줄바꿈 문자(\n)나 특수문자를 포함하지 말고 자연스러운 문장으로 이어 써라.

    ### 출력 형식
    반드시 아래 JSON 포맷으로만 응답해라. 주석, 설명은 절대 포함하지 마라.

    {{
        "detail_summary": "기사에 대한 상세 요약(한국어, 문장 수 제약 준수)"
    }}
    """

    # 유헌수 2025-12-23 [한국어 번역 및 검수] 프롬프트 추가   
    # 8. [최종 검수] 한국어 번역 및 검수 (Safety Net)
    question_translate_to_korean = f"""
    Reasoning: high
    # Valid channels: analysis, final

    너는 '한국어 번역 및 검수 전문가'다.
    아래 [검수 대상 데이터]는 뉴스 분석 결과다. 값(Value)들이 한국어로 작성되었는지 확인하고, 영어나 다른 언어로 작성된 부분이 있다면 자연스러운 한국어로 번역해라.
    이미 한국어로 잘 작성된 부분은 절대 수정하지 말고 그대로 둬라.

    ### [검수 대상 데이터]
    [json_data]

    ### [작업 가이드라인]
    1. **언어 감지**: 각 필드의 값이 한국어인지 영어(또는 타언어)인지 식별해라.
    2. **번역 수행**:
       - 영어나 타언어로 된 문장은 문맥에 맞게 자연스러운 한국어로 번역해라.
       - 고유명사(기관명, 인명 등)는 한국어 표기를 원칙으로 하되, 필요시 괄호 안에 원어를 병기해라. (예: "KEPCO" -> "한국전력(KEPCO)")
    3. **유지**: 이미 한국어로 작성된 내용은 토씨 하나 바꾸지 말고 그대로 유지해라.
    4. **구조 유지**: 입력된 JSON의 키(Key)와 구조를 완벽하게 유지해서 출력해라.

    ### [출력 형식]
    반드시 입력된 JSON과 동일한 키를 가진 JSON 포맷으로만 응답해라. 주석, 설명은 절대 포함하지 마라.
    """


    # ==================================================================================
    # [Deprecated / Zombie Prompts] 사용하지 않는 구버전 프롬프트 (보관용)
    # ==================================================================================


    
    # question = f""" 
    #     "contents" = [contents]
    #     위의 HTML에서 기사를 추출하고 아래 형식에 맞춰 JSON 객체로 응답해줘. JSON 객체의 구조는 다음과 같아
    #     답변은 주석없이 json데이터만 줘. "contents"는 다시 반환할 필요 없어.
    # {{
    #     "keyword" : [주요 키워드1, 주요 키워드2, 주요 키워드3],
    #     "predkeywords":  [pred_keywords_from_db] 중 가장 유사도가 높은 키워드 순으로 3개만, "{{"키워드1": "유사도점수", "키워드2": "유사도점수", "키워드3": "유사도점수"}}" 형태로 만들어줘",
    #     "short_summary" : "한줄 기사 요약",
    #     "long_summary" : "500자로 기사 요약, long_summary는 자세한 정보까지 요약에 포함되어야 해.",
    #     "sentiments" :  {{
    #         "organization" : "위 기사가 [org_name_list_from_db] 기관 중 관련된 기사이면 가장 유사도가 높은 기관 순으로 기관명을 알려줘. 리스트에 있는 기관명과 동일한 것만 찾아. 리스트 형식으로 반환해줘",
    #         "positiveRatio": "기사 내용이 기관에 대한 긍정적인 비율 (%), 주석 달지말고 비율만 알려줘. organization의 개수와 동일한 크기를 가진 리스트 형식으로 반환해줘, %없이 출력해 ",
    #         "negativeRatio": "기사 내용이 기관에 대한 부정적인 비율 (%), 주석 달지말고 비율만 알려줘.  organization의 개수와 동일한 크기를 가진 리스트 형식으로 반환해줘, %없이 출력해 ",
    #         "neutralRatio": "기사 내용이 기관에 대한 중립적인 비율 (%), 주석 달지말고 비율만 알려줘.  organization의 개수와 동일한 크기를 가진 리스트 형식으로 반환해줘, %없이 출력해 ",
    #         "reason": "긍정과 부정 비율 판단 근거(문장 형식).  organization의 개수와 동일한 크기를 가진 리스트 형식으로 반환해줘",
    #         "positiveReason": "긍정 비율 판단 근거 (문장 형식)",
    #         "negativeReason": "부정 비율 판단 근거 (문장 형식)",
    #         "positiveKeywords": ["긍정키워드1", "긍정키워드2", "긍정키워드3"],
    #         "negativeKeywords": ["부정키워드1", "부정키워드2", "부정키워드3"]
    #     }}
    # }} 
    
    # """
    # answer_template = f"""
    # {{
    #     "keyword" : [주요 키워드1, 주요 키워드2, 주요 키워드3],
    #     "predkeywords":  [pred_keywords_from_db] 중 가장 유사도가 높은 키워드 순으로 3개만, "{{"키워드1": "유사도점수", "키워드2": "유사도점수", "키워드3": "유사도점수"}}" 형태로 만들어줘",
    #     "short_summary" : "한줄 기사 요약",
    #     "long_summary" : "500자로 기사 요약, long_summary는 자세한 정보까지 요약에 포함되어야 해.",
    #     "sentiment" :  {{
    #         "organization" : "위 기사가 [org_name_list_from_db] 기관 중 관련된 기사이면 가장 유사도가 높은 기관 순으로 기관명을 알려줘. 리스트에 있는 기관명과 동일한 것만 찾아. 리스트 형식으로 반환해줘",
    #         "positiveRatio": "기사 내용이 기관에 대한 긍정적인 비율 (%), 주석 달지말고 비율만 알려줘. organization의 개수와 동일한 크기를 가진 리스트 형식으로 반환해줘, %없이 출력해 ",
    #         "negativeRatio": "기사 내용이 기관에 대한 부정적인 비율 (%), 주석 달지말고 비율만 알려줘.  organization의 개수와 동일한 크기를 가진 리스트 형식으로 반환해줘, %없이 출력해 ",
    #         "neutralRatio": "기사 내용이 기관에 대한 중립적인 비율 (%), 주석 달지말고 비율만 알려줘.  organization의 개수와 동일한 크기를 가진 리스트 형식으로 반환해줘, %없이 출력해 ",
    #         "reason": "긍정과 부정 비율 판단 근거(문장 형식).  organization의 개수와 동일한 크기를 가진 리스트 형식으로 반환해줘",
    #         "positiveReason": "긍정 비율 판단 근거 (문장 형식)",
    #         "negativeReason": "부정 비율 판단 근거 (문장 형식)",
    #         "positiveKeywords": ["긍정키워드1", "긍정키워드2", "긍정키워드3"],
    #         "negativeKeywords": ["부정키워드1", "부정키워드2", "부정키워드3"]
    #     }}
    # }} """
    # question_new = f"""
    # 다음 HTML에서 기사를 추출하고 아래 형식에 맞춰 JSON 객체로 응답해줘. JSON 객체의 구조는 다음과 같아
    # {{
    #     "keyword" : [주요 키워드1, 주요 키워드2, 주요 키워드3],
    #     "predkeywords":  [pred_keywords_from_db] 중 가장 유사도가 높은 키워드 순으로 3개만, "{{"키워드1": "유사도점수", "키워드2": "유사도점수", "키워드3": "유사도점수"}}" 형태로 만들어줘",
    #     "short_summary" : "한줄 기사 요약",
    #     "long_summary" : "500자로 기사 요약, long_summary는 자세한 정보까지 요약에 포함되어야 해.",
    #     "sentiment" :  {{
    #         "organization" : "위 기사가 [org_name_list_from_db] 기관 중 관련된 기사이면 가장 유사도가 높은 기관 순으로 기관명을 알려줘. 리스트에 있는 기관명과 동일한 것만 찾아. 리스트 형식으로 반환해줘",
    #         "positiveRatio": "기사 내용이 기관에 대한 긍정적인 비율 (%), 주석 달지말고 비율만 알려줘. organization의 개수와 동일한 크기를 가진 리스트 형식으로 반환해줘, %없이 출력해 ",
    #         "negativeRatio": "기사 내용이 기관에 대한 부정적인 비율 (%), 주석 달지말고 비율만 알려줘.  organization의 개수와 동일한 크기를 가진 리스트 형식으로 반환해줘, %없이 출력해 ",
    #         "neutralRatio": "기사 내용이 기관에 대한 중립적인 비율 (%), 주석 달지말고 비율만 알려줘.  organization의 개수와 동일한 크기를 가진 리스트 형식으로 반환해줘, %없이 출력해 ",
    #         "reason": "긍정과 부정 비율 판단 근거.",
    #         "positiveReason": "긍정 비율 판단 근거 (문장 형식),",
    #         "negativeReason": "부정 비율 판단 근거 (문장 형식)",
    #         "positiveKeywords": ["긍정키워드1", "긍정키워드2", "긍정키워드3"],
    #         "negativeKeywords": ["부정키워드1", "부정키워드2", "부정키워드3"]
    #     }}
    # }} 
    # """    

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
    

    # ====================================================================================
    # # 20251013 리자: 프롬프트 수정: 기관 입장에서 ..? 
    # # 1. 기관 추가, 2. keyword 제거
    # question_summary = f"""
    # contents : [contents]
    # organization : [organization]
    # 위의 기사를 분석하여 아래 형식에 맞춰 JSON 객체로 응답해줘 (\n, \r\n, \t 제거). JSON 객체의 구조는 다음과 같아:
    # {{
    #     "short_summary": "한줄 기사 요약",
    #     "long_summary": "5줄 이상으로 기사 요약, long_summary는 자세한 정보까지 요약에 포함되어야 해. organization을 중심으로 요약해줘."
    # }}
    # """ 
    # ###"short_summary": "한줄 기사 요약",
    #     ##"long_summary": "5줄 이상으로 기사 요약, long_summary는 자세한 정보까지 요약에 포함되어야 해."
    #    # "category_reason": 반환한 category별로 이유를 설명해줘 dictionary 형태로.
    
    # # 추가
    # # ~Ratio : 0~1사이의 float 형태로 출력해줘 --> 2025.03.03 최미화 질문 : 왜 넣은거죠? 
    # # 2025.03.03 : Prompt 수정, 최미화, 기관 이름이 명확이 추출되도록 수정함 
    # # 2025.03.10 : Prompt 수정, 최미화, 긍정키워드, 부정키워드 추출 방법 기술 추가함. 
    # question_sentiment = f"""
    # contents : [contents]
    # 위 기사를 분석하여 아래 JSON 객체 구조에 정확히 맞춰서 응답해 줘. organization에는 하나의 기관만 넣고  하나의 기관에 대해서 positiveRatio~negativeKeywords 정보를 만들어줘.
    # 여러 기관과 관련이 있으면 organization에 기관을 하나 추가하고 그에 맞는 positiveRatio~negativeKeywords 정보를 추가해줘. 
    # 기사에 기관명, 기관명 약자 등이 언급된 경우에만 관련 기관으로 판단해줘. 해당 기관이 관련있다는 근거는 orginizationReason에 추가해줘.
    # {{
    #     "sentiments" :  [{{
    #         "organization" : "위 기사가 [org_name_list_from_db] 기관 중 관련된 기사이면 가장 유사도가 높은 기관 순으로 기관명을 알려줘. 리스트에 있는 기관명과 동일한 것만 찾아.",
    #         "positiveRatio": "기사 내용이 기관에 대한 긍정적인 비율 (%), 주석 달지말고 비율만 알려줘. %없이 0~100사이의 float 형태로 출력해 ",
    #         "negativeRatio": "기사 내용이 기관에 대한 부정적인 비율 (%), 주석 달지말고 비율만 알려줘. %없이 0~100사이의 float 형태로 출력해 ",
    #         "neutralRatio": "기사 내용이 기관에 대한 중립적인 비율 (%), 주석 달지말고 비율만 알려줘. %없이 0~100사이의 float 형태로 출력해 ",
    #         "reason": "긍정과 부정 비율 판단 근거.",
    #         "positiveReason": "긍정 비율 판단 근거 (문장 형식),",
    #         "negativeReason": "부정 비율 판단 근거 (문장 형식)",
    #         "positiveKeywords": ["긍정키워드1", "긍정키워드2", "긍정키워드3"]  전체 기사에서 의미를 파악해서 문맥이 있는 긍정키워드를 추출해줘. 문맥있는 표현이면 좋겠어. ,
    #         "negativeKeywords": ["부정키워드1", "부정키워드2", "부정키워드3"]  전체 기사에서 의미를 파악해서 문맥이 있는 부정키워드를 추출해줘. 문맥있는 표현이면 좋겠어. ,
    # 		"orginizationReason" : "해당 기관이 관련있다는 근거"            
    #     }}]
    # }} 
    # """    
    
    
    # ##########################################################

    # # 20251013 리자: 프롬프트 3)분리
    # question_sentiment_ratio = f"""
    # 기사 : [contents]
    # 기관 : [organization] (이 기관은 [synonyms]로도 불립니다.)
    # 위 기사에서 해당 기관 또는 그 별칭([synonyms])이 언급된 부분을 중심으로 감성 분석을 수행해 줘.
    # 기관에 대한 언급 중 긍정 / 부정 / 중립의 비율을 추정해서 아래 JSON 형식으로만 답변해.

    #     {{
    #         "positiveRatio": "기관 언급 중 긍정적 내용의 비율 (0~100, float, % 기호 없이)",
    #         "neutralRatio": "기관 언급 중 중립적 내용의 비율 (0~100, float, % 기호 없이)",
    #         "negativeRatio": "기관 언급 중 부정적 내용의 비율 (0~100, float, % 기호 없이)"
    #     }}

    #     세 비율의 합은 100이 되어야 해. 주석이나 설명은 넣지 마.
    # """
    
    # # question_negative_ratio = f"""
    # # contents : [contents]
    # # organization : [organization]
   
    
    # # """
    
    # # question_neutral_ratio = f"""
    # # contents : [contents]
    # # organization : [organization]
   
    
    # # """
    
    # #all three reasons using predictions as input;
    # # question_sentiment_ratio => question_reason
    
    # sentiment_reason = f"""
    # 기사 : [contents]
    # 기관 : [organization] (이 기관은 [synonyms]로도 불립니다.)
    
    # 해당 기관을 대상으로 기사를 분석된 감성 비율은 다음과 같아:
    #     - 긍정: [positiveRatio]
    #     - 부정: [negativeRatio]

    #     이 비율을 판단한 이유와 주요 키워드를 작성해줘.
    #     출력은 아래 JSON 형식으로 해.

    #     {{
    #         "reason": "긍정과 부정 비율을 종합적으로 판단한 근거 (한 문단)",
    #         "positiveReason": "긍정 비율 판단 근거 (문장 형식)",
    #         "negativeReason": "부정 비율 판단 근거 (문장 형식)",
        
    #     }}
    
    # """
    
    # sentiment_keywords = f"""
    # 기사 : [contents]
    # 기관 : [organization] (이 기관은 [synonyms]로도 불립니다.)
    
    # 이 기사는 여러 주제를 다룰 수 있지만, 
    #     **오직 해당 기관([organization])의 이미지, 평판, 또는 대중 인식에 영향을 미치는 내용만** 분석해 줘.

    #     기관과 직접적으로 관련된 **긍정적인 요인**과 **부정적인 요인**을 찾아 아래 JSON 형식으로 정리해 줘.
    #     단순한 단어나 기사 전반의 키워드가 아니라, 
    #     기관의 평판(이미지)에 영향을 주는 문맥 있는 표현을 뽑아야 해. 
    #     (예: "기술 혁신", "성과 향상", "비리 의혹", "경영 악화" 등)

    #     {{
    #         "positiveKeywords": ["긍정 키워드1", "긍정 키워드2", "긍정 키워드3"],
    #         "negativeKeywords": ["부정 키워드1", "부정 키워드2", "부정 키워드3"]
    #     }}

    #     출력 시:
    #     - JSON만 출력해. 
    #     - 주석, 설명, 문장형 해석은 절대 넣지 마.

    # """

    # ##########################################################
    # ====================================================================================



    # # question_summary 이전에 db_keyword_list와 비교하여 검증 20250429 mcst
    # question_verify = f"""
    # [Step 1] 다음 기사(contents)와 db_keyword_list를 제공합니다.
    # - contents: [contents]
    # - db_keyword_list: [pred_keywords_from_db]

    # [Step 2] 분석하고 다음과 같은 JSON 객체로만 답변해 주세요. 반드시 (\n, \r\n, \t 제거) 등 특수문자는 제거합니다.

    # JSON 형식:
    # {{
    #     "ai_keyword": 기사(contents)에서 주요 이슈나 주제를 추출하여 핵심 키워드를 최대 5개 리스트로 작성합니다. 문맥을 고려한 표현을 사용하세요.
    #     "db_keyword_list": 제공한 db_keyword_list를 그대로 넣습니다.
    #     "related": ai_keyword와 db_keyword_list를 비교하여, 1개 이상 깊히 관련있는 단어가 있으면 true, 전혀 관련이 없으면 false로 합니다.
    #     "reason": related가 true 이면, ai_keyword와 깊히 관련있는 단어를 반드시 db_keyword_list 안에서 최대 3개를 선택하여 관련 키워드를 리스트형식으로 작성합니다. 
    #     "description" : reason에 표시하는 항목의 결정한 이유는 ai_keyword의 어떤 항목과 db_keyword_list의 어떤항목이 관련이 깊은지 알려주세요.
    # }}

    # [특별한 규칙]
    # - related가 true 이면,  반드시 reason과 description을 출력해야합니다.
    # - reason은 오직 db_keyword_list에서만 선택해야 합니다. (ai_keyword에서 선택하면 절대 안 됩니다)
    # - 선택할 db_keyword_list가 하나도 없으면, related는 반드시 false로 설정하세요.
    # - 절대 ai_keyword 항목에서 reason을 뽑지 마세요. db_keyword_list만 사용하세요.
    # - reason 항목중에서 만약에 db_keyword_list에 존재한다면 좋지만, ai_keyword 항목에만 있는 항목은 제거
    
    # [추가 설명]
    # - reason에 표시 항목은 예를 들어 ai_keyword의 '탄소중립'과 db_keyword_list의 'ESG'가 관련이 있으면 'ESG'를 표시
    # - reason에 표시 항목은 예를 들어 ai_keyword의 '대처훈련'과 db_keyword_list의 '안전'이 관련이 있으면 '안전'을 표시
    # - reason에 표시 항목은 중복을 제거

    # [최종 조건]
    # - 출력은 반드시 위 JSON 구조를 지켜야 합니다.
    # - 설명문 없이 JSON만 출력하세요.
    # """
    
    