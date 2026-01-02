# Short Summary2 및 유사도 계산 최적화 통합 문서

> 작성일: 2025-12-22  
> 통합 문서: Short Summary2 최적화 + 유사도 계산 기관명 처리

---

## 📋 목차

1. [Short Summary2 생성 최적화](#1-short-summary2-생성-최적화)
2. [유사도 계산 시 기관명 처리 방안](#2-유사도-계산-시-기관명-처리-방안)
3. [Short Summary2 기반 필터링 접근법](#3-short-summary2-기반-필터링-접근법)

---

## 1. Short Summary2 생성 최적화

### 1.1 문제 분석

**현재 프롬프트의 문제점**:
1. **순차적 처리**: LLM이 `short_summary`를 먼저 생성한 후, 그것을 다시 읽고 처리해야 함
2. **추가 추론**: 기관명 제거, 조사/격 제거 등 추가 작업 필요
3. **프롬프트 길이**: 작업 순서 설명이 길어져 프롬프트가 복잡해짐
4. **처리 시간 증가**: 2단계 작업으로 인해 처리 시간이 약 1.5~2배 증가

### 1.2 최적화 방안

#### 방안 1: 동시 생성 방식 (권장) ⭐⭐⭐⭐⭐

**핵심 아이디어**: `short_summary` 작성 시 동시에 `short_summary2`도 생성

**장점**:
- ✅ 한 번의 추론으로 두 가지 모두 생성
- ✅ 처리 시간 단축 (약 30~50% 감소 예상)
- ✅ 프롬프트 단순화

**수정된 프롬프트**:
```python
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
```

**핵심 변경점**:
- ✅ "작업 순서" 섹션 제거
- ✅ "동시에 작성" 지시로 변경
- ✅ 프롬프트 길이 단축

**예상 효과**:
- **처리 시간**: 약 30~50% 단축
- **프롬프트 길이**: 약 20% 감소
- **정확도**: 유지 (LLM이 문맥 고려)

---

## 2. 유사도 계산 시 기관명 처리 방안

### 2.1 문제 상황

#### 문제 1: 기관명으로 인한 오선택

**시나리오**:
```
short_summary: "한국전력 식당 메뉴 부실"
predefine_keyword: "전력"

유사도 계산:
- "한국전력 식당 메뉴 부실" vs "전력"
- 기관명 "한국전력"에 "전력"이 포함되어 있어 유사도가 높게 나옴
- 결과: "전력" 키워드가 선택됨 (잘못된 선택, 기사 주제는 식당/급식)
```

#### 문제 2: 기관명 제거 시 문맥 손실

**시나리오**:
```
short_summary: "한국전력의 전력망 확충"
predefine_keyword: "전력"

기관명 제거 후:
- "전력망 확충" vs "전력"
- "전력망"이 "전력" 키워드와 유사도가 높아야 함 (문맥적으로 맞음)
- 하지만 기관명을 제거하면 문맥이 손실될 수 있음
```

### 2.2 해결 방안

#### 방안 1: 키워드별 조건부 기관명 제거 (권장)

**핵심 아이디어**: 각 키워드마다 기관명 포함/제거 버전으로 유사도 계산 후 선택

**로직**:
1. 각 키워드에 대해 2가지 유사도 계산:
   - `similarity_with_org`: 기관명 포함 전체 문장과 키워드 유사도
   - `similarity_without_org`: 기관명 제거 후 문장과 키워드 유사도
2. 두 유사도 차이 분석:
   - 차이가 크면 → 기관명 영향이 큼 → 기관명 제거 버전 사용
   - 차이가 작으면 → 기관명 영향이 작음 → 기관명 포함 버전 사용
3. 최종 유사도 선택

**의사코드**:
```python
def calculate_similarity_with_orgname_handling(summary, keyword, org_name, synonyms):
    # 1. 기관명 포함 버전
    similarity_with_org = cosine_similarity(summary, keyword)
    
    # 2. 기관명 제거 버전
    summary_without_org = remove_orgname(summary, org_name, synonyms)
    similarity_without_org = cosine_similarity(summary_without_org, keyword)
    
    # 3. 차이 계산
    diff = abs(similarity_with_org - similarity_without_org)
    
    # 4. 임계값 기반 선택
    threshold = 0.1  # 경험적 값
    if diff > threshold:
        # 기관명 영향이 큼 → 제거 버전 사용
        return similarity_without_org
    else:
        # 기관명 영향이 작음 → 포함 버전 사용
        return similarity_with_org
```

**장점**:
- ✅ 키워드별로 최적의 유사도 선택
- ✅ 문맥 보존과 기관명 영향 제거의 균형
- ✅ 유연한 처리

**단점**:
- ⚠️ 계산량 증가 (각 키워드마다 2번 계산)
- ⚠️ 임계값 설정 필요

#### 방안 4: 키워드-문맥 매칭 점수 (추천)

**핵심 아이디어**: 키워드가 제거 후 문장의 핵심 주제와 관련이 있는지 먼저 확인

**로직**:
1. `short_summary`에서 기관명 제거
2. 제거 후 문장의 핵심 주제 추출 (간단한 키워드 추출 또는 LLM)
3. 각 키워드가 핵심 주제와 관련이 있는지 확인
4. 관련성이 낮으면 유사도 계산에서 제외 또는 페널티 적용

**의사코드**:
```python
def calculate_context_aware_similarity(summary, keywords, org_name, synonyms):
    # 1. 기관명 제거
    summary_without_org = remove_orgname(summary, org_name, synonyms)
    
    # 2. 제거 후 문장의 핵심 주제 추출
    core_topics = extract_core_topics(summary_without_org)
    # 예: "식당 메뉴 부실" → ["식당", "메뉴", "부실"]
    
    # 3. 각 키워드와 핵심 주제의 관련성 확인
    keyword_scores = {}
    for keyword in keywords:
        relevance_score = check_keyword_topic_relevance(keyword, core_topics)
        
        if relevance_score < threshold:
            keyword_scores[keyword] = 0.0
        else:
            similarity = cosine_similarity(summary_without_org, keyword)
            keyword_scores[keyword] = similarity * relevance_score
    
    return keyword_scores
```

**장점**:
- ✅ 문맥 중심 필터링
- ✅ 기관명 영향 제거
- ✅ 핵심 주제와의 관련성 강조

---

## 3. Short Summary2 기반 필터링 접근법

### 3.1 제안 방법

**프로세스**:
1. **short_summary 작성** (기존과 동일)
2. **short_summary2 생성**: short_summary에서 기관명 제거
3. **각 키워드에 대해 유사도 계산**:
   - `similarity_with_org` = short_summary vs 키워드
   - `similarity_without_org` = short_summary2 vs 키워드
4. **유사도 차이 분석**:
   - 차이가 크면 → 기관명 영향이 큼 → 키워드 제거
   - 차이가 작으면 → 기관명 영향이 작음 → 키워드 유지

### 3.2 장점

1. **기존 메소드 재사용**
   - ✅ `best_keyword_of_summary` 메소드를 그대로 사용 가능
   - ✅ 코드 변경 최소화
   - ✅ 구현 간단

2. **명확한 로직**
   - ✅ short_summary2는 한 번만 생성
   - ✅ 각 키워드마다 2번 계산 (포함/제거 버전)
   - ✅ 차이 기반 필터링으로 명확함

3. **실용적**
   - ✅ 추가 LLM 호출 불필요
   - ✅ 계산량이 적절함

### 3.3 시나리오별 예상 결과

| 시나리오 | short_summary | short_summary2 | 키워드 | 유사도(포함) | 유사도(제거) | 차이 | 결과 |
|---------|---------------|----------------|--------|------------|------------|------|------|
| A | "한국전력 식당 메뉴 부실" | "식당 메뉴 부실" | "전력" | 0.65 | 0.15 | 0.50 | 제거 ✅ |
| B | "한국전력의 전력망 확충" | "전력망 확충" | "전력" | 0.70 | 0.68 | 0.02 | 유지 ✅ |
| C | "한국전력과 한국가스공사 협력" | "한국가스공사 협력" | "전력" | 0.60 | 0.20 | 0.40 | 제거 ✅ |
| D | "한국전력 전력 정책 발표" | "전력 정책 발표" | "전력" | 0.75 | 0.72 | 0.03 | 유지 ✅ |

### 3.4 개선 제안

#### 제안 1: 임계값 + 절대값 고려

**로직**:
```python
def filter_keyword_by_similarity_diff(summary, summary2, keyword):
    similarity_with_org = calculate_similarity(summary, keyword)
    similarity_without_org = calculate_similarity(summary2, keyword)
    
    diff = abs(similarity_with_org - similarity_without_org)
    
    # 조건 1: 차이가 크면 제거
    if diff > 0.2:  # 임계값
        return None  # 제거
    
    # 조건 2: 제거 후 유사도가 너무 낮으면 제거
    if similarity_without_org < 0.3:  # 최소 유사도
        return None  # 제거
    
    # 조건 3: 둘 다 만족하면 유지
    return similarity_without_org  # 제거 후 유사도 사용
```

**장점**:
- ✅ 차이뿐만 아니라 절대값도 고려
- ✅ 더 안전한 필터링

#### 제안 2: 기관명 제거 개선

**로직**:
```python
def remove_orgname_improved(summary, org_name, synonyms):
    # 1. 기관명과 동의어 제거
    text = summary
    for name in [org_name] + synonyms:
        # 정규식으로 제거 (단어 경계 고려)
        pattern = r'\b' + re.escape(name) + r'\b'
        text = re.sub(pattern, '', text)
    
    # 2. 조사/격 조정
    text = re.sub(r'\s+의\s+', ' ', text)  # "한국전력의" → 제거
    text = re.sub(r'\s+과\s+', ' ', text)  # "한국전력과" → 제거
    text = re.sub(r'\s+', ' ', text).strip()  # 공백 정리
    
    return text
```

### 3.5 최종 의견

**제안하신 방법은 좋은 접근입니다**

**이유**:
1. ✅ 기존 메소드 재사용 가능
2. ✅ 구현 간단
3. ✅ 대부분의 케이스에서 효과적

**개선이 필요한 부분**:
1. **임계값 설정**
   - 차이 임계값: 0.15 ~ 0.25 권장
   - 제거 후 최소 유사도: 0.3 권장
   - 경험적 조정 필요

2. **기관명 제거 방식**
   - 단순 문자열 제거보다 정규식 기반 제거 권장
   - 조사/격 처리 필요

3. **엣지 케이스 처리**
   - 차이뿐만 아니라 절대값도 고려
   - 제거 후 유사도가 너무 낮으면 제거

### 3.6 권장 구현 방식

```python
def filter_keywords_by_orgname_removal(summary, keywords, org_name, synonyms):
    # 1. short_summary2 생성
    summary2 = remove_orgname_improved(summary, org_name, synonyms)
    
    # 2. 각 키워드에 대해 유사도 계산
    filtered_keywords = {}
    for keyword in keywords:
        sim_with_org = calculate_similarity(summary, keyword)
        sim_without_org = calculate_similarity(summary2, keyword)
        
        diff = abs(sim_with_org - sim_without_org)
        
        # 필터링 조건
        if diff > 0.2 and sim_without_org < 0.3:
            # 기관명 영향이 크고, 제거 후 유사도가 낮음 → 제거
            continue
        else:
            # 유지 (제거 후 유사도 사용)
            filtered_keywords[keyword] = sim_without_org
    
    return filtered_keywords
```

---

## ✅ 결론

### Short Summary2 최적화
- **문제**: 순차적 처리로 인한 시간 증가
- **해결**: **동시 생성 방식** 권장
- **효과**: 처리 시간 30~50% 단축

### 유사도 계산 기관명 처리
- **문제**: 기관명으로 인한 오선택
- **해결**: **Short Summary2 기반 필터링** 또는 **키워드-문맥 매칭**
- **효과**: False Positive 대폭 감소

### 핵심 원칙
1. 기관명 제거 후 문장의 핵심 주제와 키워드의 관련성을 먼저 확인
2. 관련성이 낮으면 유사도 계산에서 제외 또는 페널티
3. 관련성이 있으면 정상적으로 유사도 계산

이렇게 하면 "한국전력 식당 메뉴 부실"에서 "전력" 키워드가 제거되고, "한국전력의 전력망 확충"에서 "전력" 키워드가 유지됩니다.



