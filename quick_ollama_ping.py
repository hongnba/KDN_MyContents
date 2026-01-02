#!/usr/bin/env python3
"""
quick_ollama_ping.py
간단한 Ollama 엔드포인트 검사 스크립트
사용법:
    python3 quick_ollama_ping.py --url http://localhost:11434

이 스크립트는 여러 가능한 엔드포인트에 대해 요청을 보내고
응답 상태 코드와 본문 앞부분을 출력합니다. 로컬에서 실행하세요.
"""
import argparse
import requests
import sys
import ksubscribe_share.config as CONF

ENDPOINTS = [
    '/',
    '/api/models',
    '/models',
    '/api/generate',
    '/api/version',
    '/version',
]

# 이전 llama-3-Korean-Bllossom-8B-Q4_K_M 모델 사용 (주석 처리):
# SAMPLE_PAYLOAD = {
#     "model": "llama-3-Korean-Bllossom-8B-Q4_K_M:latest",
#     "prompt": "안녕하세요. 테스트 응답을 주세요.",
#     "max_tokens": 16
# }

# 현재 사용: gpt-oss:20b 모델
# 하드코딩된 기존 설정 (보관용 주석):
# SAMPLE_PAYLOAD = {
#     "model": "gpt-oss:20b",
#     "prompt": "안녕하세요. 테스트 응답을 주세요.",
#     "max_tokens": 16
# }

# 설정 파일의 값을 사용하도록 변경
SAMPLE_PAYLOAD = {
    "model": CONF.OLLAMA_MODEL,
    "prompt": "안녕하세요. 테스트 응답을 주세요.",
    "max_tokens": 16
}


def try_get(url, path, timeout=5):
    full = url.rstrip('/') + path
    try:
        r = requests.get(full, timeout=timeout)
        body = r.text
        print(f"GET {path} -> {r.status_code} {r.reason}")
        print(body[:1000])
    except Exception as e:
        print(f"GET {path} -> ERROR: {e}")


def try_post(url, path, payload=None, timeout=10):
    full = url.rstrip('/') + path
    try:
        r = requests.post(full, json=payload or {}, timeout=timeout)
        print(f"POST {path} -> {r.status_code} {r.reason}")
        # Try to show JSON safely
        text = r.text
        print(text[:2000])
    except Exception as e:
        print(f"POST {path} -> ERROR: {e}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--url', default='http://localhost:11434', help='OLLAMA base URL')
    p.add_argument('--try-generate', action='store_true', help='POST to /api/generate with small sample payload')
    args = p.parse_args()

    url = args.url
    print(f"Probing {url} for common Ollama endpoints...\n")

    # Try GET on each
    for path in ENDPOINTS:
        # For POST endpoint path (/api/generate), do GET first too
        try_get(url, path)
        print('-' * 60)

    if args.try_generate:
        print('\nAttempting a small POST to /api/generate (may start a model load)')
        try_post(url, '/api/generate', SAMPLE_PAYLOAD)


if __name__ == '__main__':
    main()
