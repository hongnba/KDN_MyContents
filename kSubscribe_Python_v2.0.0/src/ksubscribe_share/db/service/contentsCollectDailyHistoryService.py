
from bson import ObjectId
import traceback
from typing import List
from datetime import date, datetime, timedelta, timezone
import pytz
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO, ContentsOrgCategory
from ksubscribe_share.db.dbmodelV2.contentsCollectDailyHistoryVO import ContentsCollectDailyHistoryVO
from ksubscribe_share.db.dbmodelV2.contentsCollectErrorVO import ContentsCollectErrorVO
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService
import logging


#컨텐츠 수집 이력 
class ContentsCollectDailyHistoryService():
    
    mongoManager = MongoManager()  # MongoManager 싱글톤 인스턴스를 사용
    collectionName = "contents_collect_daily_history" 
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ContentsCollectDailyHistoryService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        pass
#                regDt =None,  
                #regId  =None, 
                #editDt =None, 
                #editId  =None,) 

    def isExist(self):
        collection = self.mongoManager.getCollection(self.collectionName)

        # 오늘 날짜 00시00분00초를 UTC로
        today_start_utc = datetime.now().replace(hour=0,minute=0,second=0,microsecond=0).replace(tzinfo=pytz.timezone('Asia/Seoul') )
        today_end_utc = today_start_utc + timedelta(days=1)
        today_start_utc = today_start_utc.astimezone(pytz.utc)
        today_end_utc = today_end_utc.astimezone(pytz.utc)

        filter = {"collectDt": 
            {"$gte" : today_start_utc,
            "$lt": today_end_utc}}  # UTC 날짜와 비교

        result = collection.find_one(filter)
        
        #today_start_utc = datetime.now().replace(hour=10,minute=0,second=0,microsecond=0).replace(tzinfo=pytz.timezone('Asia/Seoul') )
        now = datetime.utcnow().replace(tzinfo=pytz.utc)

        if result is None:
            empty_history = ContentsCollectDailyHistoryVO(
                collectCount=0,
                totalCount=0,
                failCount=0,
                successCount=0,
                collectDt=now,
                scrappingCount=0,
                regDt=now,
                regId="admin",
                editDt=now,
                editId="admin",
            ).to_mongo()
            return collection.insert_one(empty_history)
        return None

    def insert_daily_history(self,collect_dt, total_count, success_count,fail_count,
                     collect_count,reg_dt,edit_dt):
        try:
            collection = self.mongoManager.getCollection(self.collectionName)
            insert_data = ContentsCollectDailyHistoryVO(
                collectDt = collect_dt,                                                     
                totalCount = total_count, 
                successCount  = success_count,
                failCount  = fail_count,
                collectCount  = collect_count,
                regDt =reg_dt,   
                editDt =edit_dt, )    
            collection.insert_one(insert_data.to_mongo())
 
        except Exception as e :
            print(e)
            pass 

    def update_daily_history(self,scraped_cnt):
        """금일 수집한 count 업데이트
        Args:
            scraped_cnt (_type_): _description_
        Returns:
            _type_: _description_
        """
        # 금일 수집한 count 업데이트 --> 최미화 질문, UTC 타임으로 비교해야 하지 않나요? 
        collection = self.mongoManager.getCollection(self.collectionName)
        today = datetime.now()
        start_of_day = datetime(today.year, today.month, today.day) 
        end_of_day = start_of_day + timedelta(days=1)
        filter = {
             "collectDt": {
                "$gte": start_of_day, "$lte": end_of_day 
                }}
        data = {"$set":{"scrappingCount":scraped_cnt }}
  
        result = collection.update_one(
            filter,
            data,
        ) 
        return result
    
    
    def inc_daily_scrapping_cnt(self):
        """금일 scrappingCount를 1개 증가시킨 
        """
        # 현재 UTC 날짜 가져오기
        today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today_start_utc = datetime.now().replace(hour=0,minute=0,second=0,microsecond=0).replace(tzinfo=pytz.timezone('Asia/Seoul') )
        today_end_utc = today_start_utc + timedelta(days=1)
        today_start_utc = today_start_utc.astimezone(pytz.utc)
        today_end_utc = today_end_utc.astimezone(pytz.utc)
        
        # MongoDB 업데이트 쿼리
        query = {"collectDt": {
            "$gte" : today_start_utc,
            "$lt": today_end_utc}}  # UTC 날짜와 비교
        update = {"$inc": {"scrappingCount": 1, 
                           }}

        # 업데이트 실행
        collection = self.mongoManager.getCollection(self.collectionName)
        result = collection.update_one(query, update)

        # 결과 출력
        #print(f"Modified documents: {result.modified_count}")   

    def inc_daily_collect_cnt(self,session = None):
        """금일 scrappingCount를 1개 증가시킨 
        """
        # 오늘 날짜 00시00분00초를 UTC로
        today_start_utc = datetime.now().replace(hour=0,minute=0,second=0,microsecond=0).replace(tzinfo=pytz.timezone('Asia/Seoul') )
        today_end_utc = today_start_utc + timedelta(days=1)
        today_start_utc = today_start_utc.astimezone(pytz.utc)
        today_end_utc = today_end_utc.astimezone(pytz.utc)


        # MongoDB 업데이트 쿼리
        # collect와 success 의 차이 
        filter = {"collectDt": 
            {"$gte" : today_start_utc,
            "$lt": today_end_utc}}  # UTC 날짜와 비교
        update = {"$inc": {"successCount": 1,
                           "totalCount": 1,
                           "collectCount": 1},
                  }

        # 업데이트 실행
        collection = self.mongoManager.getCollection(self.collectionName)
        result = collection.update_one(filter, update,session= session)

        # 결과 출력
        #print(f"Modified documents: {result.modified_count}")   

    def inc_daily_fail_cnt(self,session = None):
        """금일 scrappingCount를 1개 증가시킨 
        """
        # 현재 UTC 날짜 가져오기
        today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        # 오늘 날짜 00시00분00초를 UTC로
        today_start_utc = datetime.now().replace(hour=0,minute=0,second=0,microsecond=0).replace(tzinfo=pytz.timezone('Asia/Seoul') )
        today_end_utc = today_start_utc + timedelta(days=1)
        today_start_utc = today_start_utc.astimezone(pytz.utc)
        today_end_utc = today_end_utc.astimezone(pytz.utc)

        # MongoDB 업데이트 쿼리    
        filter = {"collectDt": 
            {"$gte" : today_start_utc,
            "$lt": today_end_utc}}  # UTC 날짜와 비교
        update = {"$inc": {"failCount": 1},
                  "$inc": {"totalCount": 1}
                  }

        # 업데이트 실행
        collection = self.mongoManager.getCollection(self.collectionName)
        result = collection.update_one(filter, update,session= session)

        # 결과 출력
        #print(f"Modified documents: {result.modified_count}")   

    def search_collect_daily_history_from_period(self, start_date: date, period: int):
        """
        설명 
        Args:
            OOO : 설명 
        Returns:
            OOO: 설명 
        """         
        try:
            start_datetime = datetime.combine(start_date, datetime.min.time())  # 0시로 초기화
            end_datetime = start_datetime + timedelta(days=period)  # 종료일 0시로 초기화
            query = {
                "collectDt": {
                    "$gte": start_datetime,  # 오늘의 0시 포함
                    "$lt": end_datetime      # 내일의 0시 미포함
                }
            }
            
            collection = self.mongoManager.getCollection(self.collectionName) 
            
            # 조건을 만족하는 여러 문서 반환
            results = list(collection.find(query))

            result_list = [ContentsCollectDailyHistoryVO.from_mongo(item) for item in results] 
            
            # 결과 반환 (결과가 없을 경우 None 반환)
            return result_list if result_list else None
        except Exception as e :
            print(f"An error occurred: {e}")
            return None
