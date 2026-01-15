from datetime import datetime, date, timedelta
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.dbmodelV2.contentsCollectRequestVO import ContentsCollectRequestVO


class ContentsCollectRequestService():
    
    mongoManager = MongoManager()           # MongoManager 싱글톤 인스턴스를 사용
    collectionName = "contents_collect_request"
        
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ContentsCollectRequestService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        pass 

   
    def getRequestsFromPeriod(self, start_date: date, period: int):
        try:
            start_datetime = datetime.combine(start_date, datetime.min.time())  # 0시로 초기화
            end_datetime = start_datetime + timedelta(days=period)  # 종료일 다음 날 0시로 초기화
            
            
            query = {
                "regDt": {
                    "$gte": start_datetime,  # 오늘의 0시 포함
                    "$lt": end_datetime      # 내일의 0시 미포함
                }
            }
            
            collection = self.mongoManager.getCollection(self.collectionName) 
            
            # 조건을 만족하는 여러 문서 반환
            results = list(collection.find(query))

            result_list = [ContentsCollectRequestVO.from_mongo(item) for item in results] 
            
            # 결과 반환 (결과가 없을 경우 None 반환)
            return result_list if result_list else None
        
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
        

    #----------------------------------------------------------------------------------------
    # remove 
    #----------------------------------------------------------------------------------------

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
           
        