
from bson import ObjectId
#import datetime
from typing import List
from urllib.parse import urlparse
import json
from pymongo import DESCENDING
from datetime import datetime, timedelta
import re
import pytz

from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO, ContentsRaw, ContentsMeta,SentimentInfo
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService

#컨텐츠 수집 이력 
class ContentsService():

    mongoManager = MongoManager()  # MongoManager 싱글톤 인스턴스를 사용
    collectionName = "contents"
    
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ContentsService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        pass
    #--------------------------------------------------------------------------------------------------------------
    #return True/False 함수 
    def isExistContents(self, url):
        # contents 에서 
        result = self.findByURL(url)
        if result:
            return True
        return False

    #--------------------------------------------------------------------------------------------------------------
    #find/select/search/get 함수
    
    def find_domain_by_org_cate(self,org_cate_hash:tuple):
        org_index = 0
        cate_index = 1
    
        org_id = org_cate_hash[org_index]
        cate_id = org_cate_hash[cate_index]
        
        collection = self.mongoManager.getCollection(ContentsVO.collectionName)
        result = list(collection.find({"contentsOrgId":org_id,"categoryId":cate_id}))
        return result
        

    def find_naver_newdomain(self):
        collection = self.mongoManager.getCollection(ContentsVO.collectionName)
        
        # MongoDB에서 categoryId가 "B0010"인 문서들의 url 필드 가져오기
        results = list(collection.find({"categoryId": "B0010"}, {"url": 1, "_id": 0}))
        
        # 도메인만 추출
        domains = set()  # 중복 제거를 위해 set 사용
        for result in results:
            if "url" in result:
                parsed_url = urlparse(result["url"])
                domain = parsed_url.netloc  # 도메인 추출
                if domain:
                    domains.add(domain)

        return list(domains)  # 결과를 리스트로 변환하여 반환



    def find_first_url_by_domain(self, domain: str) -> str:
        """주어진 도메인의 첫 번째 문서의 URL을 조회하고 반환"""
        
        collection = self.mongoManager.getCollection(ContentsVO.collectionName)

        try:
            # domain 값 검증
            if not domain or not isinstance(domain, str):  
                raise ValueError(f"Invalid domain value: {domain}")

            # https:// 또는 http:// 모두 수용하는 정규식
            regex_pattern = re.compile(rf"^https?://{re.escape(domain)}", re.IGNORECASE)
            
            # 도메인이 일치하는 첫 번째 문서 찾기
            result = collection.find_one({"url": {"$regex": regex_pattern}}, {"url": 1, "_id": 0})

            if result and "url" in result:
                return result["url"]  # ✅ URL만 반환
            else:
                print(f"해당 도메인({domain})의 데이터가 없습니다.")
                return None

        except Exception as e:
            print(f"An error occurred: {e}")
            return None


          
                          
    
    def find_sorted_contents(self,limit_cnt:int):
        collection = self.mongoManager.getCollection(ContentsVO.collectionName)
        latest_contents = list(collection.find().sort("collectDt",DESCENDING).limit(limit_cnt))
        return latest_contents

    def findByURL(self,url):
        collection = self.mongoManager.getCollection(ContentsVO.collectionName)
        filter = {"url": url}
        return  collection.find_one(filter)
    
    def findContentsByv1ContentsIdx(self, v1ContentsIdx:int) -> str:
        try: 
            collection = self.mongoManager.getCollection(self.collectionName) 
            # MongoDB 업데이트 쿼리 구성
            filter_query = {
                "v1ContentsIdx": v1ContentsIdx
            }
            # 반환할 필드 지정 
            projection = {
                "_id": 1
            }
            
            # 조건을 만족하는 여러 문서 반환
            document = collection.find_one(filter_query, projection)

            # code 반환 (결과가 없을 경우 None 반환)
            return str(document["_id"]) if document else None
        
        
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def findTodayOrgContents(self, org_list):#: list[str]
        try:
            start_of_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            start_of_day = start_of_day - timedelta(days=10)
            current_time = datetime.now()
            
            collection = self.mongoManager.getCollection(self.collectionName) 
            
            query = {
                "collectDt": {
                    "$gte": start_of_day
                    # "$lte": current_time
                },
                "contentsOrgId": {"$in": org_list}
            }
            # 반환할 필드 지정 
            projection = {
                "_id": 1,
                "title": 1,
                "url": 1,
            }
            
            # 조건을 만족하는 여러 문서 반환
            results = list(collection.find(query))

            # 결과 반환 (결과가 없을 경우 None 반환)
            return results if results else None
        
        
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def findTodayContents(self, past_day: int):
        try:
            now = datetime.now() # 실행한 시간을 기점으로 24 시간 전까지만
            
            start_of_day = now - timedelta(days=past_day)
            # current_time = datetime.now()
            
            collection = self.mongoManager.getCollection(self.collectionName) 
            
            query = {
                "collectDt": {
                    "$gte": start_of_day,
                    "$lte": now
                },
            } 
            
            print(f"검색 시간 :  {start_of_day} ~  {now}")
            print(f"검색 쿼리 :  {query}")

            # 조건을 만족하는 여러 문서 반환
            results = list(collection.find(query))

            print(f"컨텐츠 개수 :  {len(results)}")

            result_list = [ContentsVO.from_mongo(item) for item in results] 
            
            # 결과 반환 (결과가 없을 경우 None 반환)
            return result_list if result_list else None
 
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
        
    def findTodaySucFalseContents(self,start_date,end_date):
        try:
            collection = self.mongoManager.getCollection(self.collectionName) 
            query = {
                "rawCollectSucYN": {"$in": [None, "N"],}  ,
                "pubDt": {
                    "$gte": start_date,
                    "$lte": end_date
                },                              # None이거나 "N"이거나 존재하지 않는 경우
            } 
            # 조건을 만족하는 여러 문서 반환 
            results = list(collection.find(query)) 
            result_list = [ContentsVO.from_mongo(item) for item in results] 
            return result_list
                
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def findContents_rawCollectSucYN_is_false(self, limit) ->List[ContentsVO]:
        try:
            
            collection = self.mongoManager.getCollection(self.collectionName) 

            query = {
                "rawCollectSucYN": {"$in": [None, "N"]}  # None이거나 "N"이거나 존재하지 않는 경우
            }
            
            # 조건을 만족하는 여러 문서 반환
            if limit < 0: 
                results = list(collection.find(query))
            else: 
                results = list(collection.find(query).limit(limit))
                
            result_list = [ContentsVO.from_mongo(item) for item in results] 
            return result_list
                
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def findContents_rawCollectSucYN_is_true(self, limit) ->List[ContentsVO]:
        try:
            
            collection = self.mongoManager.getCollection(self.collectionName) 
            # 2일전 ,
            #date = datetime.now()-timedelta(days=2)
            query =  {#"collectDt":{"$gte":date},
                      "rawCollectSucYN": "Y" ,
                      "metaSucYN": {"$in":["N",None]} }
                #"rawCollectSucYN": "Y"  # None이거나 "N"이거나 존재하지 않는 경우
            
            # 조건을 만족하는 여러 문서 반환
            if limit < 0: 
                results = list(collection.find(query))
            else: 
                results = list(collection.find(query).limit(limit))
                
            result_list = [ContentsVO.from_mongo(item) for item in results] 
            return result_list
                
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def findSucRawContents(self,start_date,end_date,sucYN:str):
        try:
            collection = self.mongoManager.getCollection(self.collectionName) 
            query = {
                "rawCollectSucYN": sucYN,
                "metaSucYN": {"$in":["N",None]}  ,
                "pubDt": {
                    "$gte": start_date,
                    "$lte": end_date
                },                              # None이거나 "N"이거나 존재하지 않는 경우
            } 
            # 조건을 만족하는 여러 문서 반환 
            results = list(collection.find(query)) 
            result_list = [ContentsVO.from_mongo(item) for item in results] 
            return result_list
                
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
        


    def distinctOrgIdAndCateId(self):

        try:

            collection = self.mongoManager.getCollection(self.collectionName)

            pipeline = [
                {
                    "$group": {
                        "_id": {"contentsOrgId": "$contentsOrgId", "categoryId": "$categoryId"}
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "contentsOrgId": "$_id.contentsOrgId",
                        "categoryId": "$_id.categoryId",
                    }
                }
            ]
            # 결과 출력
            result = list(collection.aggregate(pipeline))
            print("Distinct pairs of contentsOrgId and categoryId:")
            for pair in result:
                print(pair)

        except Exception as e:
            print(f"An error occurred: {e}")


    #--------------------------------------------------------------------------------------------------------------
    #insert함수
                  
    def insert_contents_todebugcollection(self,contentsVO:ContentsVO):
        
        collection = self.mongoManager.getCollection("contents_debug")
        return collection.insert_one(contentsVO.to_mongo())
        
        
    # def insert_contents(self,queue_contents:ContentsQueueVO,result_analysis):
    #     contents = ContentsVO()
    #     # queue_contents
    #     contents.title = queue_contents.title
    #     contents.url = queue_contents.url
    #     contents.contentsOrgId = queue_contents.contentOrgId
    #     contents.categoryId = queue_contents.cateId
    #     contents.pubDt = queue_contents.pubDt
    #     contents.collectDt = queue_contents.collectDt
        
    #     # raw collect sucYN (Collect 성공 여부, )
    #     contents.rawCollectSucYN = 'Y'
    #     contents.contentsRaw = ContentsRaw(
    #         title = queue_contents.title,
    #         contents="",
    #         image="",
    #         errorInfo=""
    #     )
    #     contents.rawCollectDt = queue_contents.collectDt
    #     contents.metaAnalyzeDt = result_analysis['datetime']
    #     # meta data
    #     if result_analysis["success"]:
    #         result_analysis["data"] = result_analysis["data"].replace("`","")
    #         result_analysis["data"] = result_analysis["data"].replace("json","")
    #         result_analysis["data"] = json.loads(result_analysis["data"])
    #         sentiment_list = []
    #         for index, item in enumerate(result_analysis["data"]["sentiment"]["organization"]):
    #             orgName=result_analysis["data"]["sentiment"]["organization"][index]
    #             org = ContentsOrgService().findOrgbyName(orgName)
    #             org_id = None
    #             if org:
    #                 org_id = org.orgId
    #             else:
    #                 org_id = "not found"
    #             sentiment =SentimentInfo(
    #                 orgId=org_id,
    #                 orgName=orgName,#result_analysis["data"]["sentiment"]["organization"][index],
    #                 positiveRatio=result_analysis["data"]["sentiment"]["positiveRatio"][index],
    #                 negativeRatio=result_analysis["data"]["sentiment"]["negativeRatio"][index],
    #                 reason=result_analysis["data"]["sentiment"]["reason"][index],)
    #             sentiment_list.append(sentiment) 
    #         contents.metaSucYN = "Y"            
    #         contents.contentsMeta = ContentsMeta(
    #             keywords = result_analysis["data"]["keyword"],
    #             predKeywords = result_analysis["data"]["predkeywords"],
    #             shortSummary = result_analysis["data"]["short_summary"],
    #             longSummary = result_analysis["data"]["long_summary"],
    #             sentiments= sentiment_list,#result_analysis["data"]["sentiment"],
    #             )
    #     else:
    #         contents.metaSucYN = "N"
    #         contents.contentsMeta = ContentsMeta(
    #             errorInfo = result_analysis["errorInfo"]
    #         ) 

        
    #     mongo = contents.to_mongo()
    #     collection = self.mongoManager.getCollection(self.collectionName)
    #     return collection.insert_one(contents.to_mongo())
                

    #--------------------------------------------------------------------------------------------------------------
    #update함수
    
    # def update_contents_analysis(self,contents_queue,result_analysis):
    #     collection = self.mongoManager.getCollection(self.collectionName) 
    #     url = contents_queue.url
    #     contents_meta = None        
           
    #     #1. result to contentsMetaVO 
    #     try:
    #         if result_analysis["success"]:
    #             result_analysis["data"] = result_analysis["data"].replace("`","")
    #             result_analysis["data"] = result_analysis["data"].replace("json","")
    #             result_analysis["data"] = json.loads(result_analysis["data"])
    #             sentiment_list = []
    #             for index, item in enumerate(result_analysis["data"]["sentiment"]["organization"]):
                    
    #                 orgName=result_analysis["data"]["sentiment"]["organization"][index]
    #                 org = ContentsOrgService().findOrgbyName(orgName)
    #                 sentiment =SentimentInfo(
    #                     orgId=org.orgId,
    #                     orgName=orgName,#result_analysis["data"]["sentiment"]["organization"][index],
    #                     positiveRatio=result_analysis["data"]["sentiment"]["positiveRatio"][index],
    #                     negativeRatio=result_analysis["data"]["sentiment"]["negativeRatio"][index],
    #                     reason=result_analysis["data"]["sentiment"]["reason"][index],)
    #                 sentiment_list.append(sentiment) 
    #             contents_meta = ContentsMeta(
    #                 keywords = result_analysis["data"]["keyword"],
    #                 predKeywords = result_analysis["data"]["predkeywords"],
    #                 shortSummary = result_analysis["data"]["short_summary"],
    #                 longSummary = result_analysis["data"]["long_summary"],
    #                 sentiments= sentiment_list,#result_analysis["data"]["sentiment"],
    #             )
    #         else: 
    #             # 에러 디비 저장
    #             contents_meta = ContentsMeta(
    #                 errorInfo= result_analysis["data"]#
    #             )
    #     except Exception as e : 
    #         return None 
    #     #2. save result
    #     try:
    #         result = collection.update_one(         
    #             {"url": url},
    #             {"$set" :
    #             {
    #             "contentsMeta":contents_meta.to_mongo() ,
    #             "metaAnalyzeDt" : result_analysis["datetime"].strftime(
    #                 "%Y-%m-%dT%H:%M:%S."
    #             )  
    #             }, 
    #             } 
    #         )
    #         return True
            
    #     except Exception as e :
    #         # DB 저장 실패 Log
    #         return None

    def fill_orgname_catename(self): 
        
        collection = self.mongoManager.getCollection(self.collectionName) 
        
        # 조건에 맞는 문서의 name 필드를 업데이트
        result = collection.update_many({"contentsOrgId": "A0001"},  {"$set": {"contentsOrgName": "산업통상자원부"}} )
        result = collection.update_many({"contentsOrgId": "A0002"},  {"$set": {"contentsOrgName": "개인정보보호위원회"}} )
        result = collection.update_many({"contentsOrgId": "A0003"},  {"$set": {"contentsOrgName": "과학기술정보통신부"}} )
        result = collection.update_many({"contentsOrgId": "A0004"},  {"$set": {"contentsOrgName": "나라장터"}} )
        result = collection.update_many({"contentsOrgId": "A0005"},  {"$set": {"contentsOrgName": "한국에너지기술평가원"}} )
        result = collection.update_many({"contentsOrgId": "A0006"},  {"$set": {"contentsOrgName": "한국인터넷진흥원"}} )
        result = collection.update_many({"contentsOrgId": "A0007"},  {"$set": {"contentsOrgName": "한국산업기술진흥원"}} )
        result = collection.update_many({"contentsOrgId": "A0008"},  {"$set": {"contentsOrgName": "한국지능정보사회진흥원"}} )
        result = collection.update_many({"contentsOrgId": "A0009"},  {"$set": {"contentsOrgName": "산업기술 R&D 정보포털"}} )
        result = collection.update_many({"contentsOrgId": "A0010"},  {"$set": {"contentsOrgName": "한국전력공사(주)"}} )
        result = collection.update_many({"contentsOrgId": "A0011"},  {"$set": {"contentsOrgName": "한국수력원자력(주)"}} )
        result = collection.update_many({"contentsOrgId": "A0012"},  {"$set": {"contentsOrgName": "한국전력거래소"}} )
        result = collection.update_many({"contentsOrgId": "A0013"},  {"$set": {"contentsOrgName": "한국남부발전(주)"}} )
        result = collection.update_many({"contentsOrgId": "A0014"},  {"$set": {"contentsOrgName": "한국남동발전(주)"}} )
        result = collection.update_many({"contentsOrgId": "A0015"},  {"$set": {"contentsOrgName": "한국중부발전(주)"}} )
        result = collection.update_many({"contentsOrgId": "A0016"},  {"$set": {"contentsOrgName": "한국서부발전(주)"}} )
        result = collection.update_many({"contentsOrgId": "A0017"},  {"$set": {"contentsOrgName": "한국동서발전(주)"}} )
        result = collection.update_many({"contentsOrgId": "A0018"},  {"$set": {"contentsOrgName": "한전KDN(주)"}} )
        result = collection.update_many({"contentsOrgId": "A0019"},  {"$set": {"contentsOrgName": "한국전력기술(주)"}} )
        result = collection.update_many({"contentsOrgId": "A0020"},  {"$set": {"contentsOrgName": "한전KPS(주)"}} )
        result = collection.update_many({"contentsOrgId": "A0021"},  {"$set": {"contentsOrgName": "한전원자력원료(주)"}} )
        result = collection.update_many({"contentsOrgId": "A0022"},  {"$set": {"contentsOrgName": "한국에너지재단"}} )
        result = collection.update_many({"contentsOrgId": "A0023"},  {"$set": {"contentsOrgName": "한국에너지공단"}} )
        result = collection.update_many({"contentsOrgId": "A0024"},  {"$set": {"contentsOrgName": "NTIS"}} )
        result = collection.update_many({"contentsOrgId": "A0025"},  {"$set": {"contentsOrgName": "한국데이터산업진흥원"}} )
        result = collection.update_many({"contentsOrgId": "A0026"},  {"$set": {"contentsOrgName": "네이버 뉴스"}} )
        result = collection.update_many({"contentsOrgId": "A0027"},  {"$set": {"contentsOrgName": "한국산업지능화협회"}} )
        result = collection.update_many({"contentsOrgId": "A0028"},  {"$set": {"contentsOrgName": "전남정보문화산업진흥원"}} )
        result = collection.update_many({"contentsOrgId": "A0029"},  {"$set": {"contentsOrgName": "한국농수산식품유통공사"}} )

        result = collection.update_many({"categoryId": "B0001"},  {"$set": {"categoryName": "보도자료"}} )
        result = collection.update_many({"categoryId": "B0002"},  {"$set": {"categoryName": "사업공고"}} )
        result = collection.update_many({"categoryId": "B0003"},  {"$set": {"categoryName": "공지사항"}} )
        result = collection.update_many({"categoryId": "B0004"},  {"$set": {"categoryName": "보도자료"}} )
        result = collection.update_many({"categoryId": "B0005"},  {"$set": {"categoryName": "입찰공고"}} )
        result = collection.update_many({"categoryId": "B0006"},  {"$set": {"categoryName": "통합공고"}} )
        result = collection.update_many({"categoryId": "B0007"},  {"$set": {"categoryName": "네이버 포털"}} )
        result = collection.update_many({"categoryId": "B0008"},  {"$set": {"categoryName": "기타"}} )
        result = collection.update_many({"categoryId": "B0009"},  {"$set": {"categoryName": "사업공고"}} )
        result = collection.update_many({"categoryId": "B0010"},  {"$set": {"categoryName": "네이버 뉴스"}} )
        result = collection.update_many({"categoryId": "B0011"},  {"$set": {"categoryName": "고시"}} )
        result = collection.update_many({"categoryId": "B0012"},  {"$set": {"categoryName": "공고"}} )
        # 결과 출력
        print(f"Modified count: {result.modified_count} documents updated.")        
  
  
    def update_rawCollect(self, contentsVO:ContentsVO):
        # 금일 수집한 count 업데이트 --> 최미화 질문, UTC 타임으로 비교해야 하지 않나요? 
        collection = self.mongoManager.getCollection(self.collectionName)
        filter_query = {
            "_id": contentsVO._id
        }
        update_state = {
            "$set":
                {
                    "rawCollectSucYN" : contentsVO.rawCollectSucYN,
                    "contentsRaw" : contentsVO.contentsRaw.to_mongo(),
                    "rawCollectDt" : contentsVO.rawCollectDt,
                }
        }
  
        result = collection.update_one(
            filter_query,
            update_state,
        ) 
        return result
    

    def update_imageId(self, contentsVO:ContentsVO):
        # 금일 수집한 count 업데이트 --> 최미화 질문, UTC 타임으로 비교해야 하지 않나요? 
        collection = self.mongoManager.getCollection(self.collectionName)
        filter_query = {
            "_id": contentsVO._id
        }
        update_state = {
            "$set":
                {
                    "imageId" : contentsVO.imageId,
                }
        }
  
        result = collection.update_one(
            filter_query,
            update_state,
        ) 
        return result
        
    def update_metaAnalyze(self, contentsVO:ContentsVO):
        collection = self.mongoManager.getCollection(self.collectionName)
        filter_query = {
            "_id": contentsVO._id
        }
        update_state = {
            "$set":
                {
                    "metaSucYN" : contentsVO.metaSucYN,
                    "contentsMeta" : contentsVO.contentsMeta.to_mongo(),
                    "metaAnalyzeDt" : contentsVO.metaAnalyzeDt,
                }
        }
  
        result = collection.update_one(
            filter_query,
            update_state,
        ) 
        return result
    
    #--------------------------------------------------------------------------------------------------------------
    #delete 
    #--------------------------------------------------------------------------------------------------------------

    def removeDuplicateUrl(self,logger):
        collection = self.mongoManager.getCollection(ContentsVO.collectionName)
        pipeline = [
                {
                    "$group": {
                        "_id": "$url",  # 중복 확인할 필드
                        "count": {"$sum": 1},
                        "docs": {"$push": "$_id"}  # 중복된 문서들의 _id 목록
                    }
                },
                {
                    "$match": {
                        "count": {"$gt": 1}  # 중복된 항목만 필터링
                    }
                }
            ]

        duplicates = list(collection.aggregate(pipeline))
        for entry in duplicates:
            url = entry["_id"]  # 첫 번째 문서를 제외하고 삭제
            ids_to_delete = entry["docs"][:-1]  # 첫 번째 문서를 제외하고 삭제
            collection.delete_many({"_id": {"$in": ids_to_delete}})
            logger.info(f"중복된 contents url : {url} ({len(ids_to_delete)}개) 삭제") 
        pass     
    

    def remove_org_commcode(self, orgId:str) : 
        """
        설명 
        Args:
            OOO : 설명 
        Returns:
            OOO: 설명 
        """             
        
        try:

            collection = self.mongoManager.getCollection(self.collectionName)

            filter_query = {
                "contentsOrgId": orgId
            }
            count = collection.count_documents(filter_query)
                                    
            # 조건을 만족하는 첫 번째 문서 반환
            result = collection.delete_one(filter_query)

            # 결과 확인 및 출력
            if result.deleted_count > 0:
                print(f"기관 '{orgId}'의 콘텐츠 {result.deleted_count}개가 성공적으로 삭제되었습니다.")
            else:
                print(f"조건에 맞는 코드 '{orgId}'를 찾을 수 없습니다.")
        
        except Exception as e:
            print(f"An error occurred: {e}")
            return None                    
           
           
    def remove_contents_KST250229(self) : 
        """
        collectDt 값이 2025년 2월 29일(KST 기준) 이전인 모든 데이터를 삭제하는 함수

        Returns:
            int: 삭제된 문서 개수
        """    
        try:
            collection = self.mongoManager.getCollection(self.collectionName)

            # KST 기준 2025-02-29 00:00:00 생성
            kst = pytz.timezone("Asia/Seoul")
            cutoff_date = datetime(2025, 2, 29, 0, 0, 0, tzinfo=kst)            

            # MongoDB에서 UTC 기준으로 저장된 경우를 고려하여 UTC로 변환
            utc_cutoff_date = cutoff_date.astimezone(pytz.utc)

            # 삭제할 문서 필터 설정 (collectDt가 2025-02-29 이전인 데이터)
            filter_query = {
                "collectDt": {"$lt": utc_cutoff_date}
            }

            # 문서 개수 조회
            count = collection.count_documents(filter_query)
            print(f"2025-02-29 00:00:00 KST 이전의 문서 개수: {count} - 개를 삭제하겠습니다.")
            
            # 삭제 수행
            result = collection.delete_many(filter_query)

            # 결과 확인 및 출력
            if result.deleted_count > 0:
                print(f"'{result.deleted_count}'개의 2025-02-29 이전 데이터가 삭제되었습니다.")
            else:
                print("삭제할 데이터가 없습니다.")

            return result.deleted_count

        except Exception as e:
            print(f"An error occurred: {e}")
            return None
        
        
           

    

if __name__=='__main__':
    ContentsService().removeDuplicateUrl()
    
    