from datetime import date, datetime, timedelta
import traceback
import pytz
import re
import traceback
import pandas as pd
import urllib.request
from typing import List
import requests
import json
import time
import pickle
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from sklearn.metrics.pairwise import linear_kernel
from sklearn.feature_extraction.text import TfidfVectorizer
from bs4 import BeautifulSoup

import ssl
import sys

from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO, ContentsOrgCategory
from ksubscribe_share.db.dbmodelV2.contentsCollectHistoryVO import ContentsCollectDetail
from ksubscribe_share.db.service.contentsCollectHistoryService import ContentsCollectHistoryService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.logger import Logger
from ksubscribe_share.utils.random_utils import generate_random_string
from ksubscribe_share.db.mongoManager import MongoManager


contentsCollectHistoryService = ContentsCollectHistoryService() 
contentsOrgService = ContentsOrgService()   

# SELENIUM
def get_contents_by_selenium_main(driver, contentsOrg : ContentsOrgVO, category : ContentsOrgCategory):
    sys.setrecursionlimit(10**6)
    ssl._create_default_https_context=ssl._create_unverified_context
 
    driver.set_page_load_timeout(300)
    today = datetime.now(pytz.timezone('Asia/Seoul'))    #today.
    logger = Logger()
    docker_collect_logger = logger.setup_logger(logger.docker_collect_logger_name)
     
    # 여기서 from 날짜를 뽑아서
    # today = [231223, 231224, 231225]

 #   last_suc_str = category.lastSucYMD 
    last_suc = category.lastSucYMD #datetime.strptime(last_suc_str, "%Y%m%d")
    # seoul_tz = pytz.timezone('Asia/Seoul')
    # last_suc = seoul_tz.localize(last_suc)
    # last_suc 다음 날짜부터 오늘까지의 날짜 리스트 생성
    next_day = last_suc# + timedelta(days=1)
    #date_list = [(next_day + timedelta(days=x)).strftime("%Y%m%d") for x in range((today - next_day).days + 1)]
    
    date_list=['20250905','20250906','20250907','20250908','20250909','20250910'] #김현지 테스트용

    lastSucYMD = today 
    result = {}
        
    try:
        docker_collect_logger.info(f'get_contents_by_selenium_main : {contentsOrg.orgName}({contentsOrg.orgId}) {category.cateName}({category.cateId}) 수집 시작')
        
        # aT 크롤링 차단으로 인해 브라우저 쿠키 사용 우회
        if contentsOrg.orgId == 'A0029':
            # 이후의 요청에서 쿠키를 사용
            driver.get(category.collectUrlInfo)
            print(driver.page_source[:1000])
            time.sleep(3)

            # 쿠키를 저장
            pickle.dump(driver.get_cookies(), open("cookies.pkl", "wb"))
            
            driver.get(category.collectUrlInfo)
            for cookie in pickle.load(open("cookies.pkl", "rb")):
                driver.add_cookie(cookie)

            # 웹페이지 접속
            driver.refresh()
        else: 
            driver.get(category.collectUrlInfo)
            #print(driver.page_source[:1000])
        time.sleep(2)
        
    except Exception as e:
        pass 
        traceback.print_exc()
        result = {"success" : False , "error" : e,"datetime" : today}
        # return result


    #mongoManager = MongoManager()
    #session = mongoManager.client.start_session()  
        
    collect_cnt = 0     
    try:
        # 트랜잭션 시작
        # session.start_transaction( )         
        result, collect_sub_cnt = get_contents_by_selenium(driver, contentsOrg, category, date_list, today)
        collect_cnt += collect_sub_cnt        
        if result["success"] == False : 
            raise Exception("collect fail")  # 예외 발생

        while(result["next_page"] is not None) : 
            time.sleep(2)         
            result["next_page"].click()
            result, collect_sub_cnt = get_contents_by_selenium(driver, contentsOrg, category, date_list, today)
            collect_cnt += collect_sub_cnt
            
            if result["success"] == False : 
                raise Exception("collect fail")  # 예외 발생
       
        contentsOrgService.updateCategorySucYMD(contentsOrg.orgId, category.cateId, True, lastSucYMD,logger=docker_collect_logger)

        # 트랜잭션 커밋
        #session.commit_transaction()
        #docker_collect_logger.debug("트랜잭션 커밋 성공!")
        docker_collect_logger.info(f'get_contents_by_selenium : {contentsOrg.orgName}({contentsOrg.orgId}) {category.cateName}({category.cateId}) 수집 완료 (건수 : {collect_cnt})')
        result = {"success" : True ,"datetime" : today}

    except Exception as e:
        docker_collect_logger.info(f'get_contents_by_selenium : {contentsOrg.orgName}({contentsOrg.orgId}) {category.cateName}({category.cateId}) 수집 오류 (건수 : {collect_cnt})')
        docker_collect_logger.debug(e) 
        # 예외 발생 시 트랜잭션 롤백
        #session.abort_transaction()
        #docker_collect_logger.debug(f'트랜잭션 롤백: {e} ')        
        result = {"success" : False , "error" : e,"datetime" : today}
    
    # 세션 종료
    #session.end_session()        
    return result   

def get_contents_by_selenium(driver, contentsOrg : ContentsOrgVO, category : ContentsOrgCategory, date_list, today, session = None):
    collect_cnt = 0
    logger = Logger()
    docker_collect_logger = logger.setup_logger(logger.docker_collect_logger_name)
    result = {}
    next_page = None
    try:
            # Xpath로 tbody or ul... 잡기
        try:
            tbody = driver.find_element(By.XPATH, category.COL_HTML_TBODY_TAG)
        except Exception as e:
            tbody = driver.find_element(By.TAG_NAME, 'tbody')
            # tag_name으로. tr or li 임
        trs = tbody.find_elements(By.TAG_NAME, category.COL_HTML_TR_TAG)
        for idx, tr in enumerate(trs):
            # tr 하위 td 잡기. tag_name으로. td or span or p
            td = tr.find_elements(By.TAG_NAME, category.COL_HTML_TD_TAG)
            if len(td) == 0 : continue
            # 공지사항 건너뛰기 시작
            if tr.get_attribute('class') == 'nia_noti' \
                or tr.get_attribute('class') == 'cate' \
                or td[0].text == '공지' \
                or tr.get_attribute('class') == 'notice_alert' \
                or tr.get_attribute('class') == 'boardNotice_Row' \
                or tr.get_attribute('class') == 'colNotice' \
                or tr.get_attribute('class') == 'row notice' \
                or tr.get_attribute('class') == 'row md-dn':
                    continue
                # 공지사항 건너뛰기 끝

                # 제목 가져오기 시작
            if contentsOrg.orgId == 'A0001' and category.cateId == 'B0002':
                    title = td[1].find_element(By.TAG_NAME, 'a').text
            elif contentsOrg.orgId == 'A0001' and category.cateId == 'B0004':
                    title = td[2].find_element(By.TAG_NAME, 'a').get_attribute('title')
            elif contentsOrg.orgId == 'A0009' or contentsOrg.orgId == 'A0005':
                    title = td[1].text
            elif contentsOrg.orgId == 'A0018':
                    title = tr.find_element(By.CLASS_NAME, 'thumbnail_txt').find_elements(By.TAG_NAME, 'p')[0].text[13:]
            elif contentsOrg.orgId == 'A0001' and category.cateId == 'B0001':
                    title = td[2].find_element(By.TAG_NAME, 'a').text
            elif contentsOrg.orgId == 'A0023':
                    title = tr.find_element(By.CLASS_NAME, category.COL_HTML_TITLE_TAG).text
            elif contentsOrg.orgId == 'A0029':
                    title = tr.find_element(By.CLASS_NAME, category.COL_HTML_TITLE_TAG).text
            elif contentsOrg.orgName == '부산항만공사': # 250403 추가. 부산항만공사.
                    title = tr.find_element(By.CLASS_NAME, category.COL_HTML_TITLE_TAG).find_element(By.TAG_NAME, 'span').text
            elif contentsOrg.orgName == '한국콘텐츠진흥원': # 250521 추가
                    title = tr.find_element(By.TAG_NAME, 'a').text
            else:
                    # class_name으로 tit, subject 등 new 이런 span or em태그 떼어내야
                    title = tr.find_element(By.CLASS_NAME, category.COL_HTML_TITLE_TAG)
                    html_content = title.get_attribute('innerHTML')
                    # BeautifulSoup로 파싱하여 태그 제거
                    soup = BeautifulSoup(html_content, "html.parser")
                    for tag in soup.find_all(["span", "em"]):
                        tag.decompose()
                    title = soup.text.strip()
                # 제목 가져오기 끝

                # 날짜 가져오기 시작
                # td[n] 순서로 엘리먼트 잡고 '202' 찾아서 idx로 끝자리까지
            if contentsOrg.orgId == 'A0013':
                    date_element = tr.find_element(By.CLASS_NAME, 'date').text
            elif contentsOrg.orgId == 'A0008':
                    date_element = tr.find_element(By.CLASS_NAME, 'src').text
            elif contentsOrg.orgId == 'A0044' and contentsOrg.cateId =='B0001': # 250813 국민연금공단 보도자료
                    dateCntForNps = dateCntForNps + 1
                    xpathForNps = '//*[@id="contents"]/div[3]/div[1]/ul/li['+str(dateCntForNps)+']/ul/li[2]/span[2]'
                    date_element = tr.find_element(By.XPATH, xpathForNps).text
            else:
                    date_element = td[category.COL_HTML_DATE_N].text # '등록일자 2023.05.08 or 2023-05-08

            date_idx = date_element.find('202')
            date = date_element[date_idx:date_idx+10]
            date = re.sub(r'[^0-9]', '', date)
                # 날짜 가져오기 끝

                # URL 가져오기 시작
                # a태그 링크 / onclick에 붙은 param             
            if category.COL_HTML_URL_TYPE == 'link':
                    # if row_data[4] == 'KHNPd':
                    #     url = tr.find_element(By.TAG_NAME, 'a').get_attribute(row_data["COL_HTML_TD_TAG"])
                if tr.find_element(By.TAG_NAME, 'a').get_attribute(category.COL_HTML_URL_ATTR) is not None:
                        url = tr.find_element(By.TAG_NAME, 'a').get_attribute(category.COL_HTML_URL_ATTR)
                else:
                        url = td[category.COL_HTML_URL_LINK_N].find_element(By.TAG_NAME, 'a').get_attribute(category.COL_HTML_URL_ATTR)
                        
            elif category.COL_HTML_URL_TYPE == 'param':
                    # url에 들어갈 param 찾기
                    # 속성값을 찾아오는 경우, 없어도 에러를 발생시키지 않음.
                    # 첫번째 시도
                if tr.get_attribute(category.COL_HTML_URL_ATTR) is not None:
                        js_func = tr.get_attribute(category.COL_HTML_URL_ATTR)
                    # 두번째 시도
                elif tr.find_element(By.TAG_NAME, 'a').get_attribute(category.COL_HTML_URL_ATTR) is not None:
                        js_func =  tr.find_element(By.TAG_NAME, 'a').get_attribute(category.COL_HTML_URL_ATTR)
                    # 나머지 경우
                else:
                        js_func = td[category.COL_HTML_URL_LINK_N].find_element(By.TAG_NAME, 'a').get_attribute(category.COL_HTML_URL_ATTR)

                pattern = r"'([^']*)'"  # 작은따옴표로 둘러싸인 문자열을 찾는 정규식
                param_list = re.findall(pattern, js_func)  # 정규식과 대상 문자열을 이용하여 매칭된 문자열들을 추출
                    # ['99835', '25515', '16010100', '25515']
                    # 몇번째 param을 가지고 올건지
                if len(param_list) == 0:
                        pattern = r"\((.*?)\)"
                        result = re.findall(pattern, js_func)
                        url = category.COL_HTML_DETAIL_PAGE_URL + result[category.COL_HTML_URL_PARAM_N]
                else:
                        url = category.COL_HTML_DETAIL_PAGE_URL + param_list[category.COL_HTML_URL_PARAM_N]
                if contentsOrg.orgId == 'A0009':
                        url += '|snsShare'
                if contentsOrg.orgId == 'A0028':
                        url += '/detailView.do'
                if contentsOrg.orgId == 'A0001':
                        url += '/view'
                if contentsOrg.orgId == 'A0039':
                        url += '&lev=0'
                        #print(url)
                    # URL 가져오기 끝

                # 오늘 날짜인 것만 체크.
            if date in date_list:
                    print(date_list)
                    print(date, '날짜를 찾았습니다! 스크래핑을 시작합니다.')
                    #docker_collect_logger.debug('오늘 날짜임!')
                    unique_value = generate_random_string(5)

                    collectDetail = ContentsCollectDetail() 
                    collectDetail.url = url
                    collectDetail.title = title
                    # date = datetime.strptime(date,"%Y%m%d")
                    # date = date.replace()
                    collectDetail.pubDt = date
                    collectDetail.shortUrl = unique_value
                    collectDetail.sucYN = bool(title and title.strip() and url and url.strip())
                    if collectDetail.sucYN:
                        if contentsCollectHistoryService.insertCategoryCollectHistory(today, contentsOrg, category, collectDetail, session,logger=docker_collect_logger):
                            collect_cnt +=1
                    
                    # break # 키워드 for문 돌릴 때 break임
                    # 오늘 날짜이고 이 페이지의 끝 row이면. 다음 페이지로.
                    if idx == len(trs) - 1:
                        try: # 250806 김현지: 교육부의 경우 페이지네이션 잡아오는 방식이 class 등이 아닌 Xpath
                            if contentsOrg.orgId == 'A0039':
                                page_bar=driver.find_element(By.XPATH, category.COL_HTML_PAGEBAR_TAG)
                            else: page_bar = driver.find_element(By.CLASS_NAME, category.COL_HTML_PAGEBAR_TAG)
                        except:
                            page_bar = driver.find_element(By.ID, category.COL_HTML_PAGEBAR_TAG)
                        if category.COL_HTML_NOW_PAGE_INFO1 == 'tag':
                            now_page = page_bar.find_element(By.TAG_NAME, category.COL_HTML_NOW_PAGE_INFO2).text
                        elif category.COL_HTML_NOW_PAGE_INFO1 == 'class':
                            now_page = page_bar.find_element(By.CLASS_NAME, category.COL_HTML_NOW_PAGE_INFO2).text
                        try:
                            if contentsOrg.orgId == 'A0016':
                                next_page = page_bar.find_element(By.XPATH, f'// *[ @ id = "menu432_obj5442"] / div[2] / form / div / div / ul / li[{int(now_page)+1}] / a')
                            elif contentsOrg.orgId == 'A0013':
                                next_page = page_bar.find_element(By.XPATH, f'// *[ @ id = "menu216_obj4396"] / div[2] / form[3] / div / div / ul / li[{int(now_page)+1}] / a')
                            elif contentsOrg.orgId == 'A0023' and category.cateId == 'B0003':
                                next_page = page_bar.find_element(By.XPATH, f'// *[ @ id = "ctl00_ContentPlaceHolder1_PagingHelper1"] / li[{int(now_page)+3}] / a')
                            elif contentsOrg.orgId == 'A0012' and category.cateId == 'B0001':
                                next_page = page_bar.find_element(By.XPATH, f'//*[@id="contents_body"]/div/div[3]/span/a[{int(now_page)+1}]')
                            elif contentsOrg.orgId == 'A0039':
                                n = int(now_page)%5
                                if n != 0:
                                    n += 3
                                    next_page = page_bar.find_element(By.XPATH, f'//*[@id="txt"]/section/div[3]/div/a[{n}]')
                                else:
                                    next_page_formoe = page_bar.find_element(By.XPATH, f'//*[@id="txt"]/section/div[3]/div/a[8]')
                                    next_page_formoe.click()
                                    time.sleep(3)
                                    # 한번 클릭했으므로 잠깐 쉬었다가 다시 DOM 불러와야 함
                                    page_bar=driver.find_element(By.XPATH, category.COL_HTML_PAGEBAR_TAG)
                                    # 가장 첫 페이지네이션으로 변경
                                    next_page = page_bar.find_element(By.XPATH, f'//*[@id="txt"]/section/div[3]/div/a[3]')                           
                            else:
                                next_page = page_bar.find_element(By.XPATH, f'//*[ text() = {int(now_page) + 1} ]')
                        except:
                            # next_page = page_bar.find_element(By.XPATH, row_data["COL_HTML_URL_ATTR"])
                            next_page = page_bar.find_element(By.CLASS_NAME, 'next')      
            else:  
                    next_page = None
    
        result = {"success" : True , "datetime" : today, "next_page" : next_page}        
    
    except Exception as e:
            docker_collect_logger.error(traceback.format_exc()) 
            next_page = None
            result = {"success" : False , "error" : e,"datetime" : today,"next_page" : next_page} 
    finally:
            return result, collect_cnt
    #else: return "테스트중"
 
# 250827 김현지: kepco, koen 등 우선 삭제, 필요시 원본코드에서 가져와서 활용
