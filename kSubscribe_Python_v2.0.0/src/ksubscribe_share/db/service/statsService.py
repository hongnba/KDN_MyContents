from bson import ObjectId
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
from pymongo import DESCENDING
import pytz

from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO, SentimentInfo
from ksubscribe_share.db.service.baseQueryService import BaseQueryService
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.dbmodelV2.dailyStatsVO import DailyStatsVO
from ksubscribe_share.db.dbmodelV2.weeklyStatsVO import WeeklyStatsVO
from ksubscribe_share.db.dbmodelV2.monthlyStatsVO import MonthlyStatsVO
from ksubscribe_share.db.dbmodelV2.keywordStatVO import KeywordStatVO

class StatsService(BaseQueryService):
    """기관 평판 통계 서비스 - 일별/주별/월별 통계 관리"""
    
    mongoManager = MongoManager()
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(StatsService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        super().__init__()

    def count_for_period(self, orgId: str, period: str, start_date: datetime = None, end_date: datetime = None) -> Union[DailyStatsVO, WeeklyStatsVO, MonthlyStatsVO]:
        """
        일정 기간 내에 해당 기관 관련 데이터 집계 계산
        
        Args:
            orgId: 기관 ID
            period: 기간 타입 ('day', 'week', 'month')
            start_date: 시작 날짜 (선택사항)
            end_date: 종료 날짜 (선택사항)
            
        Returns:
            계산된 통계 객체
        """
        # 날짜 범위 설정
        if not start_date or not end_date:
            start_date, end_date = self._get_period_dates(period)
        
        # Contents 컬렉션에서 해당 기관의 데이터 조회 -> List[ContentsVO]
        contents_data = self._get_contents_for_period(orgId, start_date, end_date)
        
        # 통계 계산
        stats_data = self._calculate_stats(orgId, contents_data, start_date, end_date, period)
        
        # 적절한 통계 객체 생성 및 저장
        if period == 'day':
            stats = DailyStatsVO(**stats_data)
        elif period == 'week':
            stats = WeeklyStatsVO(**stats_data)
        elif period == 'month':
            stats = MonthlyStatsVO(**stats_data)
        else:
            raise ValueError(f"Invalid period: {period}. Must be 'day', 'week', or 'month'")
        
        # 기존 데이터가 있으면 업데이트, 없으면 새로 생성
        existing_stats = self.get_for_period(orgId, period, start_date, end_date)
        if existing_stats:
            stats._id = existing_stats._id
            self.update_one(stats)
        else:
            self.insert_one(stats)
        
        return stats

    def get_for_period(self, orgId: str, period: str, start_date: datetime = None, end_date: datetime = None) -> Optional[Union[DailyStatsVO, WeeklyStatsVO, MonthlyStatsVO]]:
        """
        일정 기간 내에 해당 기관 관련 집계 데이터 가져오기
        
        Args:
            orgId: 기관 ID
            period: 기간 타입 ('day', 'week', 'month')
            start_date: 시작 날짜 (선택사항)
            end_date: 종료 날짜 (선택사항)
            
        Returns:
            기존 통계 객체 또는 None
        """
        # 날짜 범위 설정
        if not start_date or not end_date:
            start_date, end_date = self._get_period_dates(period)
        
        # 적절한 컬렉션명 설정
        if period == 'day':
            collection_name = "daily_stats"
            stats_class = DailyStatsVO
        elif period == 'week':
            collection_name = "weekly_stats"
            stats_class = WeeklyStatsVO
        elif period == 'month':
            collection_name = "monthly_stats"
            stats_class = MonthlyStatsVO
        else:
            raise ValueError(f"Invalid period: {period}. Must be 'day', 'week', or 'month'")
        
        # 해당 기간의 통계 데이터 조회
        collection = self.mongoManager.getCollection(collection_name)
        query = {
            "orgId": orgId,
            "last_calculate_date": {
                "$gte": start_date,
                "$lte": end_date
            }
        }
        
        document = collection.find_one(query, sort=[("last_calculate_date", DESCENDING)])
        
        if document:
            return stats_class.from_mongo(document)
        
        return None

    def _get_period_dates(self, period: str) -> tuple:
        """기간에 따른 시작/종료 날짜 계산"""
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        
        if period == 'day':
            # 오늘 00:00:00 ~ 23:59:59
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period == 'week':
            # 7일 전 00:00:00 ~ 오늘 23:59:59
            start_date = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period == 'month':
            # 30일 전 00:00:00 ~ 오늘 23:59:59
            start_date = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        else:
            raise ValueError(f"Invalid period: {period}")
        
        return start_date, end_date

    def _get_contents_for_period(self, orgId: str, start_date: datetime, end_date: datetime) -> List[ContentsVO]:
        """지정된 기간의 기관 관련 컨텐츠 조회"""
        collection = self.mongoManager.getCollection("contents")
        
        query = {
            "contentsOrgId": orgId,
            #리자: pubDt로 하는 건 맞는지..?
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

    def _calculate_stats(self, orgId: str, contents_list: List[ContentsVO], start_date: datetime, end_date: datetime, period: str) -> Dict:
        """컨텐츠 리스트로부터 통계 계산"""
        positive_keywords = {}
        negative_keywords = {}
        total_articles = len(contents_list)
        positive_count = 0
        negative_count = 0
        
        for contents in contents_list:
            if not contents.contentsMeta or not contents.contentsMeta.sentiments:
                continue
            
            # 감정 분석 결과 처리
            for sentiment in contents.contentsMeta.sentiments:
                if sentiment.orgId == orgId:
                    # 긍정/부정 비율 계산
                    if sentiment.positiveRatio and sentiment.positiveRatio > 0.5:
                        positive_count += 1
                    elif sentiment.negativeRatio and sentiment.negativeRatio > 0.5:
                        negative_count += 1
                    
                    # 긍정 키워드 처리
                    if sentiment.positiveKeywords:
                        for keyword in sentiment.positiveKeywords:
                            if keyword in positive_keywords:
                                positive_keywords[keyword]['count'] += 1
                                positive_keywords[keyword]['related_articles'].append(str(contents._id))
                            else:
                                positive_keywords[keyword] = {
                                    'keyword': keyword,
                                    'count': 1,
                                    'related_articles': [str(contents._id)]
                                }
                    
                    # 부정 키워드 처리
                    if sentiment.negativeKeywords:
                        for keyword in sentiment.negativeKeywords:
                            if keyword in negative_keywords:
                                negative_keywords[keyword]['count'] += 1
                                negative_keywords[keyword]['related_articles'].append(str(contents._id))
                            else:
                                negative_keywords[keyword] = {
                                    'keyword': keyword,
                                    'count': 1,
                                    'related_articles': [str(contents._id)]
                                }
        
        # 키워드 통계를 KeywordStatVO 객체로 변환
        positive_keyword_stats = [
            KeywordStatVO(
                keyword=kw_data['keyword'],
                count=kw_data['count'],
                related_articles=kw_data['related_articles']
            ) for kw_data in positive_keywords.values()
        ]
        
        negative_keyword_stats = [
            KeywordStatVO(
                keyword=kw_data['keyword'],
                count=kw_data['count'],
                related_articles=kw_data['related_articles']
            ) for kw_data in negative_keywords.values()
        ]
        
        # 비율 계산
        positive_rate = (positive_count / total_articles * 100) if total_articles > 0 else 0.0
        negative_rate = (negative_count / total_articles * 100) if total_articles > 0 else 0.0
        
        # 기본 통계 데이터
        stats_data = {
            'orgId': orgId,
            'positive_keywords': positive_keyword_stats,
            'negative_keywords': negative_keyword_stats,
            'articles_no': total_articles,
            'positive_rate': positive_rate,
            'negative_rate': negative_rate,
            'last_calculate_date': end_date
        }
        
        # 기간별 세부 데이터 추가
        if period == 'week':
            # 주별 통계에 일별 세부 데이터 추가
            stats_data['daily_breakdown'] = self._calculate_daily_breakdown(contents_list, orgId)
        elif period == 'month':
            # 월별 통계에 주별 세부 데이터 추가
            stats_data['weekly_breakdown'] = self._calculate_weekly_breakdown(contents_list, orgId)
        
        return stats_data

    def _calculate_daily_breakdown(self, contents_list: List[ContentsVO], orgId: str) -> Dict[str, Dict]:
        """주별 통계용 일별 세부 데이터 계산"""
        daily_data = {}
        
        for contents in contents_list:
            if not contents.pubDt:
                continue
                
            # 날짜 키 생성 (YYYY-MM-DD 형식)
            date_key = contents.pubDt.strftime('%Y-%m-%d')
            
            if date_key not in daily_data:
                daily_data[date_key] = {
                    'articles_no': 0,
                    'positive_count': 0,
                    'negative_count': 0,
                    'positive_rate': 0.0,
                    'negative_rate': 0.0
                }
            
            daily_data[date_key]['articles_no'] += 1
            
            # 감정 분석 결과 처리
            if contents.contentsMeta and contents.contentsMeta.sentiments:
                for sentiment in contents.contentsMeta.sentiments:
                    if sentiment.orgId == orgId:
                        if sentiment.positiveRatio and sentiment.positiveRatio > 0.5:
                            daily_data[date_key]['positive_count'] += 1
                        elif sentiment.negativeRatio and sentiment.negativeRatio > 0.5:
                            daily_data[date_key]['negative_count'] += 1
                        break
        
        # 비율 계산
        for date_key, data in daily_data.items():
            if data['articles_no'] > 0:
                data['positive_rate'] = (data['positive_count'] / data['articles_no']) * 100
                data['negative_rate'] = (data['negative_count'] / data['articles_no']) * 100
        
        return daily_data

    def _calculate_weekly_breakdown(self, contents_list: List[ContentsVO], orgId: str) -> Dict[str, Dict]:
        """월별 통계용 주별 세부 데이터 계산"""
        weekly_data = {}
        
        for contents in contents_list:
            if not contents.pubDt:
                continue
                
            # 주차 키 생성 (YYYY-W## 형식)
            year, week, _ = contents.pubDt.isocalendar()
            week_key = f"{year}-W{week:02d}"
            
            if week_key not in weekly_data:
                weekly_data[week_key] = {
                    'articles_no': 0,
                    'positive_count': 0,
                    'negative_count': 0,
                    'positive_rate': 0.0,
                    'negative_rate': 0.0
                }
            
            weekly_data[week_key]['articles_no'] += 1
            
            # 감정 분석 결과 처리
            if contents.contentsMeta and contents.contentsMeta.sentiments:
                for sentiment in contents.contentsMeta.sentiments:
                    if sentiment.orgId == orgId:
                        if sentiment.positiveRatio and sentiment.positiveRatio > 0.5:
                            weekly_data[week_key]['positive_count'] += 1
                        elif sentiment.negativeRatio and sentiment.negativeRatio > 0.5:
                            weekly_data[week_key]['negative_count'] += 1
                        break
        
        # 비율 계산
        for week_key, data in weekly_data.items():
            if data['articles_no'] > 0:
                data['positive_rate'] = (data['positive_count'] / data['articles_no']) * 100
                data['negative_rate'] = (data['negative_count'] / data['articles_no']) * 100
        
        return weekly_data

    def get_stats_summary(self, orgId: str, period: str, start_date: datetime = None, end_date: datetime = None) -> Dict:
        """통계 요약 정보 반환 (Java Controller에서 사용할 형태)"""
        stats = self.get_for_period(orgId, period, start_date, end_date)
        
        if not stats:
            return {
                'averagePositiveRatio': 0.0,
                'averageNegativeRatio': 0.0,
                'totalContentsCounts': 0,
                'positiveKeywords': [],
                'negativeKeywords': []
            }
        
        result = {
            'averagePositiveRatio': stats.positive_rate,
            'averageNegativeRatio': stats.negative_rate,
            'totalContentsCounts': stats.articles_no,
            'positiveKeywords': [
                {
                    'keyword': kw.keyword,
                    'count': kw.count,
                    'related_articles': kw.related_articles
                } for kw in stats.positive_keywords
            ],
            'negativeKeywords': [
                {
                    'keyword': kw.keyword,
                    'count': kw.count,
                    'related_articles': kw.related_articles
                } for kw in stats.negative_keywords
            ],
            'last_calculate_date': stats.last_calculate_date
        }
        
        # 기간별 세부 데이터 추가
        if hasattr(stats, 'daily_breakdown') and stats.daily_breakdown:
            result['daily_breakdown'] = stats.daily_breakdown
        if hasattr(stats, 'weekly_breakdown') and stats.weekly_breakdown:
            result['weekly_breakdown'] = stats.weekly_breakdown
        
        return result
