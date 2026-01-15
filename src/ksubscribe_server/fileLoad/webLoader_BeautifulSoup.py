from langchain.document_loaders import WebBaseLoader
from bs4 import BeautifulSoup
import requests

class WebLoaderBeautifulSoup:
    def __init__(self, url):
        self.url = url
    
    def load_webpage(self):
        # LangChain WebBaseLoader를 이용해 웹 페이지 로드
        loader = WebBaseLoader(self.url)
        document = loader.load()  # HTML 문서 로드
        return document[0].page_content if document else None
    
    def parse_content(self, html_content):
        # BeautifulSoup을 사용하여 HTML에서 필요한 정보 추출
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 제목(title) 추출
        title = soup.title.string if soup.title else "No Title Found"
        
        # 내용(content) 추출 (본문의 예시로 <p> 태그 내용)
        content = "\n".join([p.get_text() for p in soup.find_all('p')])
        
        # 이미지 추출 (첫 번째 이미지 URL 가져오기)
        images = [img['src'] for img in soup.find_all('img') if 'src' in img.attrs]
        
        return title, content, images

    def extract_and_save(self):
        # 1. 웹 페이지 로드
        html_content = self.load_webpage()
        if not html_content:
            print("Failed to load content.")
            return
        
        # 2. HTML에서 title, content, 이미지 추출
        title, content, images = self.parse_content(html_content)
        
        # 3. 추출한 데이터를 저장
        extracted_data = {
            "title": title,
            "content": content,
            "images": images
        }
        
        # 결과 출력 또는 저장 (여기서는 출력으로 대체)
        print("Title:", extracted_data["title"])
        print("Content:", extracted_data["content"][:500])  # 내용의 일부만 출력
        print("Images:", extracted_data["images"])




