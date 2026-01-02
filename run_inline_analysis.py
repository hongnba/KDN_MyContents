#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간이 실행기: MongoDB 없이 첨부된 문서 JSON으로 Ollama 기반 5가지 분석을 실행합니다.
- 외부 DB 모듈을 import 하지 않으므로 parsing-container에 pymongo/bson이 없어도 동작합니다.
- Ollama는 컨테이너 네트워크에서 http://ollama:11434 으로 호출합니다 (프로젝트 기본 설정 사용).

사용법 (이미 제공된 문서 데이터를 하드코딩하여 실행):
    python3 run_inline_analysis.py

작성: AI assistant
"""

import json
import os
import requests
from types import SimpleNamespace
from datetime import datetime
from bs4 import BeautifulSoup
import sys

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
OLLAMA_API = OLLAMA_URL + "/api/generate"

# 이전 llama-3-Korean-Bllossom-8B-Q4_K_M 모델 사용 (주석 처리):
# OLLAMA_MODEL = "llama-3-Korean-Bllossom-8B-Q4_K_M:latest"

# 현재 사용: gpt-oss:20b 모델
OLLAMA_MODEL = "gpt-oss:20b"

# ----- 문서(사용자 제공) -----
queue_doc = {
  "_id": {"$oid": "68edc849ae3da00bfe2d0cf2"},
  "contentOrgId": "A0010",
  "cateId": "B0010",
  "title": "한국전력기술, 생성형 AI 실무·보안 교육으로 디지털 혁신 가속화",
  "url": "http://www.epj.co.kr/news/articleView.html?idxno=37143",
  "shortUrl": "J6Syn",
  "pubDt": {"$date": "2025-10-13T00:00:00Z"},
  "collectKeyword": "한국전력",
  "collectDt": {"$date": "2025-10-14T03:49:29.022Z"}
}

# ----- 프롬프트 템플릿 (간소화 버전, 원본과 내용은 동일한 의도) -----
question_verify = '''[Step 1] 다음 기사(contents)와 db_keyword_list를 제공합니다.\n- contents: [contents]\n- db_keyword_list: [pred_keywords_from_db]\n\n[출력] JSON으로만 응답: {"ai_keyword": [...], "db_keyword_list": [...], "related": true|false, "reason": [...]}\n결과는 JSON만 출력하세요.''' 

question_summary = '''contents : [contents]\norganization : [organization]\n위의 기사를 분석하여 아래 형식에 맞춰 JSON 객체로 응답해줘.\n{\n    "short_summary": "한줄 기사 요약",\n    "long_summary": "5줄 이상으로 기사 요약, organization을 중심으로 요약해줘."\n}'''

question_sentiment_ratio = '''기사 : [contents]\n기관 : [organization] (이 기관은 [synonyms]로도 불립니다.)\n위 기사에서 해당 기관 또는 그 별칭([synonyms])이 언급된 부분을 중심으로 감성 분석을 수행해 줘.\n아래 JSON으로만 응답:\n{ "positiveRatio": "0~100", "neutralRatio": "0~100", "negativeRatio": "0~100" }\n세 비율의 합은 100이어야 합니다.''' 

sentiment_reason = '''기사 : [contents]\n기관 : [organization]\n해당 기관을 대상으로 위에 주어진 비율을 판단한 이유와 주요 키워드를 아래 JSON으로 응답해줘.\n{ "reason": "..", "positiveReason": "..", "negativeReason": ".." }'''

sentiment_keywords = '''기사 : [contents]\n기관 : [organization]\n기관의 이미지/평판과 관련된 긍정적/부정적 요인을 찾아 아래 JSON으로 응답하세요.\n{ "positiveKeywords": [..], "negativeKeywords": [..] }'''

# ----- 헬퍼 함수 -----

def fetch_article_text(url):
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"[WARN] URL fetch failed: {e}")
        return None
    # 간단한 HTML->텍스트 추출
    soup = BeautifulSoup(resp.text, "html.parser")
    # remove scripts/styles
    for s in soup(["script", "style", "noscript"]):
        s.extract()
    texts = [t.get_text(separator=" ") for t in soup.find_all(['p','div','article','span','h1','h2','h3'])]
    body = "\n".join(t.strip() for t in texts if t and len(t.strip())>20)
    # fallback: whole text
    if not body or len(body) < 200:
        body = soup.get_text(separator=" ")
    return body


def call_ollama(prompt, model=OLLAMA_MODEL, max_tokens=512, stop=None):
    payload = {
        "model": model,
        "prompt": prompt,
        "max_tokens": max_tokens
    }
    try:
        r = requests.post(OLLAMA_API, json=payload, timeout=60)
        r.raise_for_status()
    except Exception as e:
        return False, f"HTTP error: {e}"
    # Ollama may return JSON or text; try JSON first
    try:
        data = r.json()
        # Common shapes: {'output': '...', 'text': '...'} or {'choices':[{'text':...}]}
        if isinstance(data, dict):
            # try common keys
            text = None
            if 'text' in data:
                text = data['text']
            elif 'output' in data:
                text = data['output']
            elif 'choices' in data and isinstance(data['choices'], list) and len(data['choices'])>0:
                first = data['choices'][0]
                text = first.get('text') or first.get('message') or str(first)
            else:
                # last resort: full json as string
                text = json.dumps(data, ensure_ascii=False)
            return True, text
        else:
            return True, str(data)
    except ValueError:
        # not json
        return True, r.text


def safe_json_parse(s):
    if not s:
        return None
    # strip leading/trailing whitespace and attempts to extract JSON substring
    s = s.strip()
    # If the model returned extraneous text, try to find first '{' and last '}'
    try:
        start = s.index('{')
        end = s.rindex('}')
        candidate = s[start:end+1]
        return json.loads(candidate)
    except Exception:
        try:
            return json.loads(s)
        except Exception:
            return None


# ----- 실행 흐름 -----

def run():
    print("Inline analysis start")
    url = queue_doc.get('url')
    title = queue_doc.get('title')
    collect_kw = queue_doc.get('collectKeyword')
    org = queue_doc.get('contentOrgId')

    print(f"Document: {title} ({url})")

    contents = fetch_article_text(url)
    if not contents:
        print("Failed to fetch article text; aborting")
        sys.exit(1)

    # Prepare pred_keywords list (use collectKeyword as single db keyword)
    pred_keywords_db = [collect_kw] if collect_kw else []

    # 1) Verify
    p_verify = question_verify.replace('[contents]', contents[:2000]).replace('[pred_keywords_from_db]', json.dumps(pred_keywords_db, ensure_ascii=False))
    ok, resp = call_ollama(p_verify, max_tokens=300)
    print('\n== Verify raw response ==')
    print(resp)
    verify_json = safe_json_parse(resp)
    print('\n== Verify parsed JSON ==')
    print(json.dumps(verify_json, ensure_ascii=False, indent=2))

    # 2) Summary
    p_summary = question_summary.replace('[contents]', contents[:4000]).replace('[organization]', org if org else "")
    ok, resp = call_ollama(p_summary, max_tokens=512)
    print('\n== Summary raw response ==')
    print(resp)
    summary_json = safe_json_parse(resp)
    print('\n== Summary parsed JSON ==')
    print(json.dumps(summary_json, ensure_ascii=False, indent=2))

    # 3) Sentiment ratio
    p_sent = question_sentiment_ratio.replace('[contents]', contents[:4000]).replace('[organization]', collect_kw if collect_kw else "").replace('[synonyms]', "")
    ok, resp = call_ollama(p_sent, max_tokens=300)
    print('\n== Sentiment ratio raw response ==')
    print(resp)
    sent_json = safe_json_parse(resp)
    print('\n== Sentiment ratio parsed JSON ==')
    print(json.dumps(sent_json, ensure_ascii=False, indent=2))

    # 4) Sentiment reason (uses sent_json values if available)
    positive = negative = None
    if sent_json:
        positive = sent_json.get('positiveRatio') or (sent_json.get('sentiments') and sent_json['sentiments'][0].get('positiveRatio')) if isinstance(sent_json, dict) else None
        negative = sent_json.get('negativeRatio') or (sent_json.get('sentiments') and sent_json['sentiments'][0].get('negativeRatio')) if isinstance(sent_json, dict) else None
    pr_str = f"[positiveRatio]={positive}, [negativeRatio]={negative}"
    p_reason = sentiment_reason.replace('[contents]', contents[:3000]).replace('[organization]', collect_kw if collect_kw else '').replace('[positiveRatio]', str(positive) if positive else '').replace('[negativeRatio]', str(negative) if negative else '')
    ok, resp = call_ollama(p_reason, max_tokens=400)
    print('\n== Sentiment reason raw response ==')
    print(resp)
    reason_json = safe_json_parse(resp)
    print('\n== Sentiment reason parsed JSON ==')
    print(json.dumps(reason_json, ensure_ascii=False, indent=2))

    # 5) Sentiment keywords
    p_keys = sentiment_keywords.replace('[contents]', contents[:3000]).replace('[organization]', collect_kw if collect_kw else '')
    ok, resp = call_ollama(p_keys, max_tokens=300)
    print('\n== Sentiment keywords raw response ==')
    print(resp)
    keys_json = safe_json_parse(resp)
    print('\n== Sentiment keywords parsed JSON ==')
    print(json.dumps(keys_json, ensure_ascii=False, indent=2))

    print('\nInline analysis finished')


if __name__ == '__main__':
    run()
