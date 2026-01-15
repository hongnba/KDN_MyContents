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

from ksubscribe_share.db.dbmodel.webSite import WebSite
from ksubscribe_share.db.dbmodel.newsContents import NewsContents

import os
os.environ['USER_AGENT'] = 'myagent'



tracemalloc.start()

class WebLoader:
    def __init__ (self):   
        pass
    
    def WebLoad (self, news):
        url = news.link
        try:
            html = self.GetHTML(url)
        except:
            return
        tld_url = self.GetTldUrl(url)
        query = {"tld_url": tld_url}
        webinfo = WebSite.find_many(query)

        if len(webinfo) == 0:
            return
        if webinfo[0].selector == "Not detected":
            return
        
        content, img = self.GetParsing(html, webinfo[0].selector)

        newscontent = NewsContents("test", content, img)

        news.newsContents = newscontent
        news.update_one()



    
    def GetHTML(self, url):
        result = ""
        response = requests.get(url)
        
        if response.status_code == 200:
            html = response.text
            result = html
            
        return result

    def GetParsing(self, html, selector):
        soup = BeautifulSoup(html, 'html.parser')
        article_body = soup.select_one(selector)
        imagelist = article_body.find_all("img")
        image = None
        if len(imagelist) > 0:
            if article_body.find_all("img")[0].get('src'):
                image = article_body.find_all("img")[0]['src']
        return article_body.text, image
    
  

            
    def GetTldUrl(self, url):
        parts = url.split('/')
        return f"{parts[0]}//{parts[2]}"



