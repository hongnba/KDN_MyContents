"""
프롬프트 실험용 버전 - 감성분석 통합 프롬프트
===================================================
작성일: 2025-12-05
수정일: 2025-12-05
작성자: Copilot + 리자

이 파일은 감성분석 관련 프롬프트를 통합하여 
호출 횟수를 줄이고 일관성을 보장하는 실험용 프롬프트를 포함합니다.

버전 비교:
----------
[기존 방식 - 5단계]
1️⃣ question_verify           → preValidationDuration
2️⃣ question_summary          → summaryAnalysisDuration  
3️⃣ question_sentiment_ratio  ┐
4️⃣ sentiment_reason          ├→ sentimentAnalysisDuration
5️⃣ sentiment_keywords        ┘

[4단계 통합 - ratio + keywords]
1️⃣ question_verify                    → preValidationDuration
2️⃣ question_summary                   → summaryAnalysisDuration
3️⃣ question_sentiment_ratio_keywords  ┐
4️⃣ sentiment_reason                   ├→ sentimentAnalysisDuration
                                       ┘

[3단계 통합 - ratio + keywords + reason] ★ 최종 목표
1️⃣ question_verify                    → preValidationDuration
2️⃣ question_summary                   → summaryAnalysisDuration
3️⃣ question_sentiment_all             → sentimentAnalysisDuration

장점: 호출 횟수 감소 (5회 → 3회), 비율-키워드-이유 간 일관성 보장
단점: 프롬프트 복잡도 증가, 응답 품질 모니터링 필요
"""


class PromptsExperimental:
    """실험용 프롬프트 - 비율+키워드 통합"""
    
    # ================================================================
    # question_sentiment_ratio_keywords - 비율과 키워드 통합 추출
    # ================================================================
    # 목적: 비율과 키워드 간 일관성 보장
    # 규칙:
    #   - 비율 > 0 → 반드시 해당 키워드 1개 이상 추출
    #   - 키워드는 반드시 해당 기관이 주어인 문장에서만 추출
    #   - relevance (관련도): 키워드가 기관에 얼마나 직접적으로 관련되는지 0~100
    # 플레이스홀더: [contents], [organization], [synonyms]
    
    question_sentiment_ratio_keywords = """
    기사 : [contents]
    기관 : [organization] (이 기관은 [synonyms]로도 불립니다.)
    
    위 기사에서 해당 기관 또는 그 별칭이 언급된 부분을 중심으로 감성 분석을 수행해 줘.
    
    **핵심 규칙:**
    1. 비율(Ratio)과 키워드(Keywords)는 반드시 일치해야 해:
       - positiveRatio > 0 이면, positiveKeywords에 해당하는 표현을 모두 추출해
       - neutralRatio > 0 이면, neutralKeywords에 해당하는 표현을 모두 추출해
       - negativeRatio > 0 이면, negativeKeywords에 해당하는 표현을 모두 추출해
       - Ratio = 0 이면, 해당 Keywords는 빈 리스트 []
    
    2. 키워드 추출 시 **기관이 주어인 문장**에서만 추출해:
       - ✅ "한전이 신재생에너지 사업을 확대한다" → 한전 기준 긍정
       - ❌ "정부가 한전에 압박을 가했다" → 정부가 주어이므로 제외
       - ❌ "삼성이 혁신을 이끌었다" → 다른 기관이 주어이므로 제외
    
    3. 키워드에는 relevance(관련도) 점수를 포함해:
       - 0~100 사이 값
       - 기관과 직접 관련될수록 높은 점수
    
    아래 JSON 형식으로만 응답해:

    {
        "positiveRatio": 긍정 비율 (0~100, float),
        "neutralRatio": 중립 비율 (0~100, float),
        "negativeRatio": 부정 비율 (0~100, float),
        "positiveKeywords": [
            {"keyword": "긍정 표현1", "relevance": 관련도점수},
            {"keyword": "긍정 표현2", "relevance": 관련도점수}
        ],
        "neutralKeywords": [
            {"keyword": "중립 표현1", "relevance": 관련도점수}
        ],
        "negativeKeywords": [
            {"keyword": "부정 표현1", "relevance": 관련도점수}
        ]
    }

    세 비율의 합은 100이어야 해. 주석이나 설명은 넣지 마.
    """

    # ================================================================
    # question_sentiment_ratio_keywords_simple - 단순화 버전
    # ================================================================
    # relevance 없이 키워드만 추출하는 단순화 버전
    
    question_sentiment_ratio_keywords_simple = """
    기사 : [contents]
    기관 : [organization] (이 기관은 [synonyms]로도 불립니다.)
    
    위 기사에서 해당 기관에 대한 감성을 분석해 줘.
    
    **중요 규칙:**
    1. 비율이 0보다 크면 반드시 해당 키워드를 추출해야 해 (빈 리스트 금지)
    2. 키워드는 해당 기관이 주어/목적어로 언급된 문장에서만 추출해
    3. 다른 기관(정부, 타사 등)이 주어인 문장의 키워드는 제외해
    
    JSON 형식:
    {
        "positiveRatio": 0~100,
        "neutralRatio": 0~100,
        "negativeRatio": 0~100,
        "positiveKeywords": ["긍정표현1", "긍정표현2"],
        "neutralKeywords": ["중립표현1", "중립표현2"],
        "negativeKeywords": ["부정표현1", "부정표현2"]
    }
    
    세 비율의 합은 100. JSON만 출력해.
    """

    # ================================================================
    # question_sentiment_all - 비율 + 키워드 + 이유 완전 통합 (3단계용)
    # ================================================================
    # 목적: 감성분석을 단일 호출로 완료
    # 호출순서: 3번째 (마지막)
    # 장점: 
    #   - 호출 횟수 감소 (5회 → 3회)
    #   - 비율-키워드-이유 간 완전한 일관성 보장
    # 단점:
    #   - 프롬프트 복잡도 증가
    #   - 응답 길이 증가 → 토큰 비용 증가
    #   - 일부 필드 누락 가능성
    # 플레이스홀더: [contents], [organization], [synonyms]
    
    question_sentiment_all = """
    기사 : [contents]
    기관 : [organization] (이 기관은 [synonyms]로도 불립니다.)
    
    위 기사에서 해당 기관에 대한 **감성 분석**을 수행해 줘.
    다음 3가지를 한 번에 분석해야 해:
    
    ═══════════════════════════════════════════════════════════════
    [STEP 1] 감성 비율 분석
    ═══════════════════════════════════════════════════════════════
    - 기관에 대한 긍정/중립/부정 비율을 0~100 사이 값으로 산출해
    - 세 비율의 합은 반드시 100이어야 해
    
    ═══════════════════════════════════════════════════════════════
    [STEP 2] 감성 키워드 추출
    ═══════════════════════════════════════════════════════════════
    **핵심 규칙:**
    1. 비율 > 0 이면, 해당 키워드를 반드시 1개 이상 추출해
    2. 비율 = 0 이면, 해당 키워드는 빈 리스트 []
    3. 키워드는 **해당 기관이 주어인 문장**에서만 추출해:
       - ✅ "한전이 신재생에너지 사업을 확대한다" → 한전 기준 긍정
       - ❌ "정부가 한전에 압박을 가했다" → 정부가 주어이므로 제외
       - ❌ "삼성이 혁신을 이끌었다" → 다른 기관이므로 제외
    
    [키워드 분류 기준]
    - **긍정**: 기관 평판/이미지를 '향상'시키는 표현
    - **중립**: 기관과 관련되지만 평판에 영향 없는 사실적 정보
    - **부정**: 기관 평판/이미지를 '저하'시키는 표현
    
    ═══════════════════════════════════════════════════════════════
    [STEP 3] 판단 이유 작성
    ═══════════════════════════════════════════════════════════════
    - STEP 1에서 산출한 비율의 판단 근거를 한국어 문장으로 작성해
    - 각 비율(긍정/중립/부정)별로 이유를 명시해
    
    **중요: 모든 문장은 반드시 한국어로만 작성해.**
    
    ═══════════════════════════════════════════════════════════════
    [출력 형식] JSON만 출력, 주석/설명 금지
    ═══════════════════════════════════════════════════════════════
    {
        "positiveRatio": 긍정 비율 (0~100, float),
        "neutralRatio": 중립 비율 (0~100, float),
        "negativeRatio": 부정 비율 (0~100, float),
        "positiveKeywords": ["긍정 키워드1", "긍정 키워드2"],
        "neutralKeywords": ["중립 키워드1", "중립 키워드2"],
        "negativeKeywords": ["부정 키워드1", "부정 키워드2"],
        "reason": "긍정/중립/부정 비율을 종합적으로 판단한 근거 (한 문단)",
        "positiveReason": "긍정 비율 판단 근거",
        "neutralReason": "중립 비율 판단 근거",
        "negativeReason": "부정 비율 판단 근거"
    }
    """

    # ================================================================
    # question_sentiment_all_with_relevance - 관련도 점수 포함 버전
    # ================================================================
    # relevance 점수를 포함한 상세 버전
    
    question_sentiment_all_with_relevance = """
    기사 : [contents]
    기관 : [organization] (이 기관은 [synonyms]로도 불립니다.)
    
    위 기사에서 해당 기관에 대한 **감성 분석**을 수행해 줘.
    
    **핵심 규칙:**
    1. 비율(Ratio) > 0 이면 반드시 해당 키워드를 1개 이상 추출
    2. 키워드는 해당 기관이 주어인 문장에서만 추출
    3. 각 키워드에 relevance(관련도) 점수 0~100 포함
    4. 판단 이유는 한국어로 작성
    
    **중요: 모든 문장은 반드시 한국어로만 작성해.**
    
    JSON 형식:
    {
        "positiveRatio": 0~100,
        "neutralRatio": 0~100,
        "negativeRatio": 0~100,
        "positiveKeywords": [
            {"keyword": "긍정표현", "relevance": 관련도점수}
        ],
        "neutralKeywords": [
            {"keyword": "중립표현", "relevance": 관련도점수}
        ],
        "negativeKeywords": [
            {"keyword": "부정표현", "relevance": 관련도점수}
        ],
        "reason": "종합 판단 근거",
        "positiveReason": "긍정 비율 근거",
        "neutralReason": "중립 비율 근거",
        "negativeReason": "부정 비율 근거"
    }
    
    세 비율의 합은 100. JSON만 출력.
    """


# ================================================================
# 실행 순서 비교 (업데이트)
# ================================================================
"""
[기존 방식 - 5단계]
1️⃣ question_verify           → preValidationDuration
2️⃣ question_summary          → summaryAnalysisDuration
3️⃣ question_sentiment_ratio  ┐
4️⃣ sentiment_reason          ├→ sentimentAnalysisDuration (합산)
5️⃣ sentiment_keywords        ┘

[4단계 통합 방식]
1️⃣ question_verify                    → preValidationDuration
2️⃣ question_summary                   → summaryAnalysisDuration
3️⃣ question_sentiment_ratio_keywords  ┐
4️⃣ sentiment_reason                   ├→ sentimentAnalysisDuration (합산)
                                       ┘

[3단계 통합 방식] ★ 권장
1️⃣ question_verify           → preValidationDuration
2️⃣ question_summary          → summaryAnalysisDuration
3️⃣ question_sentiment_all    → sentimentAnalysisDuration

시간 측정 필드 (3단계 방식):
- preValidationDuration: 검증 소요시간
- summaryAnalysisDuration: 요약 소요시간
- sentimentAnalysisDuration: 감성분석 소요시간 (비율+키워드+이유 통합)
- totalProcessingDuration: 전체 처리시간 (scraping 포함)
"""

# ================================================================
# 오버라이딩 예시 코드 (3단계 방식)
# ================================================================
"""
사용법:
------
from ksubscribe_share.test.prompts.prompts_experimental import PromptsExperimental
from ksubscribe_server.analysis.analysis_ollama_generate import AnalysisOllamaGenerateCall
import time

class ExperimentalAnalysis3Step(AnalysisOllamaGenerateCall):
    '''3단계 감성분석 통합 버전'''
    
    def __init__(self):
        super().__init__()
        # 통합 프롬프트 설정
        self.question_sentiment_all = PromptsExperimental.question_sentiment_all
    
    def analysis_main_3step(self, content, pred_keyword_list, org_name_list, mycontents_logger, queueContent):
        '''
        3단계 analysis_main - 감성분석 완전 통합 버전
        
        실행 순서:
        1️⃣ question_verify        → 검증 + ai_keyword 추출
        2️⃣ question_summary       → 요약 생성
        3️⃣ question_sentiment_all → 비율 + 키워드 + 이유 통합
        '''
        
        # 1️⃣ 검증
        verify_start = time.time()
        # ... question_verify 호출 ...
        verify_end = time.time()
        
        # 2️⃣ 요약
        summary_start = time.time()
        # ... question_summary 호출 ...
        summary_end = time.time()
        
        # 3️⃣ 감성분석 통합 (비율 + 키워드 + 이유)
        sentiment_start = time.time()
        # ... question_sentiment_all 호출 ...
        # 응답에서 positiveRatio, neutralRatio, negativeRatio,
        #          positiveKeywords, neutralKeywords, negativeKeywords,
        #          reason, positiveReason, neutralReason, negativeReason 추출
        sentiment_end = time.time()
        
        # 시간 기록 (기존 generate_excel_report.py와 100% 호환)
        durations = {
            'preValidationDuration': verify_end - verify_start,
            'summaryAnalysisDuration': summary_end - summary_start,
            'sentimentAnalysisDuration': sentiment_end - sentiment_start,
            # totalProcessingDuration은 scraping 포함하여 상위에서 계산
        }
        return durations


# 응답 검증 함수 (필수 필드 체크)
def validate_sentiment_all_response(response_json):
    '''
    question_sentiment_all 응답의 필수 필드 검증
    Returns: (is_valid, missing_fields)
    '''
    required_fields = [
        'positiveRatio', 'neutralRatio', 'negativeRatio',
        'positiveKeywords', 'neutralKeywords', 'negativeKeywords',
        'reason', 'positiveReason', 'neutralReason', 'negativeReason'
    ]
    
    missing = [f for f in required_fields if f not in response_json]
    
    # 비율-키워드 일관성 검증
    consistency_errors = []
    for sentiment in ['positive', 'neutral', 'negative']:
        ratio = response_json.get(f'{sentiment}Ratio', 0)
        keywords = response_json.get(f'{sentiment}Keywords', [])
        
        if ratio > 0 and (not keywords or len(keywords) == 0):
            consistency_errors.append(f'{sentiment}Ratio > 0 but {sentiment}Keywords is empty')
    
    is_valid = len(missing) == 0 and len(consistency_errors) == 0
    return is_valid, missing, consistency_errors
"""
