# pip install -q langchain-openai langchain playwright beautifulsoup4
# playwright install
# pip install langchain_community

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


class PDFLoader:
    def __init__ (self):      
        pass
    
    async def PDFLoad (self, url):
        return "PDF File Load"