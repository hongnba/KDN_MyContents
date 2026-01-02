"""
프롬프트 모듈 패키지 초기화
===================================================

이 패키지는 analysis_ollama_base.py의 프롬프트를 
체계적으로 관리하기 위한 모듈입니다.

구조:
-----
prompts/
├── __init__.py              # 이 파일
├── prompt_ver_1.json        # 기존 JSON 형식 프롬프트 (레거시)
├── prompts_v2_current.py    # 현재 운영 중인 프롬프트
├── prompts_legacy.py        # 미사용/레거시 프롬프트
└── prompts_experimental.py  # 실험용 프롬프트 (비율+키워드 통합)

사용법:
------
# 현재 프롬프트 사용
from ksubscribe_share.test.prompts import PromptsCurrent
print(PromptsCurrent.question_summary)

# 레거시 프롬프트 참조
from ksubscribe_share.test.prompts import PromptsLegacy
print(PromptsLegacy.question_sentiment)

# 실험용 프롬프트
from ksubscribe_share.test.prompts import PromptsExperimental
print(PromptsExperimental.question_sentiment_ratio_keywords)

오버라이딩 예시:
---------------
from ksubscribe_server.analysis.analysis_ollama_generate import AnalysisOllamaGenerateCall
from ksubscribe_share.test.prompts import PromptsCurrent

class CustomAnalysis(AnalysisOllamaGenerateCall):
    def __init__(self):
        super().__init__()
        # 특정 프롬프트만 변경
        self.question_summary = '''
        contents : [contents]
        organization : [organization]
        커스텀 요약 프롬프트...
        '''
        # 또는 다른 버전 사용
        self.sentiment_keywords = PromptsCurrent.sentiment_keywords

프롬프트 버전 히스토리:
---------------------
- v1: 통합 프롬프트 (question, question_sentiment) - 현재 미사용
- v2: 분리 프롬프트 (verify, summary, ratio, reason, keywords) - 현재 사용 중
  - 2025-10-13: 3분리 방식 도입 (리자)
  - 2025-12-03: sentiment_keywords에 중립 키워드 추가
  - 2025-12-05: sentiment_reason에 neutralReason 추가
"""

# 현재 운영 중인 프롬프트
from .prompts_v2_current import PromptsCurrent

# 레거시/미사용 프롬프트
from .prompts_legacy import PromptsLegacy, PromptsTestVersions

# 실험용 프롬프트
from .prompts_experimental import PromptsExperimental

__all__ = [
    'PromptsCurrent',
    'PromptsLegacy', 
    'PromptsTestVersions',
    'PromptsExperimental'
]

# 버전 정보
__version__ = '2.0.0'
__updated__ = '2025-12-05'
