
from bson import ObjectId
from datetime import datetime, date, timedelta
from typing import List

from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO, ContentsOrgCategory
from ksubscribe_share.db.dbmodelV2.contentsCollectHistoryVO import ContentsCollectDetail, ContentsCollect, ContentsCollectHistoryVO
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
from ksubscribe_share.db.dbmodelV2.memberVO import MemberVO
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.service.baseQueryService import BaseQueryService
from ksubscribe_share.db.service.commCodeService import CommCodeService



from Crypto.Cipher import AES
import base64
import ksubscribe_share.config as Conf

#컨텐츠 수집 이력 
class MemberService():
    
    mongoManager = MongoManager()           # MongoManager 싱글톤 인스턴스를 사용
    collectionName = "member_account"
        
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MemberService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        pass 
   
    def getKeyword(self, sucYN : bool, lastSucYMD : int,  contentsOrg : ContentsOrgVO, category : ContentsOrgCategory):
        
        #ContentsOrgCategory에도 SUC_YN, LAST_SUC_YMD 값을 갱신해야 함. 
        return None
    
    def addMember(self, member:MemberVO):
        
        result = BaseQueryService.insert_one(member)
        
        if result.inserted_id: 
            print(f"{member.mberId} : insert 되었습니다.")
        else:
            print(f"{member.mberId} : insert 실패하였습니다")
    
    def getMember(self, mberId:str) -> MemberVO: 
        
        collection = self.mongoManager.getCollection(self.collectionName)
        result = collection.find_one({"mberId": mberId})
        return MemberVO.from_mongo(result)
    
    def getMemberListByOrgName(self, orgName:str) -> List[MemberVO]: 
        
        collection = self.mongoManager.getCollection(self.collectionName)
        cursor = collection.find({"orgName": orgName})
        return [MemberVO.from_mongo(doc) for doc in cursor] 
               
    def subscribeKeyword(self, mberId:str, keyword:str): 
        
        try:

            collection = self.mongoManager.getCollection(self.collectionName)
        
            # 업데이트 조건과 업데이트 동작 정의
            filter_condition = {"mberId": mberId}  # id가 "aaa"인 문서 찾기
            update_action = {
                "$addToSet": {
                    "keywordSubscribe": keyword     # wordList의 모든 요소 추가
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
        
    def subscribeKeywordList(self, mberId:str, keywords:List[str]): 
        
        try:

            collection = self.mongoManager.getCollection(self.collectionName)
        
            # 업데이트 조건과 업데이트 동작 정의
            filter_condition = {"mberId": mberId}  # id가 "aaa"인 문서 찾기
            update_action = {
                "$addToSet": {
                    "keywordSubscribe": {"$each": keywords}     # wordList의 모든 요소 추가
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
       
    def subscribeCateId(self, mberId:str, orgId:str, orgName:str, cateId:str, cateName:str): 
        
        try:
            collection = self.mongoManager.getCollection(self.collectionName)

            # Step 1: contentsOrgSubscribe에 orgId가 이미 존재하는지 확인
            filter_condition = {"mberId": mberId, "contentsOrgSubscribe.orgId": orgId}
            existing_document = collection.find_one(filter_condition)

            if existing_document:
                # Step 2: 기존 orgId의 categoryList에 중복되지 않는 cateId, cateName 추가
                update_action = {
                    "$addToSet": {
                        "contentsOrgSubscribe.$.categoryList": {
                            "cateId": cateId,
                            "cateName": cateName
                        }
                    }
                }
                result = collection.update_one(filter_condition, update_action)

            else:
                # Step 3: orgId가 없으면 새로운 orgId와 categoryList 추가
                update_action = {
                    "$addToSet": {
                        "contentsOrgSubscribe": {
                            "orgId": orgId,
                            "orgName": orgName,
                            "categoryList": [
                                {
                                    "cateId": cateId,
                                    "cateName": cateName
                                }
                            ]
                        }
                    }
                }
                result = collection.update_one({"mberId": mberId}, update_action, upsert=True)

            # 결과 로그 출력
            if result.modified_count > 0:
                print("문서가 성공적으로 업데이트되었습니다.")
            elif result.matched_count > 0:
                print("조건에 맞는 문서는 있지만 업데이트할 데이터가 없습니다.")
            else:
                print("조건에 맞는 문서를 찾을 수 없습니다.")

        except Exception as e:
            print(f"오류가 발생했습니다: {e}")

    def subscribeCateId_old_duplicate_error(self, mberId:str, orgId:str, orgName:str, cateId:str, cateName:str): 
        
        try:

            collection = self.mongoManager.getCollection(self.collectionName)

            """
            member의 contentsOrgSubscribe에 orgId, orgName이 없으면 추가
            orgId, orgName이 이미 있으면 해당 org의 categoryList에 중복되지 않는 cateId, cateName만 추가
            """
            # 조건: member 문서에서 mberId가 일치하는 항목
            filter_condition = {"mberId": mberId}
            
            # 업데이트 동작
            update_action = {
                # orgId와 orgName이 없으면 추가
                "$addToSet": {
                    "contentsOrgSubscribe": {
                        "orgId": orgId,
                        "orgName": orgName,
                        "categoryList": [
                            {
                                "cateId": cateId,
                                "cateName": cateName
                            }                            
                        ]
                    }
                }
            }

            # Step 1: orgId, orgName이 없는 경우 추가
            result = collection.update_one(filter_condition, update_action)
            
            # Step 2: orgId, orgName이 이미 있는 경우 categoryList에만 추가
            if result.matched_count > 0:  # 문서가 존재할 때만 실행
                update_action = {
                    "$addToSet": {
                        "contentsOrgSubscribe.$[org].categoryList": {
                            "cateId": cateId,
                            "cateName": cateName
                        }
                    }
                }
                array_filters = [{"org.orgId": orgId, "org.orgName": orgName}]
                result = collection.update_one(
                    filter_condition, 
                    update_action, 
                    array_filters=array_filters
                )

            # 결과 출력
            if result.modified_count > 0:
                print("문서가 성공적으로 업데이트되었습니다.")
            elif result.matched_count > 0:
                print("조건에 맞는 문서는 있지만 업데이트할 데이터가 없습니다.")
            else:
                print("조건에 맞는 문서를 찾을 수 없습니다.")
                
        except Exception as e:
            print(f"An error occurred: {e}")

    def collectKeywordSubscribe(self):
        
        collection = self.mongoManager.getCollection(self.collectionName)
        
        # 모든 문서를 조회
        documents = collection.find()

        for doc in documents:
            if "keywordSubscribe" in doc:
                # keywordSubscribe 읽기
                keyword_subscribe = doc["keywordSubscribe"]

                # keywordSubscribe를 List[str]로 변환
                if isinstance(keyword_subscribe, list):
                    # 중첩된 배열을 평탄화(flatten)
                    flattened = []
                    for item in keyword_subscribe:
                        if isinstance(item, list):
                            flattened.extend(item)  # 중첩 배열 풀기
                        elif isinstance(item, str):
                            flattened.append(item)  # 문자열 추가

                    # 중복 제거 및 정렬 (옵션)
                    flattened = sorted(set(flattened))

                    # keywordSubscribe 업데이트
                    collection.update_one(
                        {"_id": doc["_id"]},  # 현재 문서의 ID 기준
                        {"$set": {"keywordSubscribe": flattened}}
                    )
                    print(f"Updated with keywordSubscribe: {flattened}")
                else:
                    print(f"Skipping with invalid keywordSubscribe format")
 
    # 관리자 계정의 Tele Chat ID 를 가져오는 함수
    def getAdminMembersTeleChatIds(self):
        try:
            collection = self.mongoManager.getCollection(self.collectionName) 
            
            query = {
                "mberType": "F0003",
                "mberAuthority": "AUTH00001",
            }
            # 반환할 필드 지정 
            projection = {
                "mberId": 1,
                "mberAuthority": 1,
                "teleChatId": 1,
            }
            
            # 조건을 만족하는 여러 문서 반환
            results = list(collection.find(query, projection))

            result_list = [MemberVO.from_mongo(item) for item in results] 
            
            # 결과 반환 (결과가 없을 경우 None 반환)
            return result_list if result_list else None
        
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
            
    def getSignedUpMemberFromPeriod(self, start_date: date, period: int):
        try:
            start_datetime = datetime.combine(start_date, datetime.min.time())  # 0시로 초기화
            end_datetime = start_datetime + timedelta(days=period)  # 종료일 0시로 초기화
            
            
            query = {
                "joinDt": {
                    "$gte": start_datetime,  # 오늘의 0시 포함
                    "$lt": end_datetime      # 내일의 0시 미포함
                }
            }
            
            # 반환할 필드 지정 
            projection = {
                "_id" : 1,
                "mberId": 1,
            }
            
            collection = self.mongoManager.getCollection(self.collectionName) 
            
            # 조건을 만족하는 여러 문서 반환
            results = list(collection.find(query, projection))

            result_list = [MemberVO.from_mongo(item) for item in results] 
            
            # 결과 반환 (결과가 없을 경우 None 반환)
            return result_list if result_list else None
        
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
                
    def getOrgNameDistinct(self):
        
        collection = self.mongoManager.getCollection(self.collectionName)
        query = {}
        distinct_org_names = collection.distinct("orgName", query)        
        return distinct_org_names
       
                    
    def deduplicate_contents(self, contentsOrgSubscribe):
        # 중간 결과 저장용
        org_dict = {}

        # 중복 제거 작업
        for org in contentsOrgSubscribe:
            orgId = org["orgId"]
            categoryList = org.get("categoryList", [])

            # orgId 기준으로 그룹화
            if orgId not in org_dict:
                org_dict[orgId] = {"orgId": orgId, "orgName": org.get("orgName"), "categoryList": []}

            # cateId 중복 제거
            existing_cate_ids = {cate["cateId"] for cate in org_dict[orgId]["categoryList"]}
            for category in categoryList:
                if category["cateId"] not in existing_cate_ids:
                    org_dict[orgId]["categoryList"].append(category)
                    existing_cate_ids.add(category["cateId"])

        # 결과를 리스트로 변환
        return list(org_dict.values())        
                
    
    def deduplicate_and_update(self):
        
        commCodeService = CommCodeService()
        try:
            collection = self.mongoManager.getCollection(self.collectionName)
            
            # 모든 문서 가져오기
            documents = collection.find()

            for doc in documents:
                # 중복 제거 작업
                contentsOrgSubscribe = doc.get("contentsOrgSubscribe", [])
                org_dict = {}

                # orgId와 cateId를 기준으로 중복 제거
                for org in contentsOrgSubscribe:
                    orgId = org["orgId"]
                    orgName = commCodeService.get_orgName_by_orgId(orgId) #org.get("orgName")
                    categoryList = org.get("categoryList", [])

                    if orgId not in org_dict:
                        org_dict[orgId] = {"orgId": orgId, "orgName": orgName, "categoryList": []}

                             
                    existing_cate_ids = {cate["cateId"] for cate in org_dict[orgId]["categoryList"]}
                    for category in categoryList:
                        if category["cateId"] not in existing_cate_ids:
                            cateId = category["cateId"]
                            cateName = commCodeService.get_cateName_by_cateId(cateId)  # cateName 설정
                            category["cateName"] = cateName  # cateName 추가
                            org_dict[orgId]["categoryList"].append(category)
                            existing_cate_ids.add(cateId)                            

                # 중복 제거된 데이터로 contentsOrgSubscribe 업데이트
                deduplicated_contents = list(org_dict.values())
                collection.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"contentsOrgSubscribe": deduplicated_contents}}
                )

                print(f"Document with _id {doc['_id']} updated successfully.")

        except Exception as e:
            print(f"An error occurred: {e}")  


    data_mapping = {
    " 한전KDN" : "한전KDN(주)" ,
    " 한전KDN(주)" : "한전KDN(주)" ,
    "&apos;" : "개인" ,
    "(주)쓰리웨이소프트" : "개인" ,
    "(주)한전KDN" : "한전KDN(주)" ,
    "(주)한전kdn" : "한전KDN(주)" ,
    "KDN" : "한전KDN(주)" ,
    "kdn" : "한전KDN(주)" ,
    "경기강원지역본부" : "한전KDN(주)" ,
    "란전KDN" : "한전KDN(주)" ,
    "솔비트" : "개인" ,
    "에임위드" : "개인" ,
    "전력거래소" : "한국전력거래소" ,
    "전북사업처" : "한전KDN(주)" ,
    "주식회사 에임위드" : "개인" ,
    "한국남부발전" : "한국남부발전(주)" ,
    "한국서부발전" : "한국서부발전(주)" ,
    "한전 KDN" : "한전KDN(주)" ,
    "한전 kdn" : "한전KDN(주)" ,
    "한전KDN" : "한전KDN(주)" ,
    "한전KDN " : "한전KDN(주)" ,
    "한전KDN 강북지사" : "한전KDN(주)" ,
    "한전KDN 강원사업처" : "한전KDN(주)" ,
    "한전KDN 강원시압처" : "한전KDN(주)" ,
    "한전KDN 강원지역사업처" : "한전KDN(주)" ,
    "한전KDN 경기강원지역본부" : "한전KDN(주)" ,
    "한전KDN 경기북부사업처" : "한전KDN(주)" ,
    "한전KDN 서울인천지역본부 강북지사" : "한전KDN(주)" ,
    "한전KDN 전북사업처" : "한전KDN(주)" ,
    "한전KDN(wn)" : "한전KDN(주)" ,
    "한전KDN(주)" : "한전KDN(주)" ,
    "한전KDN(주) 경기강원지역본부" : "한전KDN(주)" ,
    "한전KDN(주)부산울산경남지역본부" : "한전KDN(주)" ,
    "한전KDN_경기강원_직할" : "한전KDN(주)" ,
    "한전KDN경기강원 지역본부 직할" : "한전KDN(주)" ,
    "한전KDN주식회사" : "한전KDN(주)" ,
    "한전KPS" : "한전KPS(주)" ,
    "한전Kdn" : "한전KDN(주)" ,
    "한전kdn" : "한전KDN(주)" ,
    "한전kdn 경기강원지역본부" : "한전KDN(주)" ,
    "한전kdn(주)" : "한전KDN(주)" ,
    "한전kdn경기강원지역본부" : "한전KDN(주)" ,
    "한전kdn주식회사" : "한전KDN(주)" ,
    "한전케이디앤" : "한전KDN(주)" ,
    "한전케이디엔" : "한전KDN(주)" ,
    "한전케이디엔(주)" : "한전KDN(주)" ,
    "한전케이디엔주식회사" : "한전KDN(주)" ,
    "햔전kdn" : "한전KDN(주)"
    }
    
    def update_mberType_authority(self, mberId: str, mberType: str, authority: str):
        """
        특정 회원의 mberType과 authority만 업데이트하는 함수
        """
        collection = self.mongoManager.getCollection(self.collectionName)

        # 업데이트 조건과 수정 내용 정의
        filter_query = {"mberId": mberId}  # mberId로 회원 식별
        update_data = {
            "$set": {
                "mberType": mberType,
                "mberAuthority": authority
            }
        }

        # MongoDB 업데이트 수행
        result = collection.update_one(filter_query, update_data)

        if result.matched_count == 0:
            print(f"No member found with mberId: {mberId}")
        else:
            print(f"Updated mberType and authority for mberId: {mberId}")
      
          
    def update_mberType_authority_orgId(self, mberId: str, mberType: str, authority: str, orgId:str, orgName:str):
        """
        특정 회원의 mberType과 authority만 업데이트하는 함수
        """
        collection = self.mongoManager.getCollection(self.collectionName)

        # 업데이트 조건과 수정 내용 정의
        filter_query = {"mberId": mberId}  # mberId로 회원 식별
        update_data = {
            "$set": {
                "mberType": mberType,
                "mberAuthority": authority,
                "orgId" : orgId,
                "orgName" : orgName
            }
        }

        # MongoDB 업데이트 수행
        result = collection.update_one(filter_query, update_data)

        if result.matched_count == 0:
            print(f"No member found with mberId: {mberId}")
        else:
            print(f"Updated mberType and authority for mberId: {mberId}")
                

    def update_receiveYN(self, mberId: str, emailReceiveYN: str, kakaoReceiveYN: str, teleReceiveYN:str):
        """
        특정 회원의 mberType과 authority만 업데이트하는 함수
        """
        collection = self.mongoManager.getCollection(self.collectionName)

        # 업데이트 조건과 수정 내용 정의
        filter_query = {"mberId": mberId}  # mberId로 회원 식별
        update_data = {
            "$set": {
                "emailReceiveYN": emailReceiveYN,
                "kakaoReceiveYN": kakaoReceiveYN,
                "teleReceiveYN": teleReceiveYN
            }
        }

        # MongoDB 업데이트 수행
        result = collection.update_one(filter_query, update_data)

        if result.matched_count == 0:
            print(f"No member found with mberId: {mberId}")
        else:
            print(f"Updated mberType and authority for mberId: {mberId}")
                      
                    
    #운영 DB MberType 
    def convert_mbertype(self):
        
        commCodeService = CommCodeService()
        try:
            
            for index, (bad_orgName, orgName) in enumerate(self.data_mapping.items()):
                print(f"Index: {index}, bad_orgName: {bad_orgName}, orgName: {orgName}")       
                
                
                orgId = commCodeService.get_orgId_byOrgName(orgName)
                memberList:List[MemberVO] = self.getMemberListByOrgName(bad_orgName)

                if orgName == "개인":                 
                    for member in memberList:     
                        self.update_mberType_authority(member.mberId, "F0002", "SYSTEM001")

                else:
                    for member in memberList:     
                        self.update_mberType_authority_orgId(member.mberId, "F0001", "SYSTEM001", orgId, orgName)
                    
        except Exception as e:
            print(f"An error occurred: {e}")   
                
                
    #-----------------------------------------------------------------------
    #remove
    #-----------------------------------------------------------------------
    

    def remove_org_commcode(self, orgId: str):
        """
        특정 orgId를 contentsOrgSubscribe 리스트에서 삭제하는 메서드

        Args:
            orgId (str): 삭제할 orgId 값

        Returns:
            int: 삭제된 문서 개수
        """             
        
        try:
            collection = self.mongoManager.getCollection(self.collectionName)

            # 필터 조건: 특정 orgId를 가진 항목이 존재하는 문서 찾기
            filter_query = {
                "contentsOrgSubscribe.orgId": orgId
            }
            
            # 삭제 연산: $pull을 사용하여 리스트에서 해당 orgId 제거
            update_query = {
                "$pull": {
                    "contentsOrgSubscribe": {"orgId": orgId}
                }
            }

            # 업데이트 실행
            result = collection.update_many(filter_query, update_query)

            # 결과 확인 및 출력
            if result.modified_count > 0:
                print(f"코드 '{orgId}'가 {result.modified_count}개의 문서에서 성공적으로 삭제되었습니다.")
            else:
                print(f"조건에 맞는 코드 '{orgId}'를 찾을 수 없습니다.")

            return result.modified_count

        except Exception as e:
            print(f"An error occurred: {e}")
            return None
           


    def remove_keyword(self, keyword: str):
        """
        특정 키워드를 keywordSubscribe 배열에서 삭제하는 함수

        Args:
            keyword (str): 삭제할 키워드 값

        Returns:
            int: 삭제된 문서 개수
        """              
        try:
            collection = self.mongoManager.getCollection(self.collectionName)

            # 삭제 연산: $pull을 사용하여 keywordSubscribe 배열에서 해당 키워드 제거
            update_query = {
                "$pull": {
                    "keywordSubscribe": keyword
                }
            }

            # 모든 문서에서 해당 키워드 삭제
            result = collection.update_many({}, update_query)

            # 결과 확인 및 출력
            if result.modified_count > 0:
                print(f"키워드 '{keyword}'가 {result.modified_count}개의 문서에서 성공적으로 삭제되었습니다.")
            else:
                print(f"조건에 맞는 키워드 '{keyword}'를 찾을 수 없습니다.")

            return result.modified_count

        except Exception as e:
            print(f"An error occurred: {e}")
            return None
                      