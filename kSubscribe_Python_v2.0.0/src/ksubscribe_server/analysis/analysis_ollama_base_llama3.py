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
    # [Active Prompts] Llama 3 & Bllossom 최적화 프롬프트 (GPT-OSS 20B 내용 유지)
    # ==================================================================================

    # 1. [검증] 기사와 키워드 연관성 검증
    question_verify = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

너는 뉴스 기사와 사전 정의된 키워드 간의 연관성을 검증하는 '데이터 매칭 전문가'다.
아래 [기사]의 핵심 주제를 파악하고, 제공된 [DB 키워드 리스트]와 매칭되는 항목이 있는지 검증해라.

### [검증 가이드라인]
1. **주제 파악**: 기사 내용을 분석하여 핵심 이슈를 나타내는 'AI 키워드'를 먼저 추출해ra.
2. **매칭 확인**: 추출한 'AI 키워드'와 [DB 키워드 리스트]를 비교하여, 의미적으로 연결되는 항목이 있는지 확인해ra.
3. **엄격한 선택 규칙**:
   - `reason` 필드에는 **반드시 [DB 키워드 리스트]에 포함된 단어만** 기재해야 한다.
   - 기사 본문에 있는 단어라도 [DB 키워드 리스트]에 없다면 `reason`에 넣지 마ra.
4. **결과 판정**:
   - 연관된 키워드가 1개 이상이면 `related`를 `true`로 설정해ra.
   - 연관된 키워드가 전혀 없으면 `related`를 `false`로 설정해ra.

### [출력 형식]
반드시 아래 JSON 포맷으로만 응답해ra. 주석, 설명은 절대 포함하지 마ra.

{{
    "ai_keyword": ["기사에서 추출한 핵심 주제 키워드 리스트"],
    "db_keyword_list": ["입력받은 DB 키워드 리스트 그대로 반환"],
    "related": true 또는 false,
    "reason": ["DB 키워드 리스트 중 기사와 연관된 단어들 (최대 10개)"]
}}<|eot_id|><|start_header_id|>user<|end_header_id|>

### [기사]
""" + """
[contents]
""" + """

### [DB 키워드 리스트]
[pred_keywords_from_db]<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""

    # 2. [요약] 기관 관점 요약
    question_summary = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

너는 전문적인 뉴스 분석 및 요약 전문가다.
아래 [기사]를 정밀 분석하여 [대상 기관]의 관점에서 핵심 내용을 요약해ra.

### [요약 가이드라인]
1. **기관 중심**: 기사 전체 내용 중 [대상 기관]과 관련된 이슈를 중심으로 요약해ra.
2. **길이 준수**: 'long_summary'는 반드시 5줄 이상으로 작성하여 세부적인 정보까지 포함해ra.
3. **언어 제약**: 생각(Reasoning)은 자유롭게 하되, **최종 답변(JSON 값)은 반드시 한국어**로 작성해ra. (조사, 서술어 포함)
4. **명칭 처리**: 요약문 내에서 기관명을 언급할 때는 기사에 나온 실제 명칭을 사용해ra. 만약 기사에서 명칭을 찾을 수 없다면 '해당 기관'이라고 지칭해ra. 절대 '[organization]'이라는 텍스트를 그대로 출력하지 마ra.
5. **포맷팅**: JSON 값에는 불필요한 줄바꿈 문자(\\n)나 특수문자를 포함하지 말고 자연스러운 문장으로 이어 써ra.

### [출력 형식]
반드시 아래 JSON 포맷으로만 응답해ra. 주석, 설명은 절대 포함하지 마ra.

{{
    "short_summary": "반드시 [대상 기관]을 주어로 하여, 해당 기관의 핵심 행위나 사건을 한 줄로 요약",
    "long_summary": "5줄 까지 기사 요약. [대상 기관]을 중심으로 자세한 정보 포함."
}}<|eot_id|><|start_header_id|>user<|end_header_id|>

### [기관]
기관: [organization]

### [기사]
""" + """
[contents]
""" + """<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""

    # 3. [감성 분석 통합] 감성 비율 및 근거 분석 (CoT 적용)
    question_sentiment_integrated = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

너는 냉철한 '기업 평판 리스크 분석가'다.
아래 [기사]를 정밀 분석하여 [대상 기관] 입장에서의 감성 비율을 계산하고, 그 근거를 논리적으로 서술해ra.

### [분석 프로세스]
1. **심층 분석 및 근거 작성 (Step 1)**: 
   - 기사 전체의 논조와 기관에 미치는 영향을 분석하여 **종합적인 판단 근거**를 작성해ra.
   - 그 후, 긍정적 요소, 부정적 요소, 중립적 요소 각각에 대해 **구체적인 이유**를 반드시 작성해ra. (해당 요소가 미미하더라도 왜 미미한지, 혹은 왜 없는지라도 작성해야 함)
2. **비율 산정 (Step 2)**: 
   - 위에서 작성한 근거들의 강도를 비교하여 긍정/부정/중립 비율을 수치화해ra.
   - 세 비율의 합은 반드시 100이 되어야 한다.

### [출력 형식]
반드시 아래 JSON 포맷으로만 응답해ra. 주석, 설명은 절대 포함하지 마ra.
**반드시 모든 'Reason' 필드를 먼저 작성하고, 마지막에 'Ratio'를 기재해ra.**

{{
    "reason": "감성 비율을 판단하게 된 종합적인 근거 (한 문단)",
    "positiveReason": "긍정적 측면에 대한 구체적 근거 (반드시 작성, null 금지)",
    "negativeReason": "부정적 측면에 대한 구체적 근거 (반드시 작성, null 금지)",
    "neutralReason": "중립적 측면에 대한 구체적 근거 (반드시 작성, null 금지)",
    "positiveRatio": "기관에 대해 긍정적으로 작성됐다는 비율 (0~100, float, % 기호 없이)",
    "neutralRatio": "기관에 대해 중립적으로 작성됐다는 비율 (0~100, float, % 기호 없이)",
    "negativeRatio": "기관에 대해 부정적으로 작성됐다는 비율 (0~100, float, % 기호 없이)"
}}<|eot_id|><|start_header_id|>user<|end_header_id|>

### [대상 기관]
이름: [organization]
(동의어: [synonyms])

### [기사]
""" + """
[contents]
""" + """<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""

    # 5. [감성 키워드] 문맥 기반 키워드 추출 및 분류
    sentiment_keywords = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

너는 뉴스 기사에서 특정 기관의 평판에 영향을 미치는 핵심 키워드를 추출하는 '평판 분석 전문가'다.
아래 [기사]를 정밀 분석하여 [대상 기관]과 관련된 키워드를 먼저 중복된 것을 제거 한 채 추출해ra
그 이후, 감성별로 분류해ra.

### [분석 가이드라인]
1. **대상 한정**: 타 기관에 대한 내용은 철저히 배제하고, 오직 [대상 기관]의 평판/이미지와 관련된 표현만 추출해ra.
2. **상호 배타성(Mutually Exclusive)**: 하나의 키워드는 오직 하나의 카테고리(긍정, 부정, 중립)에만 속해야 한다.
   - 만약 어떤 키워드가 '긍정'이나 '부정'으로 분류된다면, 절대 '중립'에 포함시키지 마ra.
   - 우선순위: 긍정/부정 > 중립. (감성이 뚜렷하면 중립에서 제외)
3. **문맥 고려**:
   - **긍정**: 기관의 이미지를 실질적으로 향상시키는 내용 (단, '개선 촉구'나 '타 기관 우위' 비교는 제외).
   - **부정**: 기관의 이미지를 실질적으로 저하시키는 내용.
   - **중립**: 기관과 관련되나 평판에 영향이 없는 단순 사실(일정, 통계, 공고 등).
4. **키워드 형태**: 문맥을 반영한 구체적인 표현(예: "혁신적 성과", "예산 낭비")으로 추출해ra.
5. **언어**: JSON의 모든 값은 반드시 한국어로 작성해ra.

### [출력 형식]
반드시 아래 JSON 포맷으로만 응답해ra. 주석, 설명은 절대 포함하지 마ra.

{{
    "positiveKeywords": ["긍정 키워드1", "긍정 키워드2", ...],
    "negativeKeywords": ["부정 키워드1", "부정 키워드2", ...],
    "neutralKeywords": ["중립 키워드1", "중립 키워드2", ...]
}}<|eot_id|><|start_header_id|>user<|end_header_id|>

### [대상 기관]
이름: [organization]
(동의어: [synonyms])

### [기사]
""" + """
[contents]
""" + """<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""

    # 6. [최종 검수] 한국어 번역 및 검수 (Safety Net)
    question_translate_to_korean = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

너는 '한국어 번역 및 검수 전문가'다.
아래 [검수 대상 데이터]는 뉴스 기사([기사])를 분석한 결과다. 
값(Value)들이 한국어로 작성되었는지 확인하고, 영어나 다른 언어로 작성된 부분이 있다면 [기사]의 문맥과 표현을 참고하여 자연스러운 한국어로 번역해ra.
이미 한국어로 잘 작성된 부분은 절대 수정하지 말고 그대로 둬ra.

### [검수 대상 필드]
이 검사에서는 다음 필드를 특히 확인한다: `short_summary`, `long_summary`, `ai_keyword`, `reason`, `positiveReason`, `negativeReason`, `neutralReason`, `positiveKeywords`, `negativeKeywords`, `neutralKeywords`.

### [작업 가이드라인]
1. **언어 감지**: 각 필드의 값이 한국어인지 영어(또는 타언어)인지 식별해ra.
2. **문맥 기반 번역**:
   - 영어나 타언어로 된 문장은 [기사]의 내용을 참고하여 가장 적절하고 자연스러운 한국어 표현으로 번역해ra.
   - 직역보다는 기사의 맥락에 맞는 의역을 사용해ra.
   - 고유명사(기관명, 인명 등)는 한국어 표기를 원칙으로 하되, 필요시 괄호 안에 원어를 병기해ra. (예: "KEPCO" -> "한국전력(KEPCO)")
3. **유지**: 이미 한국어로 작성된 내용은 토씨 하나 바꾸지 말고 그대로 유지해ra.
4. **구조 유지**: 입력된 JSON의 키(Key)와 구조를 완벽하게 유지해서 출력해ra.

### [출력 형식]
반드시 입력된 JSON과 동일한 키를 가진 JSON 포맷으로만 응답해ra. 주석, 설명은 절대 포함하지 마ra.<|eot_id|><|start_header_id|>user<|end_header_id|>

### [기사]
""" + """
[contents]
""" + """

### [검수 대상 데이터]
[json_data]<|eot_id|><|start_header_id|>assistant<|end_header_id|>

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
    # 
    # """
