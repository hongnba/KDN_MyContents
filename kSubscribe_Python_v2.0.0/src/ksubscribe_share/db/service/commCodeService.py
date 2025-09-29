
from bson import ObjectId
import datetime
from typing import List

import datetime

from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO, ContentsOrgCategory
from ksubscribe_share.db.dbmodelV2.contentsCollectHistoryVO import ContentsCollectDetail, ContentsCollect, ContentsCollectHistoryVO
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.dbmodelV2.commCodeVO import CommCodeVO


#컨텐츠 수집 이력 
class CommCodeService():

    mongoManager = MongoManager()  # MongoManager 싱글톤 인스턴스를 사용
    collectionName = "common_code"
    
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(CommCodeService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        pass
    
    
    def get_org_code_list(self):#, orgId:str, cateId:str, collectionDetail:ContentsCollectDetail
        """설명 
        Args:
            OOO : 설명 
        Returns:
            OOO: 설명 
        """             

        try: 
            collection = self.mongoManager.getCollection(self.collectionName) 
            # MongoDB 업데이트 쿼리 구성
            filter_query = {
                "codeId": "COM00A",   
                "useYN": "Y"    # 최근 성공 날짜 기준으로 필터
            }
            # 반환할 필드 지정 
            projection = {
                "codeId": 1, 
                "code": 1,   
                "codeName": 1,   
            }
            
            # 조건을 만족하는 여러 문서 반환
            cursor = collection.find(filter_query, projection)
            result_list = [item for item in cursor] 
            
            return result_list
        
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
                 

    def get_org_name_list(self):#, orgId:str, cateId:str, collectionDetail:ContentsCollectDetail
        """설명 
        Args:
            OOO : 설명 
        Returns:
            OOO: 설명 
        """             

        try: 
            collection = self.mongoManager.getCollection(self.collectionName) 
            # MongoDB 업데이트 쿼리 구성
            filter_query = {
                "codeId": "COM00A",   
                "useYN": "Y"    # 최근 성공 날짜 기준으로 필터
            }
            # 반환할 필드 지정 
            projection = {
                "codeName": 1,   
            }
            
            # 조건을 만족하는 여러 문서 반환
            results = collection.find(filter_query, projection)

            return results 
        
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
                                  

    def get_cate_code_list(self):#, orgId:str, cateId:str, collectionDetail:ContentsCollectDetail
        """설명 
        Args:
            OOO : 설명 
        Returns:
            OOO: 설명 
        """             

        try:

            collection = self.mongoManager.getCollection(self.collectionName)

            # MongoDB 업데이트 쿼리 구성
            filter_query = {
                "codeId": "COM00B",   
                "useYN": "Y"    # 최근 성공 날짜 기준으로 필터
            }
            # 반환할 필드 지정
            projection = {
                "codeId": 1, 
                "code": 1,   
                "codeName": 1,   
            }
            
            # 조건을 만족하는 여러 문서 반환
            cursor = collection.find(filter_query, projection)
            result_list = [item for item in cursor] 
            return result_list 
        
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
        

    def get_orgId_byOrgName(self, orgName:str): 
        """설명 
        Args:
            OOO : 설명 
        Returns:
            OOO: 설명 
        """             
        
        try:

            collection = self.mongoManager.getCollection(self.collectionName)

            filter_query = {
                "codeId": "COM00A",   
                "codeName": orgName  
                
            }
            # 반환할 필드 지정
            projection = {
                "code": 1,   # code 필드만 반환
                "_id": 0         # MongoDB 기본 _id 필드 제외
            }
            
            # 조건을 만족하는 첫 번째 문서 반환
            result = collection.find_one(filter_query, projection)
            
            # code 반환 (결과가 없을 경우 None 반환)
            return str(result['code']) if result else None
        
        
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
        
    def get_cateName_by_cateId(self, cateId:str): 
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
                "codeId": "COM00B",   
                "code": cateId  
            }
            # 반환할 필드 지정
            projection = {
                "codeName": 1,   # code 필드만 반환
                "_id": 0         # MongoDB 기본 _id 필드 제외
            }
            
            # 조건을 만족하는 첫 번째 문서 반환
            result = collection.find_one(filter_query, projection)
            
            # code 반환 (결과가 없을 경우 None 반환)
            return str(result['codeName']) if result else None
        
        except Exception as e:
            print(f"An error occurred: {e}")
            return None        
        
    def get_orgName_by_orgId(self, orgId:str): 
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
                "codeId": "COM00A",   
                "code": orgId  
                
            }
            # 반환할 필드 지정
            projection = {
                "codeName": 1,   # code 필드만 반환
                "_id": 0         # MongoDB 기본 _id 필드 제외
            }
            
            # 조건을 만족하는 첫 번째 문서 반환
            result = collection.find_one(filter_query, projection)
            
            # code 반환 (결과가 없을 경우 None 반환)
            return str(result['codeName']) if result else None
        
        
        except Exception as e:
            print(f"An error occurred: {e}")
            return None        
        
    def get_commonCode_by_orgId(self, orgId:str): 
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
                "codeId": "COM00A",   
                "code": orgId  
            }
            
            # 조건을 만족하는 첫 번째 문서 반환
            result = collection.find_one(filter_query)
            
            return CommCodeVO.from_mongo(result)
        
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
    
    #remove ----------------------------------------------------------------------------------------------
    def remove_category_commcode(self, cateId:str) : 
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
                "codeId": "COM00B",   
                "code": cateId  
            }
            
            # 조건을 만족하는 첫 번째 문서 반환
            result = collection.delete_one(filter_query)

            # 결과 확인 및 출력
            if result.deleted_count > 0:
                print(f"카테고리 '{cateId}'가 성공적으로 삭제되었습니다.")
            else:
                print(f"조건에 맞는 카테고리 '{cateId}'를 찾을 수 없습니다.")

        
        except Exception as e:
            print(f"An error occurred: {e}")
            return None        
            
    def remove_category_main(self):
        """
        설명 
        Args:
            OOO : 설명 
        Returns:
            OOO: 설명 
        """             
        
        self.remove_category_in_allcollection("B0004", "B0001")  #보도자료 
        self.remove_category_in_allcollection("B0009", "B0002")  #사업공고 
        self.remove_category_commcode("B0004")
        self.remove_category_commcode("B0009")
        
    def remove_category_in_allcollection(self, cateId:str, to_cateId:str):
        """
        설명 
        Args:
            OOO : 설명 
        Returns:
            OOO: 설명 
        """             
        
        try:
            #contents 수정 
            contents_collection = self.mongoManager.getCollection("contents")

            filter_query = {"categoryId": cateId}
            # 업데이트 동작: categoryId를 to_cateId로 변경
            update_action = {"$set": {"categoryId": to_cateId}}
            # 업데이트 실행
            result = contents_collection.update_many(filter_query, update_action)
            # 결과 출력
            if result.modified_count > 0:
                print(f"contents {result.modified_count}개의 문서가 업데이트되었습니다.")
            else:
                print("contents 조건에 맞는 문서를 찾을 수 없습니다.")

            #contents_collect_error 수정 
            contents_collect_error_collection = self.mongoManager.getCollection("contents_collect_error")

            filter_query = {"cateId": cateId}
            # 업데이트 동작: categoryId를 to_cateId로 변경
            update_action = {"$set": {"cateId": to_cateId}}
            # 업데이트 실행
            result = contents_collect_error_collection.update_many(filter_query, update_action)
            # 결과 출력
            if result.modified_count > 0:
                print(f"contents_collect_error {result.modified_count}개의 문서가 업데이트되었습니다.")
            else:
                print("contents_collect_error 조건에 맞는 문서를 찾을 수 없습니다.")


            # contents_collect_history 컬렉션 수정
            contents_collect_history_collection = self.mongoManager.getCollection("contents_collect_history")

            filter_query = {"contentCollectList.categoryId": cateId}
            update_action = {"$set": {"contentCollectList.$[item].categoryId": to_cateId}}
            array_filters = [{"item.categoryId": cateId}]
            result = contents_collect_history_collection.update_many(filter_query, update_action, array_filters=array_filters)

            if result.modified_count > 0:
                print(f"contents_collect_history {result.modified_count}개의 문서가 업데이트되었습니다.")
            else:
                print("contents_collect_history 조건에 맞는 문서를 찾을 수 없습니다.")
            

            # contents_org 컬렉션 수정
            contents_org_collection = self.mongoManager.getCollection("contents_org")

            filter_query = {"categoryList.cateId": cateId}
            update_action = {"$set": {"categoryList.$[item].cateId": to_cateId}}
            array_filters = [{"item.cateId": cateId}]
            result = contents_org_collection.update_many(filter_query, update_action, array_filters=array_filters)

            if result.modified_count > 0:
                print(f"contents_org {result.modified_count}개의 문서가 업데이트되었습니다.")
            else:
                print("contents_org 조건에 맞는 문서를 찾을 수 없습니다.")
                
            
            # favorite_subscribe_list 컬렉션 수정
            favorite_subscribe_list_collection = self.mongoManager.getCollection("favorite_subscribe_list")

            filter_query = {"orgIdAndCateIds.cateId": cateId}
            update_action = {"$set": {"orgIdAndCateIds.$[item].cateId": to_cateId}}
            array_filters = [{"item.cateId": cateId}]
            result = favorite_subscribe_list_collection.update_many(filter_query, update_action, array_filters=array_filters)

            if result.modified_count > 0:
                print(f"favorite_subscribe_list {result.modified_count}개의 문서가 업데이트되었습니다.")
            else:
                print("favorite_subscribe_list 조건에 맞는 문서를 찾을 수 없습니다.")
        
            
            #contents_collect_error 수정 
            member_account_collection = self.mongoManager.getCollection("member_account")
        
            # 필터 조건: categoryList에 cateId가 있는 문서 검색
            filter_query = {"contentsOrgSubscribe.categoryList.cateId": cateId}

            # 업데이트 동작: categoryList 배열 내의 cateId를 to_cateId로 변경
            update_action = {
                "$set": {"contentsOrgSubscribe.$[org].categoryList.$[cate].cateId": to_cateId}
            }

            # 배열 필터 정의
            array_filters = [
                {"org.categoryList": {"$exists": True}},  # categoryList가 있는 경우
                {"cate.cateId": cateId}  # cateId가 일치하는 경우
            ]

            # 업데이트 실행
            result = member_account_collection.update_many(filter_query, update_action, array_filters=array_filters)

            # 결과 출력
            if result.modified_count > 0:
                print(f"member_account {result.modified_count}개의 문서가 업데이트되었습니다.")
            else:
                print("member_account 조건에 맞는 문서를 찾을 수 없습니다.")        
                
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
    
    def remove_code_commcode(self, code:str) : 
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
                "code": code
            }
            
            count = collection.count_documents(filter_query)

            if count > 1 : 
                return
                                    
            # 조건을 만족하는 첫 번째 문서 반환
            result = collection.delete_one(filter_query)

            # 결과 확인 및 출력
            if result.deleted_count > 0:
                print(f"코드 '{code}'가 성공적으로 삭제되었습니다.")
            else:
                print(f"조건에 맞는 코드 '{code}'를 찾을 수 없습니다.")

        
        except Exception as e:
            print(f"An error occurred: {e}")
            return None        
                
    
    