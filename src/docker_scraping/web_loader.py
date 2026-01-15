from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException

import os
import requests
import pdfplumber
import re
import time

from ksubscribe_server.models.model import NewsModel
from ksubscribe_server.models.model import LoadModel
from ksubscribe_server.analysis.analysis_openai_v2 import analysisV2
from ksubscribe_share.db.dbmodelV2.errorInfo import ErrorInfo
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO, ContentsRaw, ContentsMeta, SentimentInfo
#from ksubscribe_share.db.dbmodelV2.commCodeVO import commCodeVO
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO,ContentsOrgCategory
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.dbmodel.news import News
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
from ksubscribe_share.db.dbmodelV2.predefineKeywordVO import PredefineKeywordVO
from ksubscribe_share.db.service.commCodeService import CommCodeService
import ksubscribe_share.config as Conf
from docker_collect.driver_utils import get_driver
from ksubscribe_share.db.service.naverScrappingService import NaverScrappingService
from ksubscribe_share.db.dbmodelV2.naverScrappingInfoVO import NaverScrappingInfoVO


class WebScraper:
    def find_text_in_body(self,driver):
        # <body> 태그 가져오기
        body_element = driver.find_element(By.TAG_NAME, 'body')

        # BeautifulSoup로 HTML 파싱
        soup = BeautifulSoup(body_element.get_attribute('outerHTML'), 'html.parser')

        # <img> 태그 제거
        for img_tag in soup.find_all('img'):
            img_tag.decompose()

        # 텍스트만 추출
        body_text = soup.get_text(separator="\n")
        # 연속된 줄바꿈(\n\n 이상)을 하나의 줄바꿈(\n)으로 축소
        body_text = re.sub(r'\n+', '\n', body_text)
        return body_text.strip()
    

class WebLoaderV3:

    
    download_folder = Conf.SCRAPING_DOWNLOAD_FOLDER 
    def __init__(self):
        self.create_folder_if_not_exists(self.download_folder)    
    
    def create_folder_if_not_exists(self,folder_path): 
        # 폴더가 존재하지 않는 경우 생성 
        if not os.path.exists(folder_path): 
            os.makedirs(folder_path) 
            #print(f"폴더 '{folder_path}'가 생성되었습니다.") 
        else: 
            pass  
 
    def find_pdf_url(self, url, driver):
        """
        PDF 링크를 포함하는 <a> 태그에서 URL을 추출합니다.
        형태 1 : <a href="pdf_file.pdf"/> 
        :param url: 페이지의 기본 URL (베이스 URL)
        :param driver: Selenium WebDriver 객체
        :return: 추출된 PDF의 URL (없으면 None)
        """         
        
        # 페이지에서 a 태그 중 PDF 링크를 탐지
        pdf_links = driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf')]")
        
        if pdf_links:
            print(f"Found {len(pdf_links)} PDF(s) on the page.")
            return pdf_links[0].get_attribute("href")  # 첫 번째 PDF 링크 반환
        else:
            print("No PDF attachment found.")
            return None
        
    def find_pdf_element(self, url, driver):
        try:
            # pdf_element = driver.find_element(By.XPATH, "//a[contains(@href, '.pdf')]")
            # pdf_element = driver.find_element(
            #     By.XPATH, "//a[contains(@href, '.pdf') | (contains(text(), '.pdf') and @data-type='pdf')]"
            # )            
            # pdf_element = driver.find_element(
            #     By.XPATH, "//a[contains(@href, '.pdf') or ((contains(text(), '.pdf') and @data-type='pdf'))]"
            # )   
            pdf_element = None
            pdf_element = driver.find_element(By.XPATH, "//a[contains(@href, '.pdf')] ")                        
            
            # pdf_element = driver.find_element(
            #     By.XPATH, "//a[contains(text(), '.pdf') and @data-type='pdf']"
            # )
        
        except Exception as e:
            print(f".pdf link 없음")
            pdf_element = driver.find_element(
                By.XPATH, "//a[contains(@title, '.pdf') and @data-type='pdf']"
            )
        finally:
            return pdf_element
                    
        
    def find_pdf_from_onclick(self, url, driver):
        """
        PDF 링크를 포함하는 <a> 태그에서 URL을 추출합니다.
        형태 2 : <a href="#" onclick="location.href='~~'" > pdf 파일명</a> 
        :param url: 페이지의 기본 URL (베이스 URL)
        :param driver: Selenium WebDriver 객체
        :return: 추출된 PDF의 URL (없으면 None)
        """        
        # PDF 다운로드를 트리거하는 <a> 태그 찾기
        pdf_elements = driver.find_elements(By.XPATH, "//a[(contains(@onclick, 'location.href') and contains(text(), 'pdf')) ]")
        for element in pdf_elements:
            onclick_value = element.get_attribute("onclick")
            if onclick_value:
                # onclick 속성에서 PDF URL 추출
                pdf_url_match = re.search(r"['\"](.*?)['\"]", onclick_value)
                if pdf_url_match:
                    pdf_url = pdf_url_match.group(1)
                    # 상대 경로일 경우 절대 경로로 변환
                    if not pdf_url.startswith('http'):
                        pdf_url = requests.compat.urljoin(url, pdf_url)
                    return pdf_url
        return None
    
    def find_pdf_element_from_onclick(self, url, driver):
        # PDF 다운로드를 트리거하는 <a> 태그 찾기
        try:
            # PDF 다운로드를 트리거하는 <a> 태그 찾기
            pdf_element = driver.find_element(By.XPATH, "//a[(contains(@onclick, 'location.href') and contains(text(), 'pdf')) ]")
            return pdf_element
        except Exception as e:
            #print(f"오류 발생: {e}")
            pass

        return None          
        
    def find_pdf_from_onclickFunction(self, url, driver):
        """
        PDF 링크를 포함하는 <a> 태그에서 URL을 추출합니다.
        형태 3 : <a href="#" onclick="함수명('id')" > pdf 파일명</a> 
        :param url: 페이지의 기본 URL (베이스 URL)
        :param driver: Selenium WebDriver 객체
        :return: 추출된 PDF의 URL (없으면 None)
        """
        try:
            # PDF 다운로드를 트리거하는 <a> 태그 찾기
            pdf_elements = driver.find_elements(By.XPATH, "//a[contains(@onclick, '(') and contains(text(), 'pdf')]")

            for element in pdf_elements:
                onclick_value = element.get_attribute("onclick")
                if onclick_value:
                    # onclick 속성에서 URL 추출
                    pdf_url_match = re.search(r"['\"](.*?)['\"]", onclick_value)
                    if pdf_url_match:
                        pdf_url = pdf_url_match.group(1)

                        # 상대 경로인 경우 절대 경로로 변환
                        if not pdf_url.startswith("http"):
                            pdf_url = requests.compat.urljoin(url, pdf_url)

                        return pdf_url

        except Exception as e:
            #print(f"오류 발생: {e}")
            pass

        return None

    def find_pdf_element_from_onclickFunction(self, url, driver):
        try:
            # PDF 다운로드를 트리거하는 <a> 태그 찾기
            pdf_element = driver.find_element(By.XPATH, "//a[contains(@onclick, '(') and contains(text(), 'pdf')]")
            return pdf_element
            
        except Exception as e:
            #print(f"오류 발생: {e}")
            pass

        return None          
        
    def download_pdf(self, pdf_url, save_path):
        try:
            response = requests.get(pdf_url)
            response.raise_for_status()  # HTTP 에러 확인
            with open(save_path, 'wb') as f:
                f.write(response.content)
            print(f"PDF downloaded to {save_path}")
            return True
        except Exception as e:
            #print(f"Error downloading PDF: {e}")
            return False
    
    def download_pdf_via_click(self, pdf_element,driver):
        try:

            # 클릭하여 다운로드 시작
            start_time = time.time()
            initial_files = set(os.listdir(self.download_folder))

            ActionChains(driver).move_to_element(pdf_element).click().perform()
            #time.sleep(3)
            # 파일 다운로드 완료 대기
            downloaded_file = self.wait_for_download(self.download_folder, start_time, initial_files)
            if downloaded_file:
                print(f"다운로드된 파일: {downloaded_file}")
                return downloaded_file
            else:
                print("파일 다운로드가 완료되지 않았습니다.") 
                
        except Exception as e:
            #print(f"Error downloading PDF: {e}")
            return None
        
    def read_pdf(self, save_path, max_pages=3):
        try:
            #full_url = os.path.join(webLoader3.download_folder, save_path) 
            with pdfplumber.open(save_path) as pdf:
                text = ''
                for i, page in enumerate(pdf.pages):
                    if i >= max_pages:  # 최대 페이지 제한
                        break
                    text += page.extract_text() + '\n'
            #print(f"PDF content:\n{text[:5000]}")  # 처음 500자 출력
            return text
        except Exception as e:
            #print(f"Error reading PDF: {e}")
            return ""

    def wait_for_download(self, download_folder,start_time, initial_files, timeout=30):
        """
        다운로드 폴더에서 새 파일이 생성될 때까지 대기합니다.

        :param download_path: 다운로드 폴더 경로
        :param timeout: 대기 시간 (초)
        :return: 다운로드된 파일 이름 (없으면 None)
        """
        while time.time() - start_time < timeout:
            current_files = set(os.listdir(download_folder))
            new_files = current_files - initial_files
            pdf_files = [f for f in new_files if f.endswith(".pdf")]
            if pdf_files:
                return os.path.join(download_folder, pdf_files[0])            
            time.sleep(1)
        return None
 
    def find_text_in_tag(self, tag_name,tag_value,element_name, driver):
        # 모든 <article> 태그 찾기
        #article_elements = driver.find_elements_by_tag_name(tagName)
        
        # 1. element 찾기 
        #elements = driver.find_elements(By.TAG_NAME, tag_name)
 
        # 2. element에서 태그 네임이 tag_value인 컨테이너? 찾기  
        if not tag_name: 
            tag_filter = "//{}".format(element_name)
        else: 
            tag_filter = "//{}[@{}='{}']".format(element_name,tag_name,tag_value)
        elements = driver.find_elements(By.XPATH, tag_filter)

        result_text = ""
        # <article> 태그 내 텍스트 수집
        for e in elements:
            if len(e.text) + len(result_text) >500:#if len(e.text) + len(result_text) >500:
                result_text = e.text[:500]
                return result_text
            result_text = e.text + "\n" 
        return result_text
    
    def find_text_in_html(self,driver):
        try:
            scraper = WebScraper()
            body_text = scraper.find_text_in_body(driver)
            return body_text
        except Exception as e:
            return None  
        
    def loadContents(self, contentsVO:ContentsVO, contentsOrgVO:ContentsOrgVO, contentsOrgCategory:ContentsOrgCategory,driver):
        url = contentsVO.url
        
        driver.set_page_load_timeout(60)
        try:
            driver.get(url)
        except TimeoutException as e :
            return False, str(e)
        
        #llm = analysisV2()
        input_text = None
        try:
            if contentsOrgCategory.collectMethod.upper() == 'onlyPdf'.upper():
                pdf_element = self.find_pdf_element(url, driver)
                if(pdf_element == None) : 
                    pdf_element = self.find_pdf_element_from_onclick(url, driver)
                if(pdf_element == None) : 
                    pdf_element = self.find_pdf_element_from_onclickFunction(url, driver)
                if pdf_element:
                    download_file = self.download_pdf_via_click(pdf_element,driver)
                    input_text = self.read_pdf(download_file)  
                else:
                    print("No PDF attachment to process.")
                    return False, "No PDF attachment to process."
            elif contentsOrgCategory.collectMethod.upper() == 'textInTag'.upper():
                tag = contentsOrgCategory.tagAttr
                tag_value = contentsOrgCategory.tagAttrValue
                element = contentsOrgCategory.tagElement
                input_text = self.find_text_in_tag(tag,tag_value,element,driver) 
            elif contentsOrgCategory.collectMethod.upper() == 'textInBody'.upper(): 
                input_text = self.find_text_in_html(driver)
            
            return True, input_text
        except Exception as e: 
            return False, str(e)
            
        
    def loadContents_naver_contents(self, url:str):
        
        driver.set_page_load_timeout(60)
        try:
            driver.get(url)
        except TimeoutException as e :
            return False, str(e)
        
        naverScrappingService = NaverScrappingService()
        naverScrappingInfoVO:NaverScrappingInfoVO = naverScrappingService.getNaverScappingInfo(url)
        
        input_text = None
        try:
            if naverScrappingInfoVO.collectMethod.upper() == 'textInTag'.upper():
                tag = naverScrappingInfoVO.tagAttr
                tag_value = naverScrappingInfoVO.tagAttrValue
                element = naverScrappingInfoVO.tagElement
                input_text = self.find_text_in_tag(tag,tag_value,element,driver) 
            elif naverScrappingInfoVO.collectMethod.upper() == 'textInBody'.upper(): 
                input_text = self.find_text_in_html(driver)
            
            return True, input_text
        except Exception as e: 
            return False, str(e)

    
if __name__ == "__main__":
    
    webLoader3 = WebLoaderV3()
    #산업통산자원부 테스트 
    # url_list_A0001_B0001 = ["https://www.motie.go.kr/kor/article/ATCL3f49a5a8c/169997/view",
    #        "https://www.motie.go.kr/kor/article/ATCL3f49a5a8c/169996/view",
    #        "https://www.motie.go.kr/kor/article/ATCL3f49a5a8c/169995/view",
    #        "https://www.motie.go.kr/kor/article/ATCL3f49a5a8c/169994/view",
    #        "https://www.motie.go.kr/kor/article/ATCL3f49a5a8c/169993/view",
    #        "https://www.motie.go.kr/kor/article/ATCL3f49a5a8c/169992/view",
    #        "https://www.motie.go.kr/kor/article/ATCL3f49a5a8c/169991/view",
    #        ]
    # url_list_A0001_B0002 = ["https://www.motie.go.kr/kor/article/ATCL2826a2625/69849/view"]
    # url_list_A0001_B0010 = ["https://www.newsis.com/view/NISX20241204_0002982787",
    #        "https://www.yna.co.kr/view/AKR20241204082200005?input=1195m",
    #        "https://www.newsis.com/view/NISX20241203_0002982473",
    #        "https://biz.newdaily.co.kr/site/data/html/2024/12/04/2024120400136.html"
    #        ]
    # url_list_A0001_B0011=[]
    
    
    driver = get_driver()
    
    try:
        url = 'https://www.motie.go.kr/kor/article/ATCL3f49a5a8c/169997/view'
        tag_url = 'https://www.motie.go.kr/kor/article/ATCL2826a2625/69939/view?mno=&pageIndex=1&rowPageC=0&schClear=on&startDtD=&endDtD=&searchCondition=1&searchKeyword='
        driver.get(tag_url)
        body_text = webLoader3.find_text_in_html(driver)
        # tag = 'class'
        # tag_value = 'detail-cont' #산업 통상부 좀 다름
        # element = 'div'
        # driver.get(tag_url)
        # text = webLoader3.find_text_in_tag(tag,tag_value,element,driver)
        print("get text in tag 완료")
        # try :
        #     pdf_element = webLoader3.find_pdf_element(url, driver)
        #     if(pdf_element == None) : 
        #         pdf_element = webLoader3.find_pdf_element_from_onclick(url, driver)
        #     if(pdf_element == None) : 
        #         pdf_element = webLoader3.find_pdf_element_from_onclickFunction(url, driver)
        #     if pdf_element:
        #         download_file = webLoader3.download_pdf_via_click(pdf_element,driver)
        #         article = webLoader3.read_pdf(download_file)
        #         print("Read 완료 #######################################")
        #     else:
        #         print("No PDF attachment to process.")
        # except Exception as e :
        #     pass 
        
        # # url_list_A0001_B0001를 테스트한 코드 (보도자료)
        # # pdf download 링크를 찾도록 구현함 
        # for url in url_list_A0001_B0001:
            
        #     driver.get(url)
        #     pdf_element = webLoader3.find_pdf_element(url, driver)
        #     if(pdf_element == None) : 
        #         pdf_element = webLoader3.find_pdf_element_from_onclick(url, driver)
        #     if(pdf_element == None) : 
        #         pdf_element = webLoader3.find_pdf_element_from_onclickFunction(url, driver)
                
        #     if pdf_element:
        #         download_file = webLoader3.download_pdf_via_click(pdf_element)
        #         article = webLoader3.read_pdf(download_file)
        #         print("Read 완료 #######################################")
        #     else:
        #         print("No PDF attachment to process.")

        ##########################################################################################                
        # url_list_A0001_B0002 테스트한 코드 (사업공고)
        # article tag안에 있는 모든 내용을 수집하도록 구현            
        # for url in url_list_A0001_B0002:            
        #     driver.get(url)            
        #     text = webLoader3.find_text_in_tag('article')
        #     print(f"content:\n{text[:500]}")  # 처음 500자 출력

        ##########################################################################################                
        # # url_list_A0001_B0010 테스트한 코드 (네이버뉴스)
        # # body안에 있는 모든 내용을 수집하도록 구현   
        # 네이버 뉴스는 그렇게 해야 할 것 같음.          
        # for url in url_list_A0001_B0010:            
        #     driver.get(url)            
        #     body_text = webLoader3.find_text_in_html(driver)
        #     print(len(body_text))
                
    except Exception as e:
        print(f'error : {e}')            
    finally:
        driver.quit()

    
    
    
    
