"""
Calendar Service - 일별 캘린더 결과 관리
negativeResult, positiveResult, neutralResult는 현재 월의 일별 데이터만 관리
"""

from datetime import datetime, timedelta
from typing import Dict, List
import pytz

from ksubscribe_share.db.service.baseQueryService import BaseQueryService
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO


class CalendarService(BaseQueryService):
    """일별 캘린더 결과 전용 서비스"""
    
    mongoManager = MongoManager()
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(CalendarService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        super().__init__()

    def get_calendar_results(self, orgId: str) -> Dict:
        """
        캘린더 결과 조회 (현재 월의 일별 데이터)
        
        Args:
            orgId: 기관 ID
            
        Returns:
            Dict: 일별 결과 데이터
        """
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        
        # 현재 월의 시작일과 종료일 계산 (첫째 날부터 오늘까지)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # 기존 캘린더 데이터 조회
        existing_calendar = self._get_existing_calendar_data(orgId, now.strftime('%Y-%m'))
        
        # 오늘이 월의 첫날인지 확인
        is_first_day_of_month = now.day == 1
        
        if is_first_day_of_month:
            # 새로운 월: 이전 데이터 삭제하고 새로 생성
            self._delete_previous_calendar_data(orgId, now.strftime('%Y-%m'))
            calendar_results = self._calculate_new_month_calendar(orgId, month_start, month_end)
        else:
            # 기존 월: 오늘 데이터만 업데이트
            calendar_results = self._update_today_calendar(orgId, existing_calendar, now)
        
        return calendar_results

    def _get_existing_calendar_data(self, orgId: str, month: str) -> Dict:
        """기존 캘린더 데이터 조회"""
        try:
            collection = self.mongoManager.getCollection("daily_calendar_results")
            doc = collection.find_one({
                "orgId": orgId,
                "month": month
            })
            
            if doc:
                return {
                    'positiveResult': doc.get('positiveResult', {}),
                    'negativeResult': doc.get('negativeResult', {}),
                    'neutralResult': doc.get('neutralResult', {})
                }
            else:
                return {
                    'positiveResult': {},
                    'negativeResult': {},
                    'neutralResult': {}
                }
        except Exception as e:
            return {
                'positiveResult': {},
                'negativeResult': {},
                'neutralResult': {}
            }

    def _delete_previous_calendar_data(self, orgId: str, month: str):
        """이전 캘린더 데이터 삭제"""
        try:
            collection = self.mongoManager.getCollection("daily_calendar_results")
            collection.delete_many({
                "orgId": orgId,
                "month": {"$ne": month}  # 현재 월이 아닌 모든 데이터 삭제
            })
        except Exception as e:
            print(f"Failed to delete previous calendar data: {str(e)}")

    def _calculate_new_month_calendar(self, orgId: str, month_start: datetime, month_end: datetime) -> Dict:
        """새로운 월의 캘린더 데이터 계산"""
        # 현재 월의 컨텐츠 조회
        contents_data = self._get_contents_for_period(orgId, month_start, month_end)
        
        # 일별 결과 계산
        daily_results = self._calculate_daily_results_for_month(contents_data, orgId, month_start, month_end)
        
        # 데이터베이스에 저장
        self._save_calendar_data(orgId, daily_results)
        
        return daily_results

    def _update_today_calendar(self, orgId: str, existing_calendar: Dict, now: datetime) -> Dict:
        """오늘 데이터만 업데이트"""
        # 오늘의 컨텐츠 조회
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        today_contents = self._get_contents_for_period(orgId, today_start, today_end)
        
        # 오늘의 결과 계산
        today_results = self._calculate_today_results(today_contents, orgId)
        
        # 기존 데이터에 오늘 결과 업데이트
        updated_calendar = existing_calendar.copy()
        date_key = now.strftime('%Y-%m-%d')
        
        updated_calendar['positiveResult'][date_key] = today_results['positiveResult']
        updated_calendar['negativeResult'][date_key] = today_results['negativeResult']
        updated_calendar['neutralResult'][date_key] = today_results['neutralResult']
        
        # 데이터베이스에 저장
        self._save_calendar_data(orgId, updated_calendar)
        
        return updated_calendar

    def _get_contents_for_period(self, orgId: str, start_date: datetime, end_date: datetime) -> List[ContentsVO]:
        """지정된 기간의 기관 관련 컨텐츠 조회"""
        collection = self.mongoManager.getCollection("contents")
        
        query = {
            "contentsOrgId": orgId,
            "pubDt": {
                "$gte": start_date,
                "$lte": end_date
            },
            "metaSucYN": "Y"  # 분석이 완료된 컨텐츠만
        }
        
        cursor = collection.find(query)
        contents_list = []
        
        for doc in cursor:
            contents = ContentsVO.from_mongo(doc)
            contents_list.append(contents)
        
        return contents_list

    def _calculate_daily_results_for_month(self, contents_list: List[ContentsVO], orgId: str, month_start: datetime, month_end: datetime) -> Dict:
        """월의 일별 결과 계산"""
        positive_result = {}
        negative_result = {}
        neutral_result = {}
        
        # 현재 월의 모든 날짜에 대해 초기화 (-99.0 for missing days)
        current_date = month_start
        while current_date <= month_end:
            date_key = current_date.strftime('%Y-%m-%d')
            positive_result[date_key] = -99.0
            negative_result[date_key] = -99.0
            neutral_result[date_key] = -99.0
            current_date += timedelta(days=1)
        
        # 날짜별로 그룹화
        date_groups = {}
        for contents in contents_list:
            if not contents.pubDt:
                continue
                
            date_key = contents.pubDt.strftime('%Y-%m-%d')
            if date_key not in date_groups:
                date_groups[date_key] = []
            date_groups[date_key].append(contents)
        
        # 각 날짜별로 감정 분석
        for date_key, day_contents in date_groups.items():
            positive_count = 0
            negative_count = 0
            neutral_count = 0
            
            for contents in day_contents:
                if not contents.contentsMeta or not contents.contentsMeta.sentiments:
                    continue
                    
                for sentiment in contents.contentsMeta.sentiments:
                    if sentiment.orgId == orgId:
                        if sentiment.positiveRatio and sentiment.positiveRatio > 0.5:
                            positive_count += 1
                        elif sentiment.negativeRatio and sentiment.negativeRatio > 0.5:
                            negative_count += 1
                        else:
                            neutral_count += 1
                        break
            
            # 비율 계산
            total = positive_count + negative_count + neutral_count
            if total > 0:
                positive_result[date_key] = (positive_count / total) * 100
                negative_result[date_key] = (negative_count / total) * 100
                neutral_result[date_key] = (neutral_count / total) * 100
        
        return {
            'positiveResult': positive_result,
            'negativeResult': negative_result,
            'neutralResult': neutral_result
        }

    def _calculate_today_results(self, contents_list: List[ContentsVO], orgId: str) -> Dict:
        """오늘의 결과 계산"""
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        
        for contents in contents_list:
            if not contents.contentsMeta or not contents.contentsMeta.sentiments:
                continue
                
            for sentiment in contents.contentsMeta.sentiments:
                if sentiment.orgId == orgId:
                    if sentiment.positiveRatio and sentiment.positiveRatio > 0.5:
                        positive_count += 1
                    elif sentiment.negativeRatio and sentiment.negativeRatio > 0.5:
                        negative_count += 1
                    else:
                        neutral_count += 1
                    break
        
        # 비율 계산
        total = positive_count + negative_count + neutral_count
        if total > 0:
            positive_ratio = (positive_count / total) * 100
            negative_ratio = (negative_count / total) * 100
            neutral_ratio = (neutral_count / total) * 100
        else:
            positive_ratio = -99.0
            negative_ratio = -99.0
            neutral_ratio = -99.0
        
        return {
            'positiveResult': positive_ratio,
            'negativeResult': negative_ratio,
            'neutralResult': neutral_ratio
        }

    def _save_calendar_data(self, orgId: str, calendar_data: Dict):
        """캘린더 데이터를 데이터베이스에 저장"""
        try:
            collection = self.mongoManager.getCollection("daily_calendar_results")
            
            # 현재 월 정보
            kst = pytz.timezone('Asia/Seoul')
            now = datetime.now(kst)
            month_key = now.strftime('%Y-%m')
            
            # 기존 데이터 확인
            existing_doc = collection.find_one({
                "orgId": orgId,
                "month": month_key
            })
            
            # 데이터 업데이트 또는 생성
            calendar_doc = {
                "orgId": orgId,
                "month": month_key,
                "positiveResult": calendar_data['positiveResult'],
                "negativeResult": calendar_data['negativeResult'],
                "neutralResult": calendar_data['neutralResult'],
                "last_updated": now
            }
            
            if existing_doc:
                collection.update_one(
                    {"_id": existing_doc["_id"]},
                    {"$set": calendar_doc}
                )
            else:
                collection.insert_one(calendar_doc)
                
        except Exception as e:
            print(f"Failed to save calendar data: {str(e)}")

    def get_daily_results_from_db(self, orgId: str, month: str = None) -> Dict:
        """
        데이터베이스에서 일별 결과 조회
        
        Args:
            orgId: 기관 ID
            month: 월 (YYYY-MM 형식, None이면 현재 월)
            
        Returns:
            Dict: 일별 결과 데이터
        """
        try:
            collection = self.mongoManager.getCollection("daily_calendar_results")
            
            if not month:
                kst = pytz.timezone('Asia/Seoul')
                now = datetime.now(kst)
                month = now.strftime('%Y-%m')
            
            doc = collection.find_one({
                "orgId": orgId,
                "month": month
            })
            
            if doc:
                return {
                    'positiveResult': doc.get('positiveResult', {}),
                    'negativeResult': doc.get('negativeResult', {}),
                    'neutralResult': doc.get('neutralResult', {}),
                    'last_updated': doc.get('last_updated')
                }
            else:
                return {
                    'positiveResult': {},
                    'negativeResult': {},
                    'neutralResult': {}
                }
                
        except Exception as e:
            return {
                'positiveResult': {},
                'negativeResult': {},
                'neutralResult': {},
                'error': str(e)
            }
