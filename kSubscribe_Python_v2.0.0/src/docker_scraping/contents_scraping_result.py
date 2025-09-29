
import csv
import os
from datetime import datetime, timedelta, timezone
from typing import List
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.logger import Logger
from ksubscribe_share.db.dbmodelV2.contentsVO import SentimentInfo

class ContentsScrapingResult:

    '''
        평판 분석 결과를 csv로 출력하는 클래스. 분석을 위해서 임시로 만듬. 필요없으면 삭제해도 됨. 
    '''    

    mongoManager = MongoManager()
    
    logger = Logger()
    docker_scraping_logger = logger.setup_logger(logger.docker_scraping_logger_name)    

    def __init__(self):
        pass 
    
    def summary_result(self):
        
        # CSV 파일 경로 및 이름 설정
        csv_file = f"docker_scraping/results/summary_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        # CSV 파일 헤더 정의
        headers = [
            "index", "orgId", "cateId", "rawCollectYN", "contentsRaw", "metaSucYN",
            "keywords_string", "predKeywords_string", "shortSummary_string", "longSummary_string"
        ]
        
        try: 
            # 파일이 존재하지 않으면 헤더를 추가
            write_header = not os.path.exists(csv_file)
            
            with open(csv_file, mode="a", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)
                
                # 헤더 추가 (처음 작성 시에만)
                if write_header:
                    writer.writerow(headers)
                
                            
                collection = self.mongoManager.getCollection("contents") 
                
                now = datetime.now() # 실행한 시간을 기점으로 24 시간 전까지만                
                start_of_day = now - timedelta(days=30)                
                query = {
                    "pubDt": {
                        "$gte": start_of_day,
                        "$lte": now
                    },
                    "rawCollectSucYN": "Y",
                    "metaSucYN": "Y"
                    
                }                
                # 조건을 만족하는 여러 문서 반환
                # 수집한 콘텐츠 가져오기            
                cursor = list(collection.find(query).sort("pubDt", -1).limit(100))
                contentsVO_list : List[ContentsVO] = [ContentsVO.from_mongo(item) for item in cursor] 
                
                for index, vo in enumerate(contentsVO_list): 
                    
                    orgId = vo.contentsOrgId
                    cateId = vo.categoryId
                    rawCollectYN = vo.rawCollectSucYN
                    contentsRaw = "" if vo.contentsRaw is None else vo.contentsRaw.contents
                    
                    metaSucYN = vo.metaSucYN
                    
                    keywords_string = None
                    predKeywords_string = None
                    shortSummary_string = None
                    longSummary_string = None
                    sentiments_string = None
                    
                    if vo.contentsMeta is not None:   
                                        
                        if vo.contentsMeta.keywords:
                            keywords_string = ",".join(vo.contentsMeta.keywords)
                        else:
                            keywords_string = ""  # 기본값

                        if vo.contentsMeta.predKeywords:
                            predKeywords_string = ",".join(vo.contentsMeta.predKeywords)
                        else:
                            predKeywords_string = ""  # 기본값                    
                            
                        shortSummary_string =  vo.contentsMeta.shortSummary
                        longSummary_string =  vo.contentsMeta.longSummary
                    
                    # 로그 데이터 추가
                    writer.writerow([
                        index, orgId, cateId, rawCollectYN, contentsRaw, metaSucYN,
                        keywords_string, predKeywords_string, shortSummary_string,
                        longSummary_string
                    ])
                
                    self.docker_scraping_logger.info(f'{index}')

        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def reputation_result(self):
        
        # CSV 파일 경로 및 이름 설정
        csv_file = f"docker_scraping/results/reputation_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        # CSV 파일 헤더 정의
        headers = [
            "line_num", "sourceOrgId", "title", "contents", "orgId", "orgName", "positiveRatio", "negativeRatio", "neutralRatio", "positiveReason", "negativeReason", "positiveKeywords", "negativeKeywords"
        ]
        
        try: 
            # 파일이 존재하지 않으면 헤더를 추가
            write_header = not os.path.exists(csv_file)
            
            with open(csv_file, mode="a", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)
                
                # 헤더 추가 (처음 작성 시에만)
                if write_header:
                    writer.writerow(headers)
                
                            
                collection = self.mongoManager.getCollection("contents") 
                
                now = datetime.now() # 실행한 시간을 기점으로 24 시간 전까지만                
                start_of_day = now - timedelta(days=30)                
                query = {
                    "pubDt": {
                        "$gte": start_of_day,
                        "$lte": now
                    },
                    "rawCollectSucYN": "Y",
                    "metaSucYN": "Y"
                    
                }                
                # 조건을 만족하는 여러 문서 반환
                # 수집한 콘텐츠 가져오기            
                cursor = list(collection.find(query).sort("pubDt", -1).limit(200))
                
                contentsVO_list : List[ContentsVO] = [ContentsVO.from_mongo(item) for item in cursor] 
                
                line_num = 1
                for index, vo in enumerate(contentsVO_list): 
                    
                    sourceOrgId = vo.contentsOrgId
                    #cateId = vo.categoryId
                    contentsRaw = "" if vo.contentsRaw is None else vo.contentsRaw.contents
                    title = vo.title

                    if vo.contentsMeta is not None and vo.contentsMeta.sentiments is not None:                                           
                        sentiments: List[SentimentInfo] =  vo.contentsMeta.sentiments
                        
                        for index2, sentiment in enumerate(sentiments): 
                            orgId = sentiment.orgId
                            orgName = sentiment.orgName
                            positiveRatio = sentiment.positiveRatio
                            negativeRatio = sentiment.negativeRatio
                            neutralRatio = sentiment.neutralRatio
                            positiveReason = sentiment.positiveReason
                            negativeReason = sentiment.negativeReason
                            positiveKeywords = "/".join(sentiment.positiveKeywords)
                            negativeKeywords = "/".join(sentiment.negativeKeywords)
                            
                            writer.writerow([
                                line_num, sourceOrgId, title, contentsRaw, orgId, orgName, positiveRatio, negativeRatio, neutralRatio, positiveReason, negativeReason, positiveKeywords, negativeKeywords
                            ])
                            line_num +=1                

        except Exception as e:
            print(f"An error occurred: {e}")
            return None
     
if __name__ == "__main__":
    dontentsScraping = ContentsScrapingResult()
    dontentsScraping.reputation_result()
    #dontentsScraping.summary_result()
    
    pass

