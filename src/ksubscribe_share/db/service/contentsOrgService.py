
from bson import ObjectId
import datetime
from typing import List
import pytz
from datetime import datetime
import logging

from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO, ContentsOrgCategory
from ksubscribe_share.db.dbmodelV2.contentsCollectHistoryVO import ContentsCollectDetail, ContentsCollect, ContentsCollectHistoryVO
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.logger import Logger

#컨텐츠 수집 이력 
class ContentsOrgService():

    mongoManager = MongoManager()  # MongoManager 싱글톤 인스턴스를 사용
    collectionName = "contents_org"
    
    
    
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ContentsOrgService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        pass

    #--------------------------------------------------------------------------------------------------------------
    #return True/False 함수 

    #--------------------------------------------------------------------------------------------------------------
    #find/select/search/get 함수


    def get_orgId_by_synonym(self, orgName:str):
        
        if orgName is None:
            return None
        
        try: 
            collection = self.mongoManager.getCollection(self.collectionName) 
            # MongoDB 업데이트 쿼리 구성
            filter_query = {
                "$or": [
                    {"orgName": orgName},  # orgName이 특정 값인 경우
                    {"orgNameSynonymList": orgName}  # orgNameSynonymList 배열에 orgName이 포함된 경우
                ]
            }
            # 반환할 필드 지정 
            projection = {
                "_id": 1,
                "orgId" : 1
            }
            
            # 조건을 만족하는 여러 문서 반환
            document = collection.find_one(filter_query, projection)

            # code 반환 (결과가 없을 경우 None 반환)
            orgId:str = str(document["orgId"]) if document else None
            return orgId
        
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def find_all(self):
        try: 
            collection = self.mongoManager.getCollection(self.collectionName)
            cursor = collection.find()
            result_list = [ContentsOrgVO.from_mongo(item) for item in cursor] 
            #utc to kst 
            for contentsOrg in result_list:
                for category in contentsOrg.categoryList:
                    if isinstance(category.lastSucYMD, datetime): 
                        # to kst 
                        local_tz = pytz.timezone('Asia/Seoul') 
                        category.lastSucYMD = category.lastSucYMD.astimezone(local_tz)
                        #category.lastSucYMD.strftime
                        pass  
                    else:
                        category.lastSucYMD = datetime.strptime(category.lastSucYMD,"%Y%m%d")
                        local_tz = pytz.timezone('Asia/Seoul') 
                        category.lastSucYMD = category.lastSucYMD.astimezone(local_tz)
                        category.lastSucYMD  = category.lastSucYMD.replace(hour=0, minute=0, second=0, microsecond=0)
                        
            return result_list
        except Exception as e :
            print(e)
            pass 
 
    def findOrgKeywords(self, orgId:str):
        
        orgKeyworkList=[]
        
        try:

            collection = self.mongoManager.getCollection(self.collectionName)
            query = {
                "orgId": orgId,
            }

            # 쿼리 실행
            result = collection.find_one(query)
            
            if not result:
                return orgKeyworkList
             
            # orgKeywordList 추출
            if "orgKeywordList" in result:
                orgKeyworkList.extend(result["orgKeywordList"])  # orgKeywordList 항목 추가

            if "categoryList" in result:
                for category in result["categoryList"]:
                    if "keywords" in category:  # keywords가 존재하는 경우
                        orgKeyworkList.extend(category["keywords"])  # keywords 추가
            
        except Exception as e:
            print(f"An error occurred: {e}")        
        
        return orgKeyworkList    
  
    def findNaraOrg(self):
        
        try:

            collection = self.mongoManager.getCollection(self.collectionName)
            query = {
                "orgId": "A0004",
            }

            # 쿼리 실행
            result = collection.find_one(query)
            
            return ContentsOrgVO.from_mongo(result)

        except Exception as e:
            print(f"An error occurred: {e}")        
        
        return None    
  
    def findOrgAndCategory(self, orgId:str, cateId:str):
        
        try:

            collection = self.mongoManager.getCollection(self.collectionName)
            query = {
                "orgId": orgId,
            }

            # 쿼리 실행
            result = collection.find_one(query)
            contentsOrgVO = ContentsOrgVO.from_mongo(result) 
            
            if contentsOrgVO.categoryList: 
                for category in contentsOrgVO.categoryList:
                    if category.cateId == cateId:  # keywords가 존재하는 경우
                        return contentsOrgVO, category
                
            return contentsOrgVO, None 

        except Exception as e:
            print(f"An error occurred: {e}")                
            return None, None    
        
    def findOrgbyName(self,name : str): 
        try:

            collection = self.mongoManager.getCollection(self.collectionName)
            query = {
                "orgName": name,
            }
            # 쿼리 실행
            result = collection.find_one(query)
            return ContentsOrgVO.from_mongo(result)

        except Exception as e:
            print(f"An error occurred: {e}")        
        
        return None    
  
    def findOrg(self, orgId:str):
        
        try:

            collection = self.mongoManager.getCollection(self.collectionName)
            query = {
                "orgId": orgId,
            }

            # 쿼리 실행
            result = collection.find_one(query)
            contentsOrgVO = ContentsOrgVO.from_mongo(result) 
            
            return contentsOrgVO 

        except Exception as e:
            print(f"An error occurred: {e}")                
            return None, None    
    
    
    # 20251013 liza 기능 추가 (기능: 기관 이름과 키워드 조회)
    def getOrgNameAndKeywords(self, orgId: str):
        """
        Get organization name and combined keywords/synonyms by orgId.
        
        Args:
            orgId (str): Organization ID to search for
            
        Returns:
            tuple: (orgName: str, combined_keywords: list) or (None, None) if not found
        """
        try:
            collection = self.mongoManager.getCollection(self.collectionName)
            query = {
                "orgId": orgId,
            }

            # 쿼리 실행
            result = collection.find_one(query)
            
            if not result:
                return None, None
                
            # Extract orgName
            orgName = result.get("orgName")
            
            # Combine orgNameSynonymList and orgKeywordList
            combined_keywords = []
            
            # Add orgNameSynonymList if present
            orgNameSynonymList = result.get("orgNameSynonymList", [])
            if orgNameSynonymList:
                combined_keywords.extend(orgNameSynonymList)
            
            # Add orgKeywordList if present
            orgKeywordList = result.get("orgKeywordList", [])
            if orgKeywordList:
                combined_keywords.extend(orgKeywordList)
            
            # Remove duplicates and return as set converted to list
            combined_keywords = list(set(combined_keywords))
            
            return orgName, combined_keywords

        except Exception as e:
            print(f"An error occurred: {e}")
            return None, None 
          
  
    #--------------------------------------------------------------------------------------------------------------
    #insert함수
          
          
    def add_subscriber_to_org(self, orgId:str, mberId:str):
        
        try:
            contentsOrgVO =  self.findOrg(orgId)
            
            if contentsOrgVO.subscriberIds is None:
                contentsOrgVO.subscriberIds = []  # 리스트 초기화
                
            if mberId not in contentsOrgVO.subscriberIds:
                contentsOrgVO.subscriberIds.append(mberId)
            
            self.updateSubscribers(contentsOrgVO)
            
        except Exception as e:
            print(f"An error occurred: {e}")
            return None          
        

    def add_subscriber_to_orgcate(self, orgId:str, cateId:str, mberId:str):
        
        try:
            contentsOrgVO =  self.findOrg(orgId)
            
            if contentsOrgVO.subscriberIds is None:
                contentsOrgVO.subscriberIds = []  # 리스트 초기화
            
            for category in contentsOrgVO.categoryList:
                if category.cateId == cateId: 
                    if mberId not in category.subscriberIds:
                        category.subscriberIds.append(mberId)                    
            
            self.updateSubscribers(contentsOrgVO)
            
        except Exception as e:
            print(f"An error occurred: {e}")
            return None          
                            
           
    #--------------------------------------------------------------------------------------------------------------
    #update함수
          
        
    def updateCategorySucYMD(self, org_id:str, category_id:str, sucYN:bool, lastSucYMD : datetime, session = None,logger:logging.Logger= None):
        
        """
        카테고리 ID의 SUC_YN과 LAST_SUC_YMD 값을 업데이트하는 함수.
        :param category_id: 업데이트할 카테고리의 ID
        :param success_flag: 업데이트할 성공 여부 (True/False)
        """
        # lastSucYMD = datetime.utcnow().replace(tzinfo=pytz.utc)
        try:
            collection = self.mongoManager.getCollection(self.collectionName)
            update_fields = {
                "categoryList.$.sucYN": "Y" if sucYN else "N"
            }
            
            if sucYN:
                update_fields["categoryList.$.lastSucYMD"] = lastSucYMD
                
            result = collection.update_one(
                {"orgId": org_id, "categoryList.cateId": category_id},  # 조건: orgId와 cateId 매칭
                {"$set": update_fields},
                session=session
            )

            # 결과 확인
            if result.matched_count > 0:
                logger and logger.debug(f"Successfully updated category '{category_id}' in org '{org_id}'.")
            else:
                logger and logger.debug(f"No matching category found for org '{org_id}' and category '{category_id}'.")
        except Exception as e:
            logger and logger.error(f"An error occurred: {e}")

        
    def updateSubscribers(self, contentsOrgVO:ContentsOrgVO):
        try:

            collection = self.mongoManager.getCollection(self.collectionName)
            # MongoDB 업데이트 쿼리
            result = collection.update_one(
                {"_id": contentsOrgVO._id},  # 조건: orgId와 cateId 매칭
                {
                    "$set": {
                        "subscriberIds": contentsOrgVO.subscriberIds
                    }
                }
            )

            # 결과 확인
            if result.matched_count > 0:
                print(f"Successfully updated  in org '{contentsOrgVO._id}'.")
            else:
                print(f"No matching  for org '{contentsOrgVO._id}' .")
        except Exception as e:
            print(f"An error occurred: {e}")
         
         
    def updateCollectInfo(self, org_id:str, category_id:str, collectMethod:str, tagElement:str, tagAttr:str, tagAttrValue:str ):
        
        try:

            collection = self.mongoManager.getCollection(self.collectionName)
            # MongoDB 업데이트 쿼리
            result = collection.update_one(
                {"orgId": org_id, "categoryList.cateId": category_id},  # 조건: orgId와 cateId 매칭
                {
                    "$set": {
                        "categoryList.$.collectMethod": collectMethod,  
                        "categoryList.$.tagElement": tagElement,  
                        "categoryList.$.tagAttr": tagAttr,  
                        "categoryList.$.tagAttrValue": tagAttrValue,  
                    }
                }
            )

            # 결과 확인
            if result.matched_count > 0:
                print(f"Successfully updated category '{category_id}' in org '{org_id}'.")
            else:
                print(f"No matching category found for org '{org_id}' and category '{category_id}'.")
            
        except Exception as e:
            print(f"An error occurred: {e}")
           
            
    def updateOrgNameSynonym(self, org_id:str, synonyms:List[str]):
        
        try:

            collection = self.mongoManager.getCollection(self.collectionName)
            # MongoDB 업데이트 쿼리
            result = collection.update_one(
                {"orgId": org_id},  # 조건: orgId와 cateId 매칭
                {
                    "$set": {
                        "orgNameSynonymList": synonyms,  
                    }
                }
            )

            # 결과 확인
            if result.matched_count > 0:
                print(f"Successfully updated  in org '{org_id}'.")
            else:
                print(f"No matching category found for org '{org_id}' .")
            
        except Exception as e:
            print(f"An error occurred: {e}")            
          
    def updateImageInfo(self, org_id:str, orgCIWidth:str, orgCIHeight:str):
        
        try:

            collection = self.mongoManager.getCollection(self.collectionName)
            # MongoDB 업데이트 쿼리
            result = collection.update_one(
                {"orgId": org_id},  # 조건: orgId와 cateId 매칭
                {
                    "$set": {
                        "orgCIWidth": orgCIWidth,  
                        "orgCIHeight": orgCIHeight
                    }
                }
            )
            # 결과 확인
            if result.matched_count > 0:
                print(f"Successfully updated  in org '{org_id}'.")
            else:
                print(f"No matching category found for org '{org_id}' .")
                        
            return True
        except Exception as e:
            print(f"An error occurred: {e}")
            return False
                    
                   
    #--------------------------------------------------------------------------------------------------------------
    #delete, remove함수    
            
    def remove_duplicate_subscriberId(self) :

        collection = self.mongoManager.getCollection(self.collectionName)
        try:
            # 200번 서버에서 데이터 읽기
            cursor = collection.find({}, {"orgId": 1, "subscriberIds": 1})
            
            for doc in cursor:
                # 읽어온 데이터
                orgId = doc["orgId"]
                subscriber_ids = doc.get("subscriberIds", [])
                
                # 중복 제거
                unique_subscriber_ids = list(set(subscriber_ids))
                
                # 41번 서버에 업데이트
                result = collection.update_one(
                    {"orgId": orgId},
                    {"$set": {"subscriberIds": unique_subscriber_ids}},
                    upsert=True  # 문서가 없으면 새로 생성
                )
                
                # 결과 로그
                if result.matched_count > 0:
                    print(f"Updated subscriberIds for orgId: {orgId}")
                elif result.upserted_id:
                    print(f"Inserted new document with orgId: {orgId}")
                else:
                    print(f"No changes for orgId: {orgId}")

        except Exception as e:
            print(f"An error occurred: {e}")        
            

          
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
                "orgId": orgId
            }
            
            count = collection.count_documents(filter_query)

            if count > 1 : 
                print(f"1개 이상의 '{orgId}' 기관이 검색되었습니다.")
                return
                                    
            # 조건을 만족하는 첫 번째 문서 반환
            result = collection.delete_one(filter_query)

            # 결과 확인 및 출력
            if result.deleted_count > 0:
                print(f"코드 '{orgId}'가 {result.deleted_count}개가 성공적으로 삭제되었습니다.")
            else:
                print(f"조건에 맞는 코드 '{orgId}'를 찾을 수 없습니다.")

        
        except Exception as e:
            print(f"An error occurred: {e}")
            return None                    
       
    #--------------------------------------------------------------------------------------------------------------
    #test함수            
    def test(self):
    
        mongoManager = MongoManager()
        collection = mongoManager.getCollection("contents_org")  
        result = collection.update_many( {},{
                "$set": { 
                    "categoryList.$[].lastSucYMD": datetime.datetime(year=2025,month=1,day=16).strftime("%Y%m%d")               # 해당 카테고리의 LAST_SUC_YMD 수정, 마지막 수직일을 기록 
                }
            },
        ) 
 


#ContentsOrgService().find_all()