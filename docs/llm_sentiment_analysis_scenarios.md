# LLM 감성 분석 고도화 시나리오 및 구현 가이드

이 문서는 LLM의 감성 분석(비율)과 키워드 추출 간의 정합성을 높이기 위한 3가지 시나리오(C, B, A)의 구현 방법을 설명합니다.
특히 **시나리오 C (비율 & 근거 주입)** 방식을 권장하며, 이를 최우선으로 상세히 기술합니다.

---

## 🎯 시나리오 C: 비율 & 근거 기반 키워드 추출 (권장)
> **"왜 10%인지 이유를 알려줄게, 그 이유에 해당하는 단어를 찾아."**
>
> 앞 단계에서 분석한 **감성 비율(Ratio)**과 **판단 근거(Reason)**를 키워드 추출 프롬프트의 입력값(Context)으로 제공하여, LLM이 엉뚱한 키워드를 뽑거나 누락하는 것을 방지합니다.

### 1. `analysis_ollama_base.py` (프롬프트 정의)

기존의 독립적인 키워드 추출 프롬프트 대신, 비율과 근거를 입력받는 새로운 프롬프트를 정의합니다.

```python
class AnalysisOllamaBase:
    # ... 기존 코드 ...

    # [시나리오 C] 키워드 추출용 프롬프트 (비율 + 근거 주입)
    question_sentiment_keywords_with_context = f"""
    기사 : [contents]
    기관 : [organization] (이 기관은 [synonyms]로도 불립니다.)
    
    [분석 컨텍스트]
    이 기사는 해당 기관에 대해 다음과 같이 분석되었습니다:
    - 긍정 비율: [positiveRatio] (근거: [positiveReason])
    - 부정 비율: [negativeRatio] (근거: [negativeReason])
    - 중립 비율: [neutralRatio] (근거: [neutralReason])

    위 분석 결과와 근거(Reason)에 부합하는 구체적인 단어나 표현을 기사 본문에서 찾아주세요.
    
    [분류 기준]
    1. **긍정 키워드**: 위 '긍정 근거'를 뒷받침하는 구체적 표현 (예: "혁신적 성과", "수상")
    2. **부정 키워드**: 위 '부정 근거'를 뒷받침하는 구체적 표현 (예: "예산 낭비", "비판")
    3. **중립 키워드**: 위 '중립 근거'에 해당하는 사실적 정보 (예: "10월 개최", "참석")

    만약 특정 감성의 비율이 0이거나 근거가 없다면, 해당 키워드 리스트는 비워두세요.

    {{
        "positiveKeywords": ["키워드1", "키워드2"],
        "negativeKeywords": ["키워드1", "키워드2"],
        "neutralKeywords": ["키워드1", "키워드2"]
    }}

    출력 시:
    - JSON만 출력해. 
    - 주석, 설명, 문장형 해석은 절대 넣지 마.
    """
```

### 2. `analysis_ollama_generate.py` (로직 수정)

`analysis_main` 또는 `analysis_main_3step` 메서드에서 실행 순서를 조정하고 데이터를 주입합니다.

```python
    def analysis_main_scenario_c(self, content, pred_keyword_list, org_name_list, mycontents_logger, queueContent):
        # ... (검증 및 요약 단계 생략) ...

        # [Step 1] 감성 비율 및 근거 분석 (기존 프롬프트 활용)
        # question_sentiment_ratio 또는 question_sentiment_all 사용
        ratio_prompt = self.question_sentiment_ratio.replace("[contents]", content).replace("[organization]", orgName)
        result_ratio = self.chat_ollama.generate(ratio_prompt)
        ratio_json = self.json_load(result_ratio) # {"positiveRatio": 70, ...}

        # [Step 2] 근거(Reason) 생성 (만약 Step 1에서 Reason이 안 나온다면 별도 호출 필요)
        reason_prompt = self.sentiment_reason.replace("[contents]", content)\
                                             .replace("[positiveRatio]", str(ratio_json['positiveRatio']))\
                                             .replace("[negativeRatio]", str(ratio_json['negativeRatio']))
        result_reason = self.chat_ollama.generate(reason_prompt)
        reason_json = self.json_load(result_reason) # {"positiveReason": "...", ...}

        # [Step 3] 키워드 추출 (Context 주입)
        keyword_prompt = self.question_sentiment_keywords_with_context\
            .replace("[contents]", content)\
            .replace("[organization]", orgName)\
            .replace("[positiveRatio]", str(ratio_json.get('positiveRatio', 0)))\
            .replace("[negativeRatio]", str(ratio_json.get('negativeRatio', 0)))\
            .replace("[neutralRatio]", str(ratio_json.get('neutralRatio', 0)))\
            .replace("[positiveReason]", reason_json.get('positiveReason', ''))\
            .replace("[negativeReason]", reason_json.get('negativeReason', ''))\
            .replace("[neutralReason]", reason_json.get('neutralReason', ''))

        result_keywords = self.chat_ollama.generate(keyword_prompt)
        keywords_json = self.json_load(result_keywords)

        # [Step 4] 결과 조립 (VO 매핑)
        # assemble_sentiment_to_ollamaModel_v2 등 활용
```

---

## 🧪 시나리오 B: 비율 기반 키워드 추출
> **"앞에서 10%라고 했으니, 그에 맞는 키워드를 찾아내라."**
>
> 근거(Reason)까지는 주지 않고, 수치(Ratio)만 힌트로 제공하여 구현을 단순화한 방식입니다.

### 1. `analysis_ollama_base.py`

```python
class AnalysisOllamaBase:
    # ...
    
    # [시나리오 B] 키워드 추출용 프롬프트 (비율만 주입)
    question_sentiment_keywords_with_ratio = f"""
    기사 : [contents]
    기관 : [organization]
    
    [분석 힌트]
    이 기사의 감성 비율은 다음과 같습니다:
    - 긍정: [positiveRatio]%
    - 부정: [negativeRatio]%
    - 중립: [neutralRatio]%

    위 비율을 참고하여, 각 감성을 대표하는 키워드를 추출해주세요.
    비율이 0%인 감성은 키워드를 추출하지 마세요.
    
    {{
        "positiveKeywords": [...],
        "negativeKeywords": [...],
        "neutralKeywords": [...]
    }}
    """
```

### 2. `analysis_ollama_generate.py`

```python
    # ... (Step 1 비율 분석 완료 후) ...
    
    # [Step 2] 키워드 추출 (비율만 주입)
    keyword_prompt = self.question_sentiment_keywords_with_ratio\
        .replace("[contents]", content)\
        .replace("[organization]", orgName)\
        .replace("[positiveRatio]", str(ratio_json.get('positiveRatio', 0)))\
        .replace("[negativeRatio]", str(ratio_json.get('negativeRatio', 0)))\
        .replace("[neutralRatio]", str(ratio_json.get('neutralRatio', 0)))
    
    # ... (이후 동일)
```

---

## 🏗️ 시나리오 A: Bottom-Up (키워드 → 비율 역산출)
> **"키워드가 없으면 비율도 없다."**
>
> LLM은 키워드 추출과 그룹핑만 담당하고, 비율 계산은 Python 코드가 수행합니다.

### 1. `analysis_ollama_base.py`

```python
class AnalysisOllamaBase:
    # ...
    
    # [시나리오 A] 키워드 추출 및 그룹핑 프롬프트
    question_keywords_grouping = f"""
    기사 : [contents]
    기관 : [organization]
    
    이 기사에서 기관의 평판과 관련된 모든 키워드를 추출하고, 의미가 유사한 키워드는 하나로 묶어서 횟수를 세어주세요.
    
    {{
        "positive_groups": {{"혁신": 3, "수상": 1}},  // 예시: '기술 혁신', '혁신적' -> '혁신'으로 통합
        "negative_groups": {{"비판": 2}},
        "neutral_groups": {{"개최": 1}}
    }}
    """
```

### 2. `analysis_ollama_generate.py`

```python
    def analysis_main_scenario_a(self, ...):
        # [Step 1] 키워드 그룹핑 추출
        prompt = self.question_keywords_grouping.replace("[contents]", content)
        result = self.chat_ollama.generate(prompt)
        data = self.json_load(result)
        
        # [Step 2] Python으로 비율 계산
        pos_count = sum(data.get('positive_groups', {}).values())
        neg_count = sum(data.get('negative_groups', {}).values())
        neu_count = sum(data.get('neutral_groups', {}).values())
        
        total = pos_count + neg_count + neu_count
        
        if total > 0:
            pos_ratio = (pos_count / total) * 100
            neg_ratio = (neg_count / total) * 100
            neu_ratio = (neu_count / total) * 100
        else:
            pos_ratio, neg_ratio, neu_ratio = 0, 0, 0
            
        # [Step 3] VO 저장
        # 계산된 ratio와 추출된 keys()를 리스트로 변환하여 저장
```

---

## 📝 요약 및 비교

| 시나리오 | 특징 | 장점 | 단점 |
| :--- | :--- | :--- | :--- |
| **C (권장)** | **비율 + 근거** 주입 | 정합성 높음, 설명력(Why) 강화 | 입력 토큰 증가, 구현 복잡도 약간 상승 |
| **B** | **비율**만 주입 | 구현 간단, 최소한의 가이드 제공 | 근거가 없어 엉뚱한 단어 추출 가능성 존재 |
| **A** | **키워드** 기반 계산 | 수치적 정확성 100% (키워드 없으면 0%) | LLM의 그룹핑 능력에 의존 (20B 모델 한계 가능성) |
