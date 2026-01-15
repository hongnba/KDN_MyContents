
from bson import ObjectId
import datetime
import traceback
from typing import List, Dict
import logging
import datetime
from urllib.parse import urlparse

from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO, ContentsOrgCategory
from ksubscribe_share.db.dbmodelV2.contentsCollectHistoryVO import ContentsCollectDetail, ContentsCollect, ContentsCollectHistoryVO
from ksubscribe_share.db.dbmodelV2.contentsCollectErrorVO import ContentsCollectErrorVO
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.service.contentsService import ContentsService
from ksubscribe_share.db.dbmodelV2.naverScrappingInfoVO import NaverScrappingInfoVO


#컨텐츠 수집 이력 
class NaverScrappingService():
    
    mongoManager = MongoManager()  # MongoManager 싱글톤 인스턴스를 사용
    collectionName = NaverScrappingInfoVO.collectionName
        
    _instance = None    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(NaverScrappingService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        pass 
    
    def getNaverScappingInfo(self, url:str) -> NaverScrappingInfoVO: 
        """
        네이버 뉴스 스크래핑 정보 읽기 
        Args:
            url : Content url 
        Returns:
            NaverScrappingInfoVO: url의 domain으로 스크래핑 정보를 검색하여 반환 
        """          
        parsed_url = urlparse(result["url"])
        domain = parsed_url.netloc  # 도메인 추출
        if domain:
            collection = self.mongoManager.getCollection(self.collectionName)
            result = collection.find_one({"domain": domain})
            return NaverScrappingInfoVO.from_mongo(result)
        else:
            return None 


    def upsert_naver_newsdomain(self, domain_list:List[str]):
        """ domain 정보 추가 
        Args:
            domain_list:List[str] : 도메일 목록 
        Returns:
            OOO: 설명 
        """             
        collection = self.mongoManager.getCollection(self.collectionName)


        for domain in domain_list:
            document = {
                "domain": domain,
                "collectMethod": "textInBody",
                "tagAttr": None,
                "tagAttrValue": None,
                "tagElement": None
            }

            # 도메인이 존재하면 업데이트, 없으면 삽입
            result = collection.update_one(
                {"domain": domain},  # 검색 조건
                {"$set": document},  # 업데이트할 데이터
                upsert=True  # 없으면 삽입
            )
            
            print(f"{domain} 도메인을 MongoDB에 저장 완료")


    def find_all_naver_newsdomain(self) -> List[NaverScrappingInfoVO]:
        """저장된 모든 도메인 데이터를 조회하는 함수
        
        Returns:
            List[NaverScrappingInfoVO]: 저장된 도메인 목록
        """
        collection = self.mongoManager.getCollection(self.collectionName)

        try:
            # 모든 도메인 데이터를 조회
            results = list(collection.find({}, {"_id": 0}))  # `_id` 필드 제외
            
            # MongoDB에서 가져온 dict를 NaverScrappingInfoVO 객체로 변환
            result_list = [NaverScrappingInfoVO.from_mongo(item) for item in results] 
            return result_list

        except Exception as e:
            print(f"An error occurred: {e}")
            return []

 
    