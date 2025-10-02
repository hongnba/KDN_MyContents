from datetime import date, datetime, timedelta
import re
import pandas as pd
import urllib.request
import traceback
from typing import List
import requests
import json
from sklearn.metrics.pairwise import linear_kernel
from sklearn.feature_extraction.text import TfidfVectorizer
from dateutil.parser import parse

from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO, ContentsOrgCategory
from ksubscribe_share.db.dbmodelV2.contentsCollectHistoryVO import ContentsCollectDetail
from ksubscribe_share.db.service.contentsCollectHistoryService import ContentsCollectHistoryService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.logger import Logger
from ksubscribe_share.utils.random_utils import generate_random_string
from ksubscribe_share.db.mongoManager import MongoManager
import pytz
from ksubscribe_share.db.service.contentsCollectDailyHistoryService import ContentsCollectDailyHistoryService
# OPENAPI 기반 수집 
# G2B
def get_g2b_nara(contentsOrg : ContentsOrgVO, category : ContentsOrgCategory, g2b_keywords: List[str]):
    collect_cnt = 0
    logger = Logger()
    docker_collect_logger = logger.setup_logger(logger.docker_collect_logger_name)
    
    contentsCollectHistoryService = ContentsCollectHistoryService()  # MongoManager 싱글톤 인스턴스를 사용
    contentsOrgService = ContentsOrgService()  # MongoManager 싱글톤 인스턴스를 사용

    # 데이터베이스에서 가져온 문자열을 datetime 객체로 변환
    last_suc_str = category.lastSucYMD 
    last_suc = category.lastSucYMD #datetime.strptime(last_suc_str, "%Y%m%d")
    if isinstance(last_suc_str, str): 
        last_suc = datetime.strptime(category.lastSucYMD, "%Y%m%d") #datetime.strptime(last_suc_str, "%Y%m%d")

    # last_suc 다음 날짜부터 오늘까지의 날짜 리스트 생성
    next_day = last_suc# + timedelta(days=1)
    today = datetime.now(pytz.timezone('Asia/Seoul'))    #today.
    date_list = [(next_day + timedelta(days=x)).strftime("%Y%m%d") for x in range((today - next_day).days + 1)]    
    today = today.strftime("%Y%m%d")
    lastSucYMD = today 
    
    docker_collect_logger.info(f'get_g2b_nara : {contentsOrg.orgName}({contentsOrg.orgId}) {category.cateName}({category.cateId}) 수집 시작')
    docker_collect_logger.info(f'g2b_keywords :  {g2b_keywords}')
    
    #mongoManager = MongoManager() 
    #session = mongoManager.client.start_session()  
  
    try:
        # 트랜잭션 시작
        # session.start_transaction()        
        
        visited = []
        no_dict = set()
        dupl = True
        categories = ['입찰공고']
        service_key = category.APIKEY1
        url = None
        for date in date_list:
            docker_collect_logger.info(f'나라장터 , {date} ')
            cate_dupl = True
            
            for key_word in g2b_keywords:
                if key_word is None or key_word == '' or key_word.isspace() or key_word == 'ALL':
                    continue
                
                docker_collect_logger.debug(f'key_word : , {key_word} ' )
                
                url = f'{category.collectUrlInfo}&serviceKey={service_key}&inqryBgnDt={date}0000&inqryEndDt={date}2359&bidNtceNm={key_word}'
                headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"}
                success = False
                
                for i in range(5):

                    docker_collect_logger.debug(f'==나라장터 {key_word} try count:[{i+1}]')
                    try:
                        response = requests.get(url, verify=False)
                        success = True
                        docker_collect_logger.debug(f'==나라장터 {key_word} try count:[{i+1}] 성공')
                    except Exception as e:
                        docker_collect_logger.debug(f'==나라장터 {key_word} try count:[{i+1}] => exception:\n{e}')
                    if success == True:
                        break 
                contents = response.text
                docker_collect_logger.info(contents)
                json_ob = json.loads(contents)
                if json_ob['response']['header']['resultCode']=='00':
                    if json_ob['response']['body']['totalCount'] != 0:
                        body = json_ob['response']['body']['items']
                        body.reverse()
                        for idx, item in enumerate(body):
                            if item['bidNtceNo'] not in no_dict:

                                try:
                                    price = str(format(int(item['presmptPrce'])+int(item['VAT']), ',d'))+'원'
                                except:
                                    price = '금액정보없음'
                                # +'('+item['ntceKindNm']+')('+item['dminsttNm']+', '+price+'원)
                                title = item['bidNtceNm']
                                if len(title) >= 50:
                                    title = title[:50] + '...'

                                unique_value = generate_random_string(5)
   
                                collectDetail = ContentsCollectDetail() 
                                collectDetail.url = item['bidNtceDtlUrl']
                                collectDetail.title = title+'('+item['ntceKindNm']+')('+item['dminsttNm']+', '+price+')'
                                collectDetail.pubDt = date
                                collectDetail.shortUrl = unique_value
                                collectDetail.sucYN = bool(title and title.strip() and url and url.strip())
                                if collectDetail.sucYN:                                    
                                    if contentsCollectHistoryService.insertCategoryCollectHistory(  today, contentsOrg, category, collectDetail,logger=docker_collect_logger):
                                        collect_cnt +=1
                                no_dict.add(item['bidNtceNo'])
                                dupl = False
                                cate_dupl = False
                    else:
                        continue
                else:
                    err_code = json_ob['response']['header']['resultCode']
                    today = datetime.utcnow().replace(tzinfo=pytz.utc)
                    result = {"success" : False , "error" : int(err_code),"datetime" : today}

        contentsOrgService.updateCategorySucYMD(contentsOrg.orgId, category.cateId, True, lastSucYMD,logger=docker_collect_logger)

        # 트랜잭션 커밋
        #session.commit_transaction()
        #docker_collect_logger.debug("트랜잭션 커밋 성공!")
        docker_collect_logger.info(f'get_g2b_nara : {contentsOrg.orgName}({contentsOrg.orgId}) {category.cateName}({category.cateId}) 수집 완료 (건수 : {collect_cnt})')
        today = datetime.utcnow().replace(tzinfo=pytz.utc)
        result = {"success" : True ,"datetime" : today}
    except Exception as e:
        docker_collect_logger.info(f'get_g2b_nara : {contentsOrg.orgName}({contentsOrg.orgId}) {category.cateName}({category.cateId}) 수집 오류 (건수 : {collect_cnt})')
        docker_collect_logger.error(traceback.format_exc())
        today = datetime.utcnow().replace(tzinfo=pytz.utc)
        result = {"success" : False , "error" : e,"datetime" : today, "url":url}
        # 예외 발생 시 트랜잭션 롤백
        #session.abort_transaction()
        #docker_collect_logger.debug(f'트랜잭션 롤백: {e}')      

    return result

def get_naver_news(providerOrgId:str, contentsOrg : ContentsOrgVO, category : ContentsOrgCategory):
    collect_cnt = 0
    logger = Logger()
    docker_collect_logger = logger.setup_logger(logger.docker_collect_logger_name)
       
    contentsCollectHistoryService = ContentsCollectHistoryService()  # MongoManager 싱글톤 인스턴스를 사용
    contentsOrgService = ContentsOrgService()  # MongoManager 싱글톤 인스턴스를 사용

    # 데이터베이스에서 가져온 문자열을 datetime 객체로 변환
    last_suc_str = category.lastSucYMD

    last_suc = category.lastSucYMD#datetime.strptime(last_suc_str, "%Y%m%d")
    # # test-------------
    # tz = pytz.timezone('Asia/Seoul')
    # if isinstance(last_suc_str, str): 
    #     last_suc = datetime.strptime(category.lastSucYMD, "%Y%m%d") #datetime.strptime(last_suc_str, "%Y%m%d")
    # last_suc.replace(tzinfo=pytz.utc)
    # last_suc = tz.localize(last_suc)
    # #tetss-------------
    # last_suc 다음 날짜부터 오늘까지의 날짜 리스트 생성
    # last_suc = datetime.strptime(last_suc,"%Y%m%d").replace(hour=0,minute=0,second=0,microsecond=0)

    next_day = last_suc + timedelta(days=1)
    
    #today = datetime.now()
    today = datetime.utcnow().replace(tzinfo=pytz.utc)    #today.
    lastSucYMD = today 

    date_list = [(next_day + timedelta(days=x)).strftime("%Y%m%d") for x in range((today - next_day).days + 1)]
    #today = today.strftime("%Y%m%d")
    #lastSucYMD = today 
    
    docker_collect_logger.info(f'get_naver_news : {contentsOrg.orgName}({contentsOrg.orgId}) {category.cateName}({category.cateId}) 수집 시작')

    #mongoManager = MongoManager()
    #session_options = {"maxTransactionLockRequestTimeoutMillis": 300000} 
    #session = mongoManager.client.start_session(options=session_options)  
    try:
        
        data = {
            '기관명':[],
            '분류명':[],
            '제목':[],
            '관련 URL':[]
                }
        naver_df = pd.DataFrame(data)
        naver_df=naver_df.rename_axis(columns='순번')

        df = pd.DataFrame(data)
        df=df.rename_axis(columns='순번')

        #orgKeyword와 categoryKeyword로 일단 수집한다. 
        naver_key_words = contentsOrg.orgKeywordList + category.keywords            
        naver_key_words = set(naver_key_words)
        
        for idx, key_word in enumerate(naver_key_words):

            docker_collect_logger.info(f'get_naver_news : key_word - {key_word}')

            # None이거나 ''이거나 '  ' 이거나 ALL이면 실행안함
            if key_word is None or key_word == '' or key_word.isspace() or key_word == 'ALL':
                continue
            query = urllib.parse.quote(key_word)
            docker_collect_logger.debug('####### query : {query}')
            # url = f'https://openapi.naver.com/v1/search/news.json?query={query}&display=100&start=1&sort=sim'
            url = category.collectUrlInfo + query

            request = urllib.request.Request(url)
            request.add_header('X-Naver-Client-Id', category.APIKEY1)
            request.add_header('X-Naver-Client-Secret', category.APIKEY2)
            response = urllib.request.urlopen(request)
            rescode = response.getcode()

            if rescode == 200:
                response_body = response.read()
                response_dict = json.loads(response_body.decode('utf-8'))
                items = response_dict['items']
                for items_index in range(len(items)):
                    remove_tag = re.compile('<.*?>')
                    title = re.sub("&(.*?);", "", items[items_index]['title'].replace("<b>", "").replace("</b>", ""))
                    description = re.sub("&(.*?);", "", items[items_index]['description'].replace("<b>", "").replace("</b>", ""))
                    link = items[items_index]['originallink']
                    naverlink = items[items_index]['link']
                    date = items[items_index]['pubDate']
                    #date = parse(date).strftime('%Y%m%d')
                    
                    date = parse(date).replace(tzinfo=pytz.timezone('Asia/Seoul'))#.strftime('%Y%m%d')
                    last_suc_ymd = datetime(last_suc.year,last_suc.month,last_suc.day)
                    pubDt_ymd = datetime(date.year,date.month,date.day)

                    # pubDt_datetime = pytz.utc.localize(datetime.strptime(date,'%Y%m%d'))
                    # pubDt_datetime
                    #last_suc.replace(tz) 
                    # 하루에 여러번 돌리므로 비교연산자 (<=)사용
                    if last_suc_ymd <= pubDt_ymd:
                        if key_word in title:
                            new_data = {
                                '기관명':'NAVER',
                                '분류명':key_word,
                                '제목':title,
                                'content':description,
                                '관련 URL':link,
                                '네이버 URL':naverlink,
                                '발행 날짜': pubDt_ymd.astimezone(pytz.utc)
                            }
                            # 24.11.28 주석
                            # naver_df = naver_df.append(new_data, ignore_index=True)
                            # 24.11.28 추가
                            naver_df = pd.concat([naver_df, pd.DataFrame([new_data])], ignore_index=True)

                            docker_collect_logger.debug(f'{date}, {title}')
            else: 
                today = datetime.utcnow().replace(tzinfo=pytz.utc)
                result = {"success" : False , "error" : rescode,"datetime" : today}
                return result  


        # 트랜잭션 시작
        #session = mongoManager.client.start_session()  
        #session.start_transaction()                    
        # naver_df에서 관련기사 제거
        if len(naver_df) > 0 :
            # TfidfVectorizer()를 이용하여 단어별 가중치 데이터를 추가함
            tfidf = TfidfVectorizer()
            tfidf_matrix = tfidf.fit_transform(naver_df['content'].values.astype('U'))
            tfidf_matrix2 = tfidf.fit_transform(naver_df['제목'].values.astype('U'))
            # print('tfidf_matrix : ', tfidf_matrix)
            n = len(naver_df['content'])
            docker_collect_logger.debug(f'n :, {n}')

            # 코사인 함수 구하기 tfidf_matrix와 tfidf_matrix를  곱하여 코사인 함수를 구함
            cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)
            cosine_sim2 = linear_kernel(tfidf_matrix2, tfidf_matrix2)
            # print('cosine_sim : ')
            # print(cosine_sim)

            num = []
            i = 0
            j = 0
            l = []
            cosine_sim[i][j]

            for i in range(n): 
                for j in range(1, n):
                    # if i == 0 or i == 9:
                    # print(i, j)
                    # print('내용 유사도 : ', cosine_sim[i][j])
                    # print('제목 유사도 : ', cosine_sim2[i][j])
                    # print('--------------')

                    if cosine_sim[i][j] >= 0.15 or cosine_sim2[i][j] >= 0.15:

                        if i < j: # i: 최신기사 j: i보다 먼저 나온 기사(나중기사)
                            num.append(j) # j를 append함
                            l.append([i, j])
                            # print(i, j)
                            # print(cosine_sim[i][j])

            new_ = []
            for v in num:
                if v not in new_:
                    new_.append(v)
                    
            # new_리스트 값(중복된 기사 인덱스)을 drop
            article = naver_df.drop(index=new_)
            df = pd.concat([df, article])
            for idx, row in df.iterrows():
                docker_collect_logger.debug("dd"+str(idx))  
                unique_value = generate_random_string(5)
                title = row["제목"]
                url = row["관련 URL"]
                naverUrl = row["네이버 URL"]
                pubDt = row['발행 날짜']
                key_word = row['분류명']                
                shortUrl = unique_value
                sucYN = bool(title and title.strip() and url and url.strip())
                collectionDate = today

                collectDetail = ContentsCollectDetail() 
                collectDetail.url = url
                collectDetail.title = title
                collectDetail.pubDt = pubDt
                collectDetail.shortUrl = shortUrl
                collectDetail.naverUrl = naverUrl
                collectDetail.sucYN = bool(title and title.strip() and url and url.strip())                
                if collectDetail.sucYN:
                    if contentsCollectHistoryService.insertCategoryCollectHistory( today, contentsOrg, category, collectDetail,keyword=key_word,logger=docker_collect_logger):
                        collect_cnt +=1 

        #네이버에 한해서 필요없어 보임 
        sucYN = True
        today = datetime.utcnow().replace(tzinfo=pytz.utc)
        
        contentsOrgService.updateCategorySucYMD(contentsOrg.orgId, category.cateId, sucYN, lastSucYMD,logger=docker_collect_logger)
        
        # 트랜잭션 커밋
        #session.commit_transaction()
        #docker_collect_logger.debug("트랜잭션 커밋 성공!")
        if collect_cnt > 0:
            docker_collect_logger.info(f'get_naver_news : {contentsOrg.orgName}({contentsOrg.orgId}) {category.cateName}({category.cateId}) 수집 완료 (건수 : {collect_cnt})')
            contentsOrgService.updateCategorySucYMD(contentsOrg.orgId, category.cateId, True, lastSucYMD, logger=docker_collect_logger)
            result = {"success" : True ,"datetime" : today}
        else :
            docker_collect_logger.info(f'get_naver_news : {contentsOrg.orgName}({contentsOrg.orgId}) {category.cateName}({category.cateId}) 수집 실패(0건) -> lastSucYMD 미갱신')
            contentsOrgService.updateCategorySucYMD(contentsOrg.orgId, category.cateId, False, None, logger=docker_collect_logger)
            result = {"success" : True ,"datetime" : today}
    except Exception as e:
        
        if collect_cnt > 0:
            docker_collect_logger.info(f'get_naver_news : {contentsOrg.orgName}({contentsOrg.orgId}) {category.cateName}({category.cateId}) 부분 수집 완료 (건수 : {collect_cnt})')
            contentsOrgService.updateCategorySucYMD(contentsOrg.orgId, category.cateId, True, lastSucYMD, logger=docker_collect_logger)
            result = {"success" : True ,"datetime" : today}
        else:
            docker_collect_logger.info(f'get_naver_news : {contentsOrg.orgName}({contentsOrg.orgId}) {category.cateName}({category.cateId}) 수집 오류')
            docker_collect_logger.error(traceback.format_exc())
            result = {"success" : False , "error" : e,"datetime" : today}
        # 예외 발생 시 트랜잭션 롤백
        #session.abort_transaction()
        #docker_collect_logger.debug(f'트랜잭션 롤백: {e}')   
             
    return result
    
    