
from bson import ObjectId
#import datetime
import traceback
from typing import List
import pytz
import logging
from datetime import datetime, timezone

from ksubscribe_share.db.service.contentsCollectDailyHistoryService import ContentsCollectDailyHistoryService
from ksubscribe_share.logger import Logger
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO, ContentsOrgCategory
from ksubscribe_share.db.dbmodelV2.contentsCollectHistoryVO import ContentsCollectDetail, ContentsCollect, ContentsCollectHistoryVO
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO
from ksubscribe_share.db.service.contentsService import ContentsService
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService
import ksubscribe_share.config as Conf


#컨텐츠 수집 이력 
class ContentsCollectHistoryService():
    
    mongoManager = MongoManager()  # MongoManager 싱글톤 인스턴스를 사용
    collectionName = "contents_collect_history" 

    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ContentsCollectHistoryService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        pass

    def find_by_date(self,collectDt):
        collection = self.mongoManager.getCollection(ContentsCollectHistoryVO.collectionName)
        filter_query1 = {
                "collectDt": collectDt
            }

        cursor = collection.find(filter_query1)
        result = [ContentsCollectHistoryVO.doc for doc in cursor]
        return result

    def insertCollectHistory(self, 
                                     sucYN : str, 
                                     collectDt : str,  
                                     orgId : str, 
                                     cateId : str, 
                                     title : str,
                                     url : str, 
                                     shortUrl:str,
                                     pubDt : datetime):
        
        #수집 이력도 넣고, 컨텐츠 큐에도 넣고, 두개 데이터의 key: url임     
            
        #STEP 1 ) ContentsCollectHistoryVO에 값을 넣는다.         
        try:
            collection = self.mongoManager.getCollection(ContentsCollectHistoryVO.collectionName)

            # collectDt
            # 필터 조건
            filter_query1 = {
                "contentOrgId": orgId,
                "collectDt": collectDt
            }
            
            document = collection.find_one(filter_query1)
            if document:
                # contentCollectList 배열 확인
                content_collect_list = document.get("contentCollectList", [])
                
                # contentCollectList에서 조건에 맞는 항목 찾기
                matching_item = next(
                    (item for item in content_collect_list
                    if item["contentOrgId"] == orgId and item["categoryId"] == cateId),
                    None
                )

                if matching_item:
                    # contentCollectList 있음: collectionDetailList에 항목 추가
                    collection.update_one(
                        {"_id": document["_id"], "contentCollectList.contentOrgId": orgId},
                        {
                            "$push": {
                                "contentCollectList.$.collectionDetailList": {
                                    "title": title,
                                    "url": url,
                                    "shortUrl": shortUrl,
                                    "pubDt": pubDt,
                                    "sucYN": sucYN
                                }
                            }
                        }
                    )
                    #print("collectionDetailList에 새 항목을 추가했습니다.")
                else:
                    # contentCollectList 없음: 새 contentCollectList 추가
                    collection.update_one(
                        filter_query1,
                        {
                            "$push": {
                                "contentCollectList": {
                                    "contentOrgId": orgId,
                                    "categoryId": cateId,
                                    "collectionDetailList": [
                                        {
                                            "title": title,
                                            "url": url,
                                            "shortUrl": shortUrl,
                                            "pubDt": pubDt,
                                            "sucYN": sucYN
                                        }
                                    ]
                                }
                            }
                        } 
                    )
                    #print("새 contentCollectList를 추가했습니다.")
                
            else:
                # 새 문서 삽입
                insert_data = {
                    "contentOrgId": orgId,
                    "collectDt": collectDt,
                    "contentCollectList": [
                        {
                            "contentOrgId": orgId,
                            "categoryId": cateId,
                            "collectionDetailList": [
                                {
                                    "title": title,
                                    "url": url,
                                    "shortUrl": shortUrl,
                                    "pubDt": pubDt,
                                    "sucYN": sucYN
                                }
                            ]
                        }
                    ]
                }
                collection.insert_one(insert_data)
                #print("새 document를 추가했습니다.")

        except Exception as e:
            #print(f"An error occurred: {e}")
            raise e

    def insertCategoryCollectHistory(self,  
                                     collectDt : datetime,  
                                     contentsOrg : ContentsOrgVO, 
                                     category : ContentsOrgCategory, 
                                     collectDetail : ContentsCollectDetail, 
                                     session = None,
                                     keyword = None, 
                                     logger:logging.Logger=None):
        
        if ContentsQueueService().isExistQueue(collectDetail.url):
            logger and logger.info(f"이미 Queue에 존재하는 contents입니다. {collectDetail.url}")
            return  None
        if ContentsService().isExistContents(collectDetail.url):
            logger and logger.info(f"이미 ContentsDB에 존재하는 contents입니다. {collectDetail.url}")
            return None
        
        ##### 250520 #####
        if isinstance(collectDt, str):
            try:
                collectDt = datetime.strptime(collectDt, "%Y%m%d")
            except ValueError:
                collectDt = datetime.strptime(collectDt, "%Y-%m-%d")
        ##################
        
        # 큰 if-else 블록으로 분리
        if Conf.MONGO_USE_TRANSACTION:
            # ============================================
            # 개발서버 (KDN) - Replica Set, 트랜잭션 사용
            # ============================================
        
            mongoManager = MongoManager()
            session = mongoManager.client.start_session()
            session.start_transaction() 
            
            try:  
                #collectDt = datetime.now(timezone.utc)
                
                if isinstance(collectDetail.pubDt, datetime): 
                    collectDetail.pubDt.replace(hour=9, minute=0, second=0, microsecond=0)
                    pass  
                else:
                    collectDetail.pubDt = datetime.strptime(collectDetail.pubDt,"%Y%m%d")
                    collectDetail.pubDt.replace(hour=9, minute=0, second=0, microsecond=0)

                collection = self.mongoManager.getCollection(ContentsCollectHistoryVO.collectionName)
                collectYMD = collectDt.strftime("%Y%m%d")
                # 필터 조건
                filter_query1 = {
                    "contentOrgId": contentsOrg.orgId,
                    "collectDt":collectYMD,
                }
                
                document = collection.find_one(filter_query1, session=session)
                if document:
                    content_collect_list = document.get("contentCollectList", [])
                    
                    # contentCollectList에서 조건에 맞는 항목 찾기
                    matching_item = next(
                        (item for item in content_collect_list
                        if item["contentOrgId"] == contentsOrg.orgId and item["categoryId"] == category.cateId),
                        None
                    )

                    if matching_item:
                        # contentCollectList 있음: collectionDetailList에 항목 추가
                        collection.update_one(
                            {"_id": document["_id"], "contentCollectList.contentOrgId": contentsOrg.orgId,
                            "contentCollectList.categoryId": category.cateId},
                            {
                                "$push": {
                                    "contentCollectList.$[elem].collectionDetailList": {
                                        "title": collectDetail.title,
                                        "url": collectDetail.url,
                                        "naverUrl": collectDetail.naverUrl,
                                        "shortUrl": collectDetail.shortUrl,
                                        "pubDt": collectDetail.pubDt,
                                        "sucYN": "Y" if collectDetail.sucYN else "N"
                                    }
                                }
                            },
                            array_filters=[
                                {
                                    "elem.contentOrgId": contentsOrg.orgId,
                                    "elem.categoryId": category.cateId
                                }
                            ],
                            session=session  # 세션 포함 (선택 사항)
                        )
                        #print("collectionDetailList에 새 항목을 추가했습니다.")
                    else:
                        # contentCollectList 없음: 새 contentCollectList 추가
                        collection.update_one(
                            filter_query1,
                            {
                                "$push": {
                                    "contentCollectList": {
                                        "contentOrgId": contentsOrg.orgId,
                                        "categoryId": category.cateId,
                                        "collectionDetailList": [
                                            {
                                                "title": collectDetail.title,
                                                "url": collectDetail.url,
                                                "naverUrl": collectDetail.naverUrl,
                                                "shortUrl": collectDetail.shortUrl,
                                                "pubDt": collectDetail.pubDt,
                                                "sucYN": "Y" if collectDetail.sucYN else "N"
                                            }
                                        ]
                                    }
                                }
                            }, session=session
                        )
                        #print("새 contentCollectList를 추가했습니다.")
                    
                else:
                    # 새 문서 삽입(o)
                    insert_data = {
                        "contentOrgId": contentsOrg.orgId,
                        "collectDt": collectYMD,
                        "contentCollectList": [
                            {
                                "contentOrgId": contentsOrg.orgId,
                                "categoryId": category.cateId,
                                "collectionDetailList": [
                                    {
                                        "title": collectDetail.title,
                                        "url": collectDetail.url,
                                        "naverUrl": collectDetail.naverUrl,
                                        "shortUrl": collectDetail.shortUrl,
                                        "pubDt": collectDetail.pubDt,
                                        "sucYN": "Y" if collectDetail.sucYN else "N"
                                    }
                                ]
                            }
                        ]
                    }
                    collection.insert_one(insert_data, session=session ) 
                    
                logger and logger.info(f"( {collectDetail.url} ) : ContentsCollectDailyHistory 반영완료 ")
                    
                #STEP 2 ) ContentsQueueVO에 값을 넣는다.         
                if collectDetail.sucYN:
                    ContentsCollectDailyHistoryService().inc_daily_collect_cnt(session)
                    contentsQueueService = ContentsQueueService()
                    result = contentsQueueService.insertQueue(contentsOrg.orgId, category.cateId, collectDetail, collectDt, keyword=keyword,session=session)
                else:
                    ContentsCollectDailyHistoryService().inc_daily_fail_cnt(session)
                    
                
                session.commit_transaction()
                
            except Exception as e:
                session.abort_transaction()
                traceback.print_exc()
                session.end_session()
                print(f"An error occurred: {e}")
                raise e

            session.end_session()
            
        else:
            # ============================================
            # 로컬서버 (더미라클소프트) - 단일 인스턴스, 트랜잭션 미사용
            # ============================================
            mongoManager = MongoManager()
            session = None
            
            try:  
                if isinstance(collectDetail.pubDt, datetime): 
                    collectDetail.pubDt.replace(hour=9, minute=0, second=0, microsecond=0)
                    pass  
                else:
                    collectDetail.pubDt = datetime.strptime(collectDetail.pubDt,"%Y%m%d")
                    collectDetail.pubDt.replace(hour=9, minute=0, second=0, microsecond=0)

                collection = self.mongoManager.getCollection(ContentsCollectHistoryVO.collectionName)
                collectYMD = collectDt.strftime("%Y%m%d")
                filter_query1 = {
                    "contentOrgId": contentsOrg.orgId,
                    "collectDt":collectYMD,
                }
                
                document = collection.find_one(filter_query1)
                if document:
                    content_collect_list = document.get("contentCollectList", [])
                    
                    matching_item = next(
                        (item for item in content_collect_list
                        if item["contentOrgId"] == contentsOrg.orgId and item["categoryId"] == category.cateId),
                        None
                    )

                    if matching_item:
                        collection.update_one(
                            {"_id": document["_id"], "contentCollectList.contentOrgId": contentsOrg.orgId,
                            "contentCollectList.categoryId": category.cateId},
                            {
                                "$push": {
                                    "contentCollectList.$[elem].collectionDetailList": {
                                        "title": collectDetail.title,
                                        "url": collectDetail.url,
                                        "naverUrl": collectDetail.naverUrl,
                                        "shortUrl": collectDetail.shortUrl,
                                        "pubDt": collectDetail.pubDt,
                                        "sucYN": "Y" if collectDetail.sucYN else "N"
                                    }
                                }
                            },
                            array_filters=[
                                {
                                    "elem.contentOrgId": contentsOrg.orgId,
                                    "elem.categoryId": category.cateId
                                }
                            ]
                        )
                    else:
                        collection.update_one(
                            filter_query1,
                            {
                                "$push": {
                                    "contentCollectList": {
                                        "contentOrgId": contentsOrg.orgId,
                                        "categoryId": category.cateId,
                                        "collectionDetailList": [
                                            {
                                                "title": collectDetail.title,
                                                "url": collectDetail.url,
                                                "naverUrl": collectDetail.naverUrl,
                                                "shortUrl": collectDetail.shortUrl,
                                                "pubDt": collectDetail.pubDt,
                                                "sucYN": "Y" if collectDetail.sucYN else "N"
                                            }
                                        ]
                                    }
                                }
                            }
                        )
                else:
                    insert_data = {
                        "contentOrgId": contentsOrg.orgId,
                        "collectDt": collectYMD,
                        "contentCollectList": [
                            {
                                "contentOrgId": contentsOrg.orgId,
                                "categoryId": category.cateId,
                                "collectionDetailList": [
                                    {
                                        "title": collectDetail.title,
                                        "url": collectDetail.url,
                                        "naverUrl": collectDetail.naverUrl,
                                        "shortUrl": collectDetail.shortUrl,
                                        "pubDt": collectDetail.pubDt,
                                        "sucYN": "Y" if collectDetail.sucYN else "N"
                                    }
                                ]
                            }
                        ]
                    }
                    collection.insert_one(insert_data)
                
                logger and logger.info(f"( {collectDetail.url} ) : ContentsCollectDailyHistory 반영완료 ")
                
                if collectDetail.sucYN:
                    ContentsCollectDailyHistoryService().inc_daily_collect_cnt(session)
                    contentsQueueService = ContentsQueueService()
                    result = contentsQueueService.insertQueue(contentsOrg.orgId, category.cateId, collectDetail, collectDt, keyword=keyword, session=session)
                else:
                    ContentsCollectDailyHistoryService().inc_daily_fail_cnt(session)
                
            except Exception as e:
                traceback.print_exc()
                print(f"An error occurred: {e}")
                raise e
        
        return True


    def test_queryy(self):
        collection = self.mongoManager.getCollection(ContentsQueueService.collectionName) 
        test_YMD =datetime.strptime("20250121", "%Y%m%d")
        
        filter_query1 = {
            "collectDt":{"$gte":test_YMD}, 
        }
        document = collection.find_one(filter_query1)
        pass  


#ContentsCollectHistoryService().test_queryy()