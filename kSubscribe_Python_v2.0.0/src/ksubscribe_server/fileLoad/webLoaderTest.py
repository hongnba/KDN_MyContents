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

tracemalloc.start()

class WebLoaderTEST:
    def __init__ (self):  
        #self.Summary("https://n.news.naver.com/mnews/article/421/0007826303")      
        pass
    
    def WebLoad (self, url):

        # LoadTimeStart = time.time()
        html =  self.Load(url)
        # LoadTimeEnd = time.time()
        
        # TransfimeStart = time.time()
        doc_transform =  self.Transform(html)
        # TransfimeEmd = time.time()
        
        # SpiltTimeStart = time.time()
        splits =  self.Split(doc_transform)
        # SpiltTimeEnd = time.time()
        

        return splits
               
        
    def WebTotalLoad (self, url):

        # LoadTimeStart = time.time()
        html =  self.Load(url)
        # LoadTimeEnd = time.time()
        
        html_total =  self.GetHTML(url)
        
        title =  self.GetTitleParsing(html_total)
        img =  self.GetImgParsing(html_total)
        
        # TransfimeStart = time.time()
        doc_transform =   self.Transform(html)
        # TransfimeEmd = time.time()
        
        # SpiltTimeStart = time.time()
        splits =   self.Split(doc_transform)
        # SpiltTimeEnd = time.time()
        

        return {
                'title' : title[0],
                'article': doc_transform[0].page_content, 
                'image' : img[0],
               }
    
        
    def Load(self, url):
        urls = [url]
        loader = AsyncChromiumLoader(urls)
        html = loader.load()
        return html

    def GetHTML(self, url):
        result = ""
        response = requests.get(url)
        
        if response.status_code == 200:
            html = response.text
            result = html
            
        return result
  
    def GetTitleParsing(self, html, tags_to_extract=["h2"]):
        soup = BeautifulSoup(html, 'html.parser')
        extracted_data = []

        for tag in tags_to_extract:
            # h2 태그 안의 span 태그들만 추출
            for h2_tag in soup.find_all(tag):
                span_tag = h2_tag.find('span')  # h2 태그 안의 첫 번째 span 태그 찾기
                if span_tag:
                    extracted_data.append(span_tag.get_text())  # span의 텍스트만 추출

        return extracted_data
    
    def GetImgParsing(self, html, tags_to_extract=["article"]):
        soup = BeautifulSoup(html, 'html.parser')
        extracted_data = []

        for tag in tags_to_extract:
            # article 태그 안의 img 태그들만 추출
            for article_tag in soup.find_all(tag):
                img_tag = article_tag.find('img')  # h2 태그 안의 첫 번째 span 태그 찾기
                if img_tag:
                    img = img_tag.get('data-src')
                    extracted_data.append(img)  # span의 텍스트만 추출

        return extracted_data
            
    def Transform(self, html):
        bs_transformer = BeautifulSoupTransformer()
        docs_transformed = bs_transformer.transform_documents(html, tags_to_extract=["article"])

        return docs_transformed

    def Split(self, docs_transformed):
        splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(  
        chunk_size=1000, chunk_overlap=0  
        )
        splits = splitter.split_documents(docs_transformed)
        
        return splits

