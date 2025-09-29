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

class WebLoaderV2:
    def __init__ (self):  
        #self.Summary("https://n.news.naver.com/mnews/article/421/0007826303")      
        pass
    
    def WebLoad (self, url):
        html =  self.Load(url)
        doc_transform =  self.Transform(html)
        splits =  self.Split(doc_transform)
        

        return splits
               
        
    def WebTotalLoad (self, url):
        #html =  self.Load(url)
        html_total =  self.GetHTML(url)
        return html_total
        # 웹사이트별 Contents 가져오기
        
      
        # 현재 데이터
        # 1. 산업통상자원부 (보도자료, 고시, 공고)
        
        
        # 2. 한국에너지기술평가원 (사업공고)
        
        # 3. 한국인터넷진흥원 (보도자료, 공지사항)
        contents = self.GetKISAParsing(html_total)
         
        # 4. 한전KPS(주) (보도자료)
         
        return contents
        
       
        
        title =  self.GetTitleParsing(html_total)
        img =  self.GetImgParsing(html_total)
        doc_transform =   self.Transform(html)
        splits =   self.Split(doc_transform)
        
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
        try:
            result = {}
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            
            if response.status_code == 200:
                html = response.text
                result = {'success': True, 'data': html}
            else :
                result = {'success': False, 'data': f'{response.status_code} : {response.reason}'}
                # print(f'code : {response.status_code} >>>>>>> \n {response.reason}\n ///////////////////////// \n') 
        except Exception as e:
            if(type(e.args[0]) == str):
                result = {'success': False, 'data': f'{e.args[0]}'}
            else :
                result = {'success': False, 'data': f'{e.args[0].args[0]}'}
            # print(f'HTML 가져오기 실패 - {e}')
            
        return result
  
    # 한국인터넷 진흥원
    def GetKISAParsing(self, html, tags_to_extract=["h2"]):
        soup = BeautifulSoup(html, 'html.parser')
        extracted_data = []
        
        # class가 'board_detail_info'인 div 찾기
        info_div = soup.find('div', class_='board_detail_info')
        if info_div:
            title = []
            date = []
            h2_tags = info_div.find_all('h2')  # div 아래의 모든 h2 태그 가져오기
            for h2 in h2_tags:
                title = h2.text.strip()  # h2 내용 출력
    
            dt_tags = info_div.find_all('dt')
            for dt in dt_tags:
                if dt.text.strip() == "등록일":  # dt 텍스트가 "one"인지 확인
                    # 해당 dt 태그의 다음 형제 dd 태그 찾기
                    dd_tag = dt.find_next_sibling('dd')
                    if dd_tag:
                        date = dd_tag.text.strip()  # dd 텍스트 출력
                    else:
                        print("해당 dt의 dd를 찾을 수 없습니다.")    
        
        # class가 'board_detail_contents'인 div 찾기
        contents_div = soup.find('div', class_='board_detail_contents')

        # 해당 div 안에 있는 모든 span 요소의 텍스트 가져오기
        if contents_div:
            
            non_strong_texts = []
            
            strong_texts = [
                span.get_text(strip=True)
                for strong in contents_div.find_all('strong')  # 모든 <strong> 태그 순회
                for span in strong.find_all('span')       # <strong> 아래 <span> 태그 찾기
            ]
            
            for span in contents_div.find_all('span'):
                # <strong> 아래에 있는 <span>인지 확인
                # if span.find_parent('strong'):
                #     continue  # <strong> 아래 있는 경우 제외

                # 가장 안쪽 <span>인지 확인
                if not span.find('span'):
                    non_strong_texts.append(span.get_text(strip=True))

            # 모든 <img> 태그 추가
            images = []
            for img in contents_div.find_all('img'):

                images.append(img.get('src'))

            # Contents 어떻게 구해야할까? -- 모든것이 통용되는 방법 찾아야 함
            
            # 가장 긴 요소 가져오기 
            max_str = max(non_strong_texts, key=len)
            
            # 가장 마지막 요소 가져오기 
            data = non_strong_texts[-1]


        return {'title' : title, 'contents' :data}
    
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

