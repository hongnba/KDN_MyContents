 
from bson import ObjectId
import datetime
from typing import List

import datetime

from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel 
from ksubscribe_share.db.dbmodelV2.predefineKeywordVO import PredefineKeywordVO
from ksubscribe_share.db.mongoManager import MongoManager
#컨텐츠 수집 이력 
class PredefineKeywordService():
    
    mongoManager = MongoManager()           # MongoManager 싱글톤 인스턴스를 사용
    collectionName = "predefine_keyword"
        
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(PredefineKeywordService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        pass 

   
    # def getKeywordList(self): include_deleted 삭제데이터 포함여부 추가 20250527 mcst
    def getKeywordList(self, include_deleted=False):    
        """
        predefine_keyword 컬렉션에서 keyword 필드만 조회 
        Args:
            include_deleted (bool): False이면 deleteYN='N'인 데이터만, True이면 모든 데이터 조회 (기본값: False)
        Returns:
            list: keyword 값들의 리스트, 오류 발생 시 None 
        """             
        
        try: 
            collection = self.mongoManager.getCollection(self.collectionName)
   
            # 반환할 필드 지정 
            projection = {
                "keyword": 1,   
            }
            # 쿼리 실행
            # 삭제데이터 포함여부에 따라 조회 조건 추가 20250527 mcst
            # cursor = collection.find({},projection)
            cursor = collection.find({} if include_deleted else {"deleteYN": "N"},projection)
            result = [doc['keyword'] for doc in cursor if 'keyword' in doc]
             
            return result

        except Exception as e:
            print(f"An error occurred: {e}")                
            return None    
      
    def addSubscribe(self, mberId:str, keyword:str): 
        """
        설명 
        Args:
            OOO : 설명 
        Returns:
            OOO: 설명 
        """        
        try:

            collection = self.mongoManager.getCollection(self.collectionName)
        
            # 업데이트 조건과 업데이트 동작 정의
            filter_condition = {"keyword": keyword}  # id가 "aaa"인 문서 찾기
            update_action = {
                "$addToSet": {
                    "subscriberIds": mberId     # wordList의 모든 요소 추가
                }
            }
            # MongoDB 업데이트 실행
            result = collection.update_one(filter_condition, update_action)

            # 결과 출력
            if result.modified_count > 0:
                print(f"문서가 성공적으로 업데이트되었습니다.")
            elif result.matched_count > 0:
                print(f"문서는 이미 업데이트되어 있습니다.")
            else:
                print(f"조건에 맞는 문서를 찾을 수 없습니다.")

        except Exception as e:
            print(f"An error occurred: {e}")
    
    
    #--------------------------------------------------------------------------------------------
    # remove 
    #--------------------------------------------------------------------------------------------
    def remove_keyword(self, keyword:str) : 
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
                "keyword": keyword
            }
            
            count = collection.count_documents(filter_query)

            if count > 1 : 
                print(f"1개 이상의 '{keyword}' 키워드가 검색되었습니다.")
                return
                                    
            # 조건을 만족하는 첫 번째 문서 반환
            result = collection.delete_one(filter_query)

            # 결과 확인 및 출력
            if result.deleted_count > 0:
                print(f"키워드 '{keyword}'가 {result.deleted_count}개가 성공적으로 삭제되었습니다.")
            else:
                print(f"조건에 맞는 키워드 '{keyword}'를 찾을 수 없습니다.")

        
        except Exception as e:
            print(f"An error occurred: {e}")
            return None                    
           
    