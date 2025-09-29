# pip install -q langchain-openai langchain playwright beautifulsoup4
# playwright install
# pip install langchain_community
# pip install bert-score

from langchain_community.chat_models import ChatOllama

# AsyncChromiumLoader를 사용해서 특정 웹사이트의 HTML 가져오기
from langchain_community.document_loaders import AsyncChromiumLoader

# BeautifulSoupTransformer로 Html을 파싱 하기
from bs4 import BeautifulSoup
from langchain_community.document_transformers import BeautifulSoupTransformer

# LLM에게 전달해서 쉽게 정보 추출하기
from langchain.text_splitter import RecursiveCharacterTextSplitter
import tracemalloc
import time
import requests

# Bert Score로 요약 정확도 확인
from bert_score import score

tracemalloc.start()

class Summary:
    def __init__ (self):  
        #self.Summary("https://n.news.naver.com/mnews/article/421/0007826303")      
        pass
    
    async def Summary (self, content):
        # totalTimeStart = time.time()
        chat_ollama =  ChatOllama(model="llama3")#"llama3") #hf.co/MLP-KTLim/llama-3-Korean-Bllossom-8B-gguf-Q4_K_M:latest
        
        summary_ko = chat_ollama.predict(f"다음 내용을 3줄 이내로 요약해줘 답변은 한글로만 답변해줘: '{content}' ")

        return  summary_ko  


class MatchSummary:
     def __init__ (self):  
        #self.Summary("https://n.news.naver.com/mnews/article/421/0007826303")      
        pass
    
     async def MatchSummary (self, content, summary):
        # totalTimeStart = time.time()
        chat_ollama =  ChatOllama(model="llama3")#"llama3") #hf.co/MLP-KTLim/llama-3-Korean-Bllossom-8B-gguf-Q4_K_M:latest
        
        match_ko = chat_ollama.predict(f"다음 원문 내용과 요약내용이 얼마나 유사한지 판단해줘 답변은 다음 예시'80%, 이유'와 동일한 형식으로 해줘, 답변은 한글로만 해줘 => 원문 : '{content}', 요약문 : '{summary}' ")

        return  match_ko  
    
    
class AccuracySummary:
     def __init__ (self):  
        #self.Summary("https://n.news.naver.com/mnews/article/421/0007826303")      
        pass
    
     async def AccuracySummary (self, content, summary):
        # totalTimeStart = time.time()
        references = [content] # ["원문 내용"]  # List 형태로 여러 문장 가능
        candidates = [summary] #["요약된 내용"]  # List 형태로 여러 문장 가능
        
        P, R, F1 = score(candidates, references, lang="ko", verbose=True)
        f1Score = float(F1)

        return  f1Score  
