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
import yaml
import os
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

    def __init__(self, yaml_path: str = None):
        """
        :param yaml_path: YAML 프롬프트 파일 경로 (선택적)
                          제공되면 YAML에서 프롬프트 로드, 없으면 기존 하드코딩된 프롬프트 사용
        """
        if yaml_path and os.path.exists(yaml_path):
            # YAML 파일에서 프롬프트 로드
            self._load_prompts_from_yaml(yaml_path)
        else:
            # 기존 하드코딩된 프롬프트 사용 (기본값)
            self._init_default_prompts()
    
    def _load_prompts_from_yaml(self, yaml_path: str):
        """YAML 파일에서 프롬프트를 로드하여 인스턴스 변수로 설정"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        prompts = config.get('prompts', {})
        
        # YAML의 각 프롬프트를 인스턴스 변수로 설정
        self.question_verify = prompts.get('question_verify', '')
        self.question_summary = prompts.get('question_summary', '')
        self.question_sentiment_integrated = prompts.get('question_sentiment_integrated', '')
        self.sentiment_keywords = prompts.get('sentiment_keywords', '')
        self.question_refine_keywords_for_wordcloud = prompts.get('question_refine_keywords_for_wordcloud', '')
        self.question_translate_to_korean = prompts.get('question_translate_to_korean', '')
        
        # Long Detail Summary Format 1~5 (모양만)
        self.question_longdetail_summary_format1 = prompts.get('question_longdetail_summary_format1', '')
        self.question_longdetail_summary_format2 = prompts.get('question_longdetail_summary_format2', '')
        self.question_longdetail_summary_format3 = prompts.get('question_longdetail_summary_format3', '')
        self.question_longdetail_summary_format4 = prompts.get('question_longdetail_summary_format4', '')
        self.question_longdetail_summary_format5 = prompts.get('question_longdetail_summary_format5', '')
    
    def _init_default_prompts(self):
        """기존 하드코딩된 프롬프트 초기화 (기본 동작)"""
        # 기존 프롬프트 정의는 그대로 유지 (아래 코드에서 정의됨)
        # Long Detail Summary Format 1~5는 빈 문자열로 초기화
        self.question_longdetail_summary_format1 = ""
        self.question_longdetail_summary_format2 = ""
        self.question_longdetail_summary_format3 = ""
        self.question_longdetail_summary_format4 = ""
        self.question_longdetail_summary_format5 = ""

    def nanoseconds_to_seconds(self, nanoseconds):
        # 나노초를 초로 변환
        return nanoseconds / 1_000_000_000    
    
    # ==================================================================================
    # [Active Prompts] 실제 서비스에서 사용 중인 프롬프트 정의
    # ==================================================================================

    # 1. [검증] 기사와 키워드 연관성 검증
    question_verify = f"""
    Reasoning: high
    # Valid channels: analysis, final

    너는 뉴스 기사와 사전 정의된 키워드 간의 연관성을 검증하는 '데이터 매칭 전문가'다.
    아래 [기사]의 핵심 주제를 파악하고, 제공된 [DB 키워드 리스트]와 매칭되는 항목이 있는지 검증해라.

    ### [검증 가이드라인]
    1. **주제 파악**: 기사 내용을 분석하여 핵심 이슈나 주제를 나타내는 '키워드'를 먼저 추출해라.
    2. **매칭 확인**: 추출한 '키워드'와 [DB 키워드 리스트]를 비교하여, 의미적으로 연결되는 항목이 있는지 확인해라.
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
    2. **길이 준수**: 'long_summary'는 반드시 5문장 이하로 작성하여 세부적인 정보까지 포함해라.
    3. **언어 제약**: 생각(Reasoning)은 자유롭게 하되, **최종 답변(JSON 값)은 반드시 한국어**로 작성해라. (조사, 서술어 포함)
    4. **명칭 처리**: 요약문 내에서 기관명을 언급할 때는 기사에 나온 실제 명칭을 사용해라. 만약 기사에서 명칭을 찾을 수 없다면 '해당 기관'이라고 지칭해라. 절대 '[organization]'이라는 텍스트를 그대로 출력하지 마라.
    5. **포맷팅**: JSON 값에는 불필요한 줄바꿈 문자(\\n)나 특수문자를 포함하지 말고 자연스러운 문장으로 이어 써라.

    ### [기관]
    기관: [organization]
    (동의어: [synonyms])

    ### [기사]
    [contents]

    ### [출력 형식]
    반드시 아래 JSON 포맷으로만 응답해라. 주석, 설명은 절대 포함하지 마라.

    **중요**: 'short_summary'와 'short_summary2'를 **동시에** 작성해라.
    - 'short_summary': [대상 기관]의 행위, 사건, 평가 등을 한 줄로 요약 (기관명 포함)
    - 'short_summary2': 'short_summary'와 동일한 내용이지만, [대상 기관]의 기관명([organization], [synonyms])과 붙어 있던 조사(의, 과, 와, 이, 가 등)나 격(을, 를, 에, 에서 등)을 제거한 문장

    {{
        "short_summary": "반드시 [대상 기관]의 행위, 사건, 평가 등을 한 줄로 요약",
        "short_summary2": "short_summary와 동일한 내용이지만 기관명과 동의어, 조사/격을 제거한 문장",
        "long_summary": "5문장 이하로 기사 요약. [대상 기관]을 중심으로 자세한 정보 포함."
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

    # # 3. [감성 비율] 긍정/부정/중립 비율 분석
    # question_sentiment_ratio = f"""
    # Reasoning: high
    # # Valid channels: analysis, final

    # 너는 냉철한 '기업 평판 리스크 분석가'다.
    # 아래 [기사]를 정밀 분석하여 [대상 기관] 입장에서의 감성 비율을 계산해라.

    # ### [분석 핵심 가이드라인]
    # 1. **중립의 함정 주의**: 기사의 문체가 건조하고 객관적(Dry Tone)이라도, 내용이 **'소송', '갈등', '법적 분쟁', '내분', '감사 지적', '손실'**을 다루고 있다면 이는 '중립'이 아니라 명백한 **'부정(Negative)'**이다.
    # 2. **동의어 처리**: 기사 내에서 [organization] 또는 [synonyms]로 지칭된 대상을 동일하게 취급해라.

    # ### [대상 기관]
    # 이름: [organization]
    # (동의어: [synonyms])

    # ### [기사]
    # [contents]

    # ### [출력 형식]
    # 반드시 아래 JSON 포맷으로만 응답해라. 주석, 설명은 절대 포함하지 마라.
    # positiveRatio, neutralRatio, negativeRatio의 합은 100이 되어야 한다.

    # {{
    #     "analysis_summary": "판단 근거 1문장 (예: 문체는 객관적이나 기관 간 소송이 발생했으므로 부정적 이슈임)",
    #     "positiveRatio": "기관에 대해 긍정적으로 작성됐다는 비율 (0~100, float, % 기호 없이)",
    #     "neutralRatio": "기관에 대해 중립적으로 작성됐다는 비율 (0~100, float, % 기호 없이)"
    #     "negativeRatio": "기관에 대해 부정적으로 작성됐다는 비율 (0~100, float, % 기호 없이)"
    # }}
    # """

    # # 4. [감성 근거] 비율 판단 근거 서술
    # sentiment_reason = f"""
    # Reasoning: high
    # # Valid channels: analysis, final

    # 너는 데이터에 기반하여 논리적 근거를 제시하는 '평판 리스크 분석가'다.
    # 앞서 분석된 [감성 비율]을 바탕으로, 왜 그런 결과가 나왔는지 [기사] 내용을 인용하여 구체적인 근거를 작성해라.

    # ### [작성 가이드라인]
    # 1. **문맥 중심 서술**: 단순한 단어 나열이 아니라, 해당 내용이 왜 기관의 이미지에 긍정/부정적인지 기사의 문맥(Context)을 들어 설명해라.
    # 2. **비교/대조 명시**: 타 기관과의 비교나, 외부의 개선 요구 사항이 포함된 경우 이를 명확히 구분하여 서술해라.
    # 3. **중립성 확인**: 단순 사실 전달(일정, 공고 등)은 감정적 평가에서 배제되었음을 명시해라.
    # 4. **언어**: 모든 문장은 반드시 한국어로 작성해라.

    # ### [대상 기관]
    # 이름: [organization]
    # (동의어: [synonyms])

    # ### [분석된 감성 비율]
    # - 긍정: [positiveRatio]
    # - 부정: [negativeRatio]
    # - 중립: [neutralRatio]

    # ### [기사]
    # [contents]

    # ### [출력 형식]
    # 반드시 아래 JSON 포맷으로만 응답해라. 주석, 설명은 절대 포함하지 마라.

    # {{
    #     "reason": "긍정과 부정 비율을 종합적으로 판단한 근거 (한 문단으로 요약)",
    #     "positiveReason": "긍정 비율 판단 근거 (문장 형식)",
    #     "negativeReason": "부정 비율 판단 근거 (문장 형식)",
    #     "neutralReason": "중립 비율 판단 근거 (문장 형식)"
    # }}
    # """

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

    # 6. [워드클라우드용 키워드 정제] 문장형 키워드를 간결한 키워드로 정제
    question_refine_keywords_for_wordcloud = f"""
    Reasoning: high
    # Valid channels: analysis, final

    너는 '워드클라우드용 키워드 정제 전문가'다.
    아래 [원본 키워드 리스트]는 뉴스 기사에서 추출된 감성별 키워드들이다. 이 중 일부는 문장 형태이거나 너무 자세한 정보를 포함하고 있어 워드클라우드에 적합하지 않다.
    워드클라우드는 빈도수를 가중치로 사용하므로, 같은 의미의 다양한 표현을 하나의 핵심 키워드로 통합해야 한다.

    ### [대상 기관]
    이름: [organization]
    (동의어: [synonyms])

    ### [기사] (참고용, 키워드 정제 시 문맥 파악에 활용)
    [contents]

    ### [원본 키워드 리스트]
    [keywords_list]
    
    **⚠️ 중요**: 
    - 기사 내용은 키워드 정제 시 문맥 파악에만 활용해라.
    - **절대로 새로운 키워드를 추가하지 마라.** 원본 키워드 리스트에 있는 키워드만 정제해라.
    - 원본 키워드 리스트에 없는 키워드는 출력에 포함하지 마라.

    ### [정제 가이드라인]
    1. **문장 → 키워드 변환**:
       - 문장형 표현은 핵심 개념만 추출해라.
       - 예: "한전 또한 발전, 송전, 변전 등 전력 사업에 목적을 둔 사업자이기 때문에..." 
         → "전력 사업 집중" 또는 "사업 목적 명확"
    
    2. **수치 제거 및 추상화**:
       - 구체적인 수치, 비율, 금액, 날짜는 제거하고 핵심 개념만 추출해라.
       - 예: "주가 3.8% 상승" → "주가 상승"
       - 예: "주가 2.7% 상승" → "주가 상승"
       - 예: "예산 44억 원 증가" → "예산 증가"
       - 예: "2025년 12월 30일 계약" → "대규모 계약" 또는 "계약 체결"
    
    3. **길이 제한**:
       - 각 키워드는 4단어 이내로 제한해라.
       - 너무 짧으면 의미가 불명확하고, 너무 길면 문장이 된다.
    
    4. **중복 통합**:
       - 같은 의미의 다양한 표현은 하나의 핵심 키워드로 통합해라.
       - 예: "주가 상승", "주가 3.8% 상승", "주가 2.7% 상승" → 모두 "주가 상승"으로 통합
       - 예: "예산 증가", "예산 44억 원 증가" → "예산 증가"로 통합
    
    5. **핵심 개념 추출**:
       - 기관명, 구체적 대상, 시간 정보 등 부가 정보는 제거하고, 행위/상태/개념의 본질만 추출해라.
       - 예: "한국전력공사와 234억원 계약" → "대규모 계약"
       - 예: "한국전력 주가 하락 2.58%" → "주가 하락"
       - ⚠️ **중요**: 기관명을 제거할 때 불완전한 표현이 남지 않도록 주의해라.
         - 올바른 예: "한국전력의 주가 상승" → "주가 상승"
         - 잘못된 예: "한국전력의 주가 상승" → "의 주가 상승" (X, 이런 불완전한 표현 금지)
         - 올바른 예: "한국전력과의 협력" → "협력 강화"
         - 잘못된 예: "한국전력과의 협력" → "과의 협력" (X, 이런 불완전한 표현 금지)
    
    6. **형태 유지**:
       - 완전한 문장이 아닌 명사구 또는 동사구 형태로 추출해라.
       - 서술어가 포함된 문장형 표현은 금지한다.
    
    7. **불필요한 키워드 삭제**:
       - 워드클라우드에 적합하지 않거나 의미가 불명확한 키워드는 삭제해도 된다.
       - 너무 길거나 문맥 없이 이해하기 어려운 키워드는 제외해라.
       - 예: "한전 또한 발전, 송전, 변전 등 전력 사업에 목적을 둔 사업자이기 때문에..." 
         → 정제 불가능한 경우 삭제 가능
       - 단, 삭제할 때는 반드시 완전한 키워드만 남기고 불완전한 표현은 남기지 마라.

    ### [출력 형식]
    반드시 아래 JSON 포맷으로만 응답해라. 주석, 설명은 절대 포함하지 마라.
    정제된 키워드만 리스트에 포함하고, 원본 키워드의 순서는 유지할 필요 없다.
    
    **⚠️ 필수 규칙**:
    - 출력되는 모든 키워드는 반드시 원본 키워드 리스트에 있던 키워드를 정제한 것이어야 한다.
    - 원본 키워드 리스트에 없는 새로운 키워드를 절대 추가하지 마라.
    - 기사 내용에서 새로운 키워드를 발견하더라도 출력에 포함하지 마라.

    {{
        "refinedKeywords": ["정제된 키워드1", "정제된 키워드2", ...]
    }}
    """

    # 7. [최종 검수] 한국어 번역 및 검수 (Safety Net)
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

    # 8. [Long Detail Summary Formats] 상세 요약 형식 1~5 (모양만)
    question_longdetail_summary_format1 = ""
    question_longdetail_summary_format2 = ""
    question_longdetail_summary_format3 = ""
    question_longdetail_summary_format4 = ""
    question_longdetail_summary_format5 = ""

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
    
    ###"short_summary": "한줄 기사 요약",
        ##"long_summary": "5줄 이상으로 기사 요약, long_summary는 자세한 정보까지 요약에 포함되어야 해."
       # "category_reason": 반환한 category별로 이유를 설명해줘 dictionary 형태로.
    
    # 추가
    # ~Ratio : 0~1사이의 float 형태로 출력해줘 --> 2025.03.03 최미화 질문 : 왜 넣은거죠? 
    # 2025.03.03 : Prompt 수정, 최미화, 기관 이름이 명확이 추출되도록 수정함 
    # 2025.03.10 : Prompt 수정, 최미화, 긍정키워드, 부정키워드 추출 방법 기술 추가함. 
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
    
    # # 20251013 리자: 프롬프트 3)분리
    # # 원본
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

    # # 옵션 1
    # question_sentiment_ratio = f"""
    # 기사 : [contents]
    # 기관 : [organization] (이 기관은 [synonyms]로도 불립니다.)

    # 너는 기관(organization)에 소속되어 뉴스 기사를 읽고 해당 기관과 관련된 내용의 감성을 분석하는 기업 평판 리스크 분석가야.
    # 기사가 대상 기관에 미칠 영향을 먼저 판단하고, 그에 따라 감성 비율을 계산해줘.

    # ### 기사가 중립적으로 작성됐다고 판단하는 주요 근거
    # - 국민과 대한민국 정부가 기사를 읽고 기관에 대한 인식에 긍정적이나 부정적으로 변하지 않는 경우
    # - 기관의 평판에 영향을 미치지 않는 공고, 일정, 통계, 제도 설명 등


    #     {{
    #         "positiveRatio": "기관에 대해 긍정적으로 작성됐다는 비율 (0~100, float, % 기호 없이)",
    #         "neutralRatio": "기관에 대해 중립적으로 작성됐다는 비율 (0~100, float, % 기호 없이)",
    #         "negativeRatio": "기관에 대해 부정적으로 작성됐다는 비율 (0~100, float, % 기호 없이)"
    #     }}

    #     세 비율의 합은 100이 되어야 해. 주석이나 설명은 넣지 마.
    # """
    
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

    # # 원본    
    # sentiment_reason = f"""

    # 기사 : [contents]
    # 기관 : [organization] (이 기관은 [synonyms]로도 불립니다.)
    
    # 너는 기관(organization)에 소속되어 기사(contents)가 기관(organization)에 긍정, 부정 혹은 중립적인지 분석하는 전문가야.
    # 해당 기관을 대상으로 기사를 분석된 감성 비율은 다음과 같아:
    #     - 긍정: [positiveRatio]
    #     - 부정: [negativeRatio]
    #     - 중립: [neutralRatio]

    # 이 비율을 판단한 이유와 주요 키워드를 작성해줘.
    # 출력은 아래 JSON 형식으로 해.

    # **중요: 모든 문장은 반드시 한국어로만 작성해. 영어 문장을 절대 사용하지 마.**

    # {{
    #     "reason": "긍정과 부정 비율을 종합적으로 판단한 근거 (한 문단)",
    #     "positiveReason": "긍정 비율 판단 근거 (문장 형식)",
    #     "negativeReason": "부정 비율 판단 근거 (문장 형식)",
    #     "neutralReason": "중립 비율 판단 근거 (문장 형식)",
    
    # }}
    
    # """

    # 중립 단어 없는 프롬프트
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

    # sentiment_keywords = f"""
    # 기사 : [contents]
    # 기관 : [organization] (이 기관은 [synonyms]로도 불립니다.)
    
    # 이 기사는 여러 주제를 다룰 수 있지만, 
    #     **오직 해당 기관([organization])의 이미지, 평판, 또는 대중 인식에 영향을 미치는 내용만** 분석해 줘.

    #     기관과 직접적으로 관련된 **긍정적인 요인**, **부정적인 요인**과 **중립적인 요인** 을 찾아 아래 JSON 형식으로 정리해 줘.
    #     단순한 단어나 기사 전반의 키워드가 아니라, 
    #     기관의 평판(이미지)에 영향을 주는 문맥 있는 표현을 뽑아야 해. 
    #     (예: "기술 혁신", "성과 향상", "비리 의혹", "경영 악화" 등)

    #     {{
    #         "positiveKeywords": ["긍정 키워드1", "긍정 키워드2", "긍정 키워드3"],
    #         "negativeKeywords": ["부정 키워드1", "부정 키워드2", "부정 키워드3"],
    #         "neutralKeywords": ["중립 키워드1", "중립 키워드2", "중립 키워드3"]
    #     }}

    #     출력 시:
    #     - JSON만 출력해. 
    #     - 주석, 설명, 문장형 해석은 절대 넣지 마.

    # """

    # # 20251203 프롬프트 수정 중립 X 키워드
    # sentiment_keywords = f"""
    # 기사 : [contents]
    # 기관 : [organization] (이 기관은 [synonyms]로도 불립니다.)
    
    # 이 기사에서 해당 기관과 관련된 내용을 2가지 유형으로 분류해 줘:

    #     [분류 기준]
    #     1. **긍정 키워드**: 기관의 평판/이미지를 '향상'시키는 내용
    #     - 단순하게 키워드 자체가 긍정적인 느낌은 준다고 선택하면 안 돼
    #     - 반드시 키워드가 기사 맥락에서 기관에게 유리하거나 호의적으로 서술된 표현인지 고려해야 돼
    #     - 예: "혁신적 성과", "투명한 운영", "시민 만족도 증가"

    #     2. **부정 키워드**: 기관의 평판/이미지를 '저하'시키는 내용
    #     - 단순하게 키워드가 부정적인 단어라고 선택하면 안 돼
    #     - 반드시 키워드가 기사 맥락에서 기관에게 불리하거나 비판적으로 서술된 표현인지 고려해야 돼
    #     - 예: "부실한 관리", "예산 낭비", "민원 급증"

    #     {{
    #         "positiveKeywords": ["긍정 키워드1", "긍정 키워드2", "긍정 키워드3"],
    #         "negativeKeywords": ["부정 키워드1", "부정 키워드2", "부정 키워드3"],
    #     }}

    #     출력 시:
    #     - JSON만 출력해. 
    #     - 주석, 설명, 문장형 해석은 절대 넣지 마.

    # """
