from datetime import date, datetime, timedelta
import feedparser
import re
import pandas as pd
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO, ContentsOrgCategory
from ksubscribe_share.db.dbmodelV2.contentsCollectHistoryVO import ContentsCollectDetail
from ksubscribe_share.db.service.contentsCollectHistoryService import ContentsCollectHistoryService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.logger import Logger
from ksubscribe_share.utils.random_utils import generate_random_string
from ksubscribe_share.db.mongoManager import MongoManager
import traceback
import pytz
# RSS
def get_contents_by_rss(contentsOrg : ContentsOrgVO, category : ContentsOrgCategory):
    collect_cnt = 0
    logger = Logger()
    docker_collect_logger = logger.setup_logger(logger.docker_collect_logger_name)
 
    contentsCollectHistoryService = ContentsCollectHistoryService()  # MongoManager 싱글톤 인스턴스를 사용
    contentsOrgService = ContentsOrgService()  # MongoManager 싱글톤 인스턴스를 사용

    # 데이터베이스에서 가져온 문자열을 datetime 객체로 변환
    last_suc_str = category.lastSucYMD 
    last_suc = category.lastSucYMD #datetime.strptime(last_suc_str, "%Y%m%d")

    # last_suc 다음 날짜부터 오늘까지의 날짜 리스트 생성
    next_day = last_suc# + timedelta(days=1)
    #today = datetime.now()
    today = datetime.now(pytz.timezone('Asia/Seoul'))    #today.
    date_list = [(next_day + timedelta(days=x)).strftime("%Y%m%d") for x in range((today - next_day).days + 1)]
    todayYMD = today.strftime("%Y%m%d")
    # lastSucYMD = todayYMD 
    lastSucYMD = today 
    
    if(contentsOrg.orgId == "A0024"):
        print(f"{contentsOrg.orgId}")
    
    docker_collect_logger.info(f'get_contents_by_rss : {contentsOrg.orgName}({contentsOrg.orgId}) {category.cateName}({category.cateId}) 수집 시작')
    

    #mongoManager = MongoManager()
    #session_options = {"maxTransactionLockRequestTimeoutMillis": 300000} 
    #session = mongoManager.client.start_session(options=session_options)  
    #session = mongoManager.client.start_session()  

       
    try:
        # 트랜잭션 시작
        #session.start_transaction()        
        
        if contentsOrg.orgId != 'A0024':
            f = feedparser.parse(category.collectUrlInfo)
        else:
            f = feedparser.parse(category.collectUrlInfo+'?dt='+todayYMD)
        articles = f['entries']
     
        sucYN = False
        for article in articles:
            if contentsOrg.orgName == '국토교통부':
                colDt = re.sub(r'[^0-9]', '', article.updated)
            else:
                colDt = re.sub(r'[^0-9]', '', article.published)[:8] # 250430 mafra
            docker_collect_logger.info(colDt)
            #docker_collect_logger.debug(re.sub(r'[^0-9]', '', article.published))
            if len(date_list) == 0:
                sucYN = True
            if colDt in date_list:
                unique_value = generate_random_string(5)
                
                title = article.title
                url = article.link
                shortUrl = unique_value
                sucYN = bool(title and title.strip() and url and url.strip())
                publishedDate = colDt

                collectDetail = ContentsCollectDetail() 
                collectDetail.url = url
                collectDetail.title = title
                collectDetail.pubDt = publishedDate
                collectDetail.shortUrl = shortUrl
                collectDetail.sucYN = bool(title and title.strip() and url and url.strip())
                if collectDetail.sucYN: 
                    if contentsCollectHistoryService.insertCategoryCollectHistory(today, contentsOrg, category, collectDetail,logger=docker_collect_logger):
                        collect_cnt +=1
        # contentsOrgService.updateCategorySucYMD(contentsOrg.orgId, category.cateId, sucYN, lastSucYMD,logger=docker_collect_logger)
        today = datetime.utcnow().replace(tzinfo=pytz.utc)
        
        # 트랜잭션 커밋
        #session.commit_transaction()
        #docker_collect_logger.debug("트랜잭션 커밋 성공!")
        if(collect_cnt > 0):
            docker_collect_logger.info(f'get_contents_by_rss : {contentsOrg.orgName}({contentsOrg.orgId}) {category.cateName}({category.cateId}) 수집 완료 (건수 : {collect_cnt}), lastSucYMD 갱신: {lastSucYMD}')
            contentsOrgService.updateCategorySucYMD(contentsOrg.orgId, category.cateId, True, lastSucYMD, logger=docker_collect_logger)
            result = {"success" : True ,"datetime" : today}
        else:
            docker_collect_logger.info(f'get_contents_by_rss : {contentsOrg.orgName}({contentsOrg.orgId}) {category.cateName}({category.cateId}) 수집 완료(0건) -> lastSucYMD 미갱신')
            contentsOrgService.updateCategorySucYMD(contentsOrg.orgId, category.cateId, False, lastSucYMD, logger=docker_collect_logger)
            result = {"success" : True ,"datetime" : today}
    except Exception as e:
        if(collect_cnt > 0):
            docker_collect_logger.info(f'get_contents_by_rss : {contentsOrg.orgName}({contentsOrg.orgId}) {category.cateName}({category.cateId}) 부분 수집 완료 (건수 : {collect_cnt}), lastSucYMD 갱신: {lastSucYMD}')
            contentsOrgService.updateCategorySucYMD(contentsOrg.orgId, category.cateId, True, lastSucYMD, logger=docker_collect_logger)
            result = {"success" : True ,"datetime" : today}
        else:
            docker_collect_logger.info(f'get_contents_by_rss : {contentsOrg.orgName}({contentsOrg.orgId}) {category.cateName}({category.cateId}) 수집 실패')
            docker_collect_logger.error(traceback.format_exc())
            result = {"success" : False , "error" : e,"datetime" : today}
        # 예외 발생 시 트랜잭션 롤백
        #session.abort_transaction()
        #docker_collect_logger.debug(f'트랜잭션 롤백: {e} ')        
    #finally:
        # 세션 종료
        #session.end_session()    
    return result 