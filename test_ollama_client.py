from langchain_ollama import ChatOllama
import traceback
import ksubscribe_share.config as CONF

print('instantiating...')
# 하드코딩된 기존 설정 (보관용 주석):
# c = ChatOllama(model='llama-3-Korean-Bllossom-8B-Q4_K_M:latest', base_url='http://172.17.0.1:11434', format='json')

# 설정 파일의 값을 사용하도록 변경
c = ChatOllama(model=CONF.OLLAMA_MODEL, base_url=CONF.OLLAMA_URL, format='json')
print('client ready, calling generate...')
try:
    r = c._client.generate(model=c.model, prompt='안녕하세요. 간단히 테스트 응답을 주세요.', format='text')
    print('OK result type:', type(r))
    print('raw:', r)
except Exception as e:
    print('EXCEPTION:', e)
    traceback.print_exc()
