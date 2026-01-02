"""
프롬프트 버전 v2 - 현재 사용 중인 프롬프트
===================================================
작성일: 2025-12-05
작성자: Copilot + 리자
참조: analysis_ollama_base.py

이 파일은 analysis_ollama_generate.py의 analysis_main()에서 
실제로 호출되는 프롬프트만 포함합니다.

현재 실행 순서 (5단계):
----------------------
1️⃣ question_verify           → preValidationDuration
2️⃣ question_summary          → summaryAnalysisDuration
3️⃣ question_sentiment_ratio  ┐
4️⃣ sentiment_reason          ├→ sentimentAnalysisDuration (합산)
5️⃣ sentiment_keywords        ┘

실험용 (3단계) - prompts_experimental.py 참조:
----------------------------------------------
1️⃣ question_verify           → preValidationDuration
2️⃣ question_summary          → summaryAnalysisDuration
3️⃣ question_sentiment_all    → sentimentAnalysisDuration

사용법 (오버라이딩):
--------------------
from ksubscribe_share.test.prompts.prompts_v2_current import PromptsCurrent

class CustomAnalysis(AnalysisOllamaGenerateCall):
    def __init__(self):
        super().__init__()
        # 특정 프롬프트만 오버라이딩
        self.question_summary = PromptsCurrent.question_summary
        self.sentiment_reason = PromptsCurrent.sentiment_reason
"""


class PromptsCurrent:
    """현재 운영 중인 프롬프트 (2025-12-05 기준)"""
    
    # ================================================================
    # 1. question_verify - DB키워드와 기사 관련성 검증 + ai_keyword 추출
    # ================================================================
    # 호출순서: 1번째
    # 역할: 
    #   - 기사에서 ai_keyword 추출
    #   - pred_keywords_from_db와 관련성 검증 (related: true/false)
    #   - 관련된 DB키워드 리스트 반환 (reason)
    # 플레이스홀더: [contents], [pred_keywords_from_db]
    
    question_verify = """
[Step 1] 다음 기사(contents)와 db_keyword_list를 제공합니다.
- contents: [contents]
- db_keyword_list: [pred_keywords_from_db]

[Step 2] 아래 요구사항에 따라 JSON 객체로만 답변해 주세요. 출력 시 (\\n, \\r\\n, \\t 등) 특수문자는 모두 제거합니다.

JSON 형식:
{
    "ai_keyword": 기사(contents)에서 주요 이슈나 주제를 추출하여 핵심 키워드를 리스트로 작성합니다. 문맥을 반영한 표현을 사용하세요.
    "db_keyword_list": 제공한 db_keyword_list를 그대로 넣습니다.
    "related": ai_keyword와 db_keyword_list를 비교하여, 1개 이상 의미적으로 관련이 있으면 true, 전혀 관련이 없으면 false로 설정하세요.
    "reason": related가 true일 경우, db_keyword_list 안에서 관련된 최대 10개의 키워드를 선택하여 리스트로 작성하세요.
}

[특별한 규칙]
- reason은 반드시 db_keyword_list 안에서만 선택해야 합니다. (ai_keyword에서 추출하면 절대 안 됩니다)
- 관련된 db_keyword_list 항목이 하나도 없으면, related는 반드시 false로 설정하세요.
- 절대 ai_keyword 항목에서 reason을 뽑지 마세요. db_keyword_list만 사용하세요.

[최종 조건]
- 출력은 반드시 위 JSON 구조를 정확히 따라야 합니다.
- 설명이나 추가 문장 없이 JSON만 출력하세요.
"""

    # ================================================================
    # 2. question_summary - 요약 생성 (짧은 요약 + 긴 요약)
    # ================================================================
    # 호출순서: 2번째
    # 역할: 기관 입장에서 기사 요약
    # 플레이스홀더: [contents], [organization]
    # 참고: pred_keywords_from_db 플레이스홀더는 현재 사용되지 않음

    question_summary = """
    contents : [contents]
    organization : [organization]
    위의 기사를 분석하여 아래 형식에 맞춰 JSON 객체로 응답해줘 (\\n, \\r\\n, \\t 제거). JSON 객체의 구조는 다음과 같아:
    
    **중요: 모든 문장은 반드시 한국어로만 작성해. 영어 문장을 절대 사용하지 마.**
    {
        "short_summary": "한줄 기사 요약",
        "long_summary": "5줄 이상으로 기사 요약, long_summary는 자세한 정보까지 요약에 포함되어야 해. organization을 중심으로 요약해줘."
    }
    """

    # ================================================================
    # 3. question_sentiment_ratio - 감성 비율 추출
    # ================================================================
    # 호출순서: 3번째
    # 역할: 긍정/부정/중립 비율 산출 (합계 = 100)
    # 플레이스홀더: [contents], [organization], [synonyms]

    question_sentiment_ratio = """
    기사 : [contents]
    기관 : [organization] (이 기관은 [synonyms]로도 불립니다.)
    위 기사에서 해당 기관 또는 그 별칭([synonyms])이 언급된 부분을 중심으로 감성 분석을 수행해 줘.
    기관에 대한 언급 중 긍정 / 부정 / 중립의 비율을 추정해서 아래 JSON 형식으로만 답변해.

        {
            "positiveRatio": "기관 언급 중 긍정적 내용의 비율 (0~100, float, % 기호 없이)",
            "neutralRatio": "기관 언급 중 중립적 내용의 비율 (0~100, float, % 기호 없이)",
            "negativeRatio": "기관 언급 중 부정적 내용의 비율 (0~100, float, % 기호 없이)"
        }

        세 비율의 합은 100이 되어야 해. 주석이나 설명은 넣지 마.
    """

    # ================================================================
    # 4. sentiment_reason - 감성 비율 판단 이유 생성
    # ================================================================
    # 호출순서: 4번째 (3번 결과를 입력으로 사용)
    # 역할: 비율 판단 근거 설명 (reason, positiveReason, neutralReason, negativeReason)
    # 플레이스홀더: [contents], [organization], [synonyms], [positiveRatio], [neutralRatio], [negativeRatio]

    sentiment_reason = """
    기사 : [contents]
    기관 : [organization] (이 기관은 [synonyms]로도 불립니다.)
    
    해당 기관을 대상으로 기사를 분석된 감성 비율은 다음과 같아:
        - 긍정: [positiveRatio]
        - 중립: [neutralRatio]
        - 부정: [negativeRatio]

        이 비율을 판단한 이유를 작성해줘.
        출력은 아래 JSON 형식으로 해.

        **중요: 모든 문장은 반드시 한국어로만 작성해. 영어 문장을 절대 사용하지 마.**

        {
            "reason": "긍정, 중립, 부정 비율을 종합적으로 판단한 근거 (한 문단)",
            "positiveReason": "긍정 비율 판단 근거 (문장 형식)",
            "neutralReason": "중립 비율 판단 근거 (문장 형식)",
            "negativeReason": "부정 비율 판단 근거 (문장 형식)"
        }
    """

    # ================================================================
    # 5. sentiment_keywords - 감성 키워드 추출
    # ================================================================
    # 호출순서: 5번째 (3번 결과를 입력으로 사용 가능)
    # 역할: 긍정/부정/중립 키워드 추출
    # 플레이스홀더: [contents], [organization], [synonyms]
    # 중요: 기관의 평판/이미지에 영향을 주는 문맥 있는 표현 추출

    sentiment_keywords = """
    기사 : [contents]
    기관 : [organization] (이 기관은 [synonyms]로도 불립니다.)
    
    이 기사에서 해당 기관과 관련된 내용을 3가지 유형으로 분류해 줘:

        [분류 기준]
        1. **긍정 키워드**: 기관의 평판/이미지를 '향상'시키는 내용
        - 단순하게 키워드 자체가 긍정적인 느낌은 준다고 선택하면 안 돼
        - 반드시 키워드가 기사 맥락에서 기관에게 유리하거나 호의적으로 서술된 표현인지 고려해야 돼
        - 예: "혁신적 성과", "투명한 운영", "시민 만족도 증가"

        2. **부정 키워드**: 기관의 평판/이미지를 '저하'시키는 내용
        - 단순하게 키워드가 부정적인 단어라고 선택하면 안 돼
        - 반드시 키워드가 기사 맥락에서 기관에게 불리하거나 비판적으로 서술된 표현인지 고려해야 돼
        - 예: "부실한 관리", "예산 낭비", "민원 급증"

        3. **중립 키워드**: 기관과 관련되지만 평판에 영향을 주지 않는 사실적 정보
        - 단순 사실, 일정, 통계, 제도 설명 등
        - 예: "10월 1일 시행", "총 3개 부서 운영"

        {
            "positiveKeywords": ["긍정 키워드1", "긍정 키워드2", "긍정 키워드3"],
            "negativeKeywords": ["부정 키워드1", "부정 키워드2", "부정 키워드3"],
            "neutralKeywords": ["중립 키워드1", "중립 키워드2", "중립 키워드3"]
        }

        출력 시:
        - JSON만 출력해. 
        - 주석, 설명, 문장형 해석은 절대 넣지 마.
    """


# ================================================================
# 변경 이력
# ================================================================
# 2025-10-13: 프롬프트 3분리 (ratio, reason, keywords) - 리자
# 2025-12-03: sentiment_keywords에 중립 키워드 추가 - 리자
# 2025-12-05: sentiment_reason에 neutralReason 추가 - Copilot
# 2025-12-05: prompts_v2_current.py로 정리 - Copilot
