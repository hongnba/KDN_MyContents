#!/usr/bin/env python3
"""
quick_eval_yonhap.py

Fetch a given URL (Yonhap) and send a summary prompt to Ollama using langchain_ollama.
This script is intended to be executed inside the ksubscribe_python_unified container where
the project code and langchain_ollama are available.

Usage: python3 /app/docker_shell/quick_eval_yonhap.py
"""
import json
import traceback
import requests
from bs4 import BeautifulSoup
from langchain_ollama import ChatOllama
import ksubscribe_share.config as CONF

URL = 'https://www.yna.co.kr/view/AKR20251021023400003'

def extract_text(url):
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')
    # try common selectors
    selectors = ['div#articleText', 'div.article', 'div#content', 'article', 'div#article', 'div.articles']
    txt = ''
    for s in selectors:
        node = soup.select_one(s)
        if node:
            paras = [p.get_text(strip=True) for p in node.find_all('p')]
            txt = '\n'.join([p for p in paras if p])
            if txt:
                break
    if not txt:
        # fallback: join many <p>
        paras = [p.get_text(strip=True) for p in soup.find_all('p')]
        txt = '\n'.join([p for p in paras if p])
    return txt

def main():
    try:
        print('Fetching URL:', URL)
        article = extract_text(URL)
        if not article:
            print('No article text extracted')
            return
        print('Article length:', len(article))

        prompt = (
            'contents : ' + article[:4000]
            + '\norganization : 한국전력공사'
            + "\n위의 기사를 분석하여 아래 형식에 맞춰 JSON 객체로 응답해줘."
            + "\n{\n  \"short_summary\": \"한줄 기사 요약\",\n  \"long_summary\": \"5줄 이상으로 기사 요약, organization을 중심으로 요약해줘.\"\n}"
        )

    print('Calling Ollama...')
    # 하드코딩된 기존 설정 (보관용 주석):
    # c = ChatOllama(model='llama-3-Korean-Bllossom-8B-Q4_K_M:latest', base_url='http://ksubscribe_ollama:11434', format='json')

    # 설정 파일의 값을 사용하도록 변경
    c = ChatOllama(model=CONF.OLLAMA_MODEL, base_url=CONF.OLLAMA_URL, format='json')
        r = c._client.generate(model=c.model, prompt=prompt, format='json')

        print('\nRAW_RESPONSE:')
        print(r.response[:4000])
        print('\n')
        try:
            parsed = json.loads(r.response)
            print('PARSED JSON:')
            print(json.dumps(parsed, ensure_ascii=False, indent=2))
        except Exception as e:
            print('Could not parse as JSON:', e)
            print('Full response saved to /app/logs/quick_eval_response.txt')
            with open('/app/logs/quick_eval_response.txt','w',encoding='utf-8') as f:
                f.write(r.response)

    except Exception as e:
        print('ERROR during processing:')
        traceback.print_exc()

if __name__ == '__main__':
    main()
