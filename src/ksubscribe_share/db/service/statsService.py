from bson import ObjectId
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
from pymongo import DESCENDING
import pytz
import requests
import json

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
        
        # 향상된 통계 계산 (새로운 스키마 지원)
        stats_data = self._calculate_enhanced_stats(orgId, contents_data, start_date, end_date, period)
        
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
        """컨텐츠 리스트로부터 통계 계산 - Java Controller 로직과 일치"""
        total_articles = len(contents_list)
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        
        for contents in contents_list:
            if not contents.contentsMeta or not contents.contentsMeta.sentiments:
                continue
            
            # 감정 분석 결과 처리
            for sentiment in contents.contentsMeta.sentiments:
                if sentiment.orgId == orgId:
                    # 긍정/부정/중립 비율 계산 (Java Controller와 동일한 로직)
                    if sentiment.positiveRatio and sentiment.positiveRatio > 0.5:
                        positive_count += 1
                    elif sentiment.negativeRatio and sentiment.negativeRatio > 0.5:
                        negative_count += 1
                    else:
                        neutral_count += 1
                    break  # 해당 기관의 첫 번째 감정 분석 결과만 사용
        
        # 비율 계산
        positive_rate = (positive_count / total_articles * 100) if total_articles > 0 else 0.0
        negative_rate = (negative_count / total_articles * 100) if total_articles > 0 else 0.0
        neutral_rate = (neutral_count / total_articles * 100) if total_articles > 0 else 0.0
        
        # 기본 통계 데이터 (Java Controller와 일치)
        stats_data = {
            'orgId': orgId,
            'articles_no': total_articles,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count,
            'positive_rate': positive_rate,
            'negative_rate': negative_rate,
            'neutral_rate': neutral_rate,
            'last_calculate_date': end_date
        }
        
        return stats_data

    def _calculate_past_period_stats(self, orgId: str, period: str, start_date: datetime, end_date: datetime) -> Dict:
        """이전 기간의 통계 계산"""
        try:
            if period == 'day':
                # 일별: 어제의 DailyStatsVO 조회
                yesterday = start_date - timedelta(days=1)
                yesterday_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
                yesterday_end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                past_daily_stats = self.get_for_period(orgId, 'day', yesterday_start, yesterday_end)
                if past_daily_stats:
                    return {
                        'totalContentsCounts': past_daily_stats.totalContentsCounts,
                        'averagePositiveRatio': past_daily_stats.averagePositiveRatio
                    }
            
            elif period == 'week':
                # 주별: 이전 주의 일별 통계들을 집계
                week_duration = end_date - start_date
                past_week_start = start_date - week_duration
                past_week_end = start_date - timedelta(seconds=1)
                
                past_daily_stats_list = self._get_daily_stats_for_period(orgId, past_week_start, past_week_end)
                if past_daily_stats_list:
                    total_contents = sum(stats.totalContentsCounts for stats in past_daily_stats_list)
                    total_positive = sum(stats.totalPositiveContentsCount for stats in past_daily_stats_list)
                    avg_positive_ratio = (total_positive / total_contents * 100) if total_contents > 0 else 0.0
                    
                    return {
                        'totalContentsCounts': total_contents,
                        'averagePositiveRatio': avg_positive_ratio
                    }
            
            elif period == 'month':
                # 월별: 이전 월의 일별 통계들을 집계
                month_duration = end_date - start_date
                past_month_start = start_date - month_duration
                past_month_end = start_date - timedelta(seconds=1)
                
                past_daily_stats_list = self._get_daily_stats_for_period(orgId, past_month_start, past_month_end)
                if past_daily_stats_list:
                    total_contents = sum(stats.totalContentsCounts for stats in past_daily_stats_list)
                    total_positive = sum(stats.totalPositiveContentsCount for stats in past_daily_stats_list)
                    avg_positive_ratio = (total_positive / total_contents * 100) if total_contents > 0 else 0.0
                    
                    return {
                        'totalContentsCounts': total_contents,
                        'averagePositiveRatio': avg_positive_ratio
                    }
        
        except Exception as e:
            print(f"Error calculating past period stats: {str(e)}")
        
        # 기본값 반환 (이전 기간 데이터가 없는 경우)
        return {
            'totalContentsCounts': 0,
            'averagePositiveRatio': 0.0
        }

    def get_stats_summary(self, orgId: str, period: str, start_date: datetime = None, end_date: datetime = None) -> Dict:
        """통계 요약 정보 반환 (Java Controller에서 사용할 형태) - Legacy method"""
        # This method is kept for backward compatibility but should use get_enhanced_stats_summary instead
        return self.get_enhanced_stats_summary(orgId, period, start_date, end_date)

    def _generate_sentiment_sorted_maps(self, contents_list: List[ContentsVO], orgId: str, limit: int = 5) -> Dict:
        """감정별 정렬된 기사 맵 생성 - Schema에 맞는 구조"""
        positive_articles = []
        negative_articles = []
        
        for contents in contents_list:
            if not contents.contentsMeta or not contents.contentsMeta.sentiments:
                continue
                
                for sentiment in contents.contentsMeta.sentiments:
                    if sentiment.orgId == orgId:
                    # 긍정 기사 (positiveRatio > 0.5)
                        if sentiment.positiveRatio and sentiment.positiveRatio > 0.5:
                            positive_articles.append({
                                'id': str(contents._id),
                                'value': {
                                    'title': contents.title if hasattr(contents, 'title') else '',
                                    'sentiment': sentiment.positiveRatio,
                                    'short_summary': contents.contentsMeta.shortSummary if contents.contentsMeta.shortSummary else ''
                                }
                            })
                    # 부정 기사 (negativeRatio > 0.5)
                        elif sentiment.negativeRatio and sentiment.negativeRatio > 0.5:
                            negative_articles.append({
                                'id': str(contents._id),
                                'value': {
                                    'title': contents.title if hasattr(contents, 'title') else '',
                                    'sentiment': sentiment.negativeRatio,
                                    'short_summary': contents.contentsMeta.shortSummary if contents.contentsMeta.shortSummary else ''
                                }
                            })
        
        # 감정 점수 기준으로 정렬 (높은 순)
        positive_articles.sort(key=lambda x: x['value']['sentiment'], reverse=True)
        negative_articles.sort(key=lambda x: x['value']['sentiment'], reverse=True)
        
        # 상위 N개만 선택
        positive_articles = positive_articles[:limit]
        negative_articles = negative_articles[:limit]
        
        return {
            'positiveSortedMap': positive_articles,
            'negativeSortedMap': negative_articles
        }

    def _generate_keyword_maps(self, contents_list: List[ContentsVO], orgId: str) -> Dict:
        """워드 클라우드용 키워드 맵 생성"""
        positive_keyword_map = {}
        negative_keyword_map = {}
        
        for contents in contents_list:
            if not contents.contentsMeta or not contents.contentsMeta.sentiments:
                continue
                
            for sentiment in contents.contentsMeta.sentiments:
                if sentiment.orgId == orgId:
                    # 긍정 키워드 처리
                    if sentiment.positiveKeywords:
                        for keyword in sentiment.positiveKeywords:
                            positive_keyword_map[keyword] = positive_keyword_map.get(keyword, 0) + 1
                    
                    # 부정 키워드 처리
                    if sentiment.negativeKeywords:
                        for keyword in sentiment.negativeKeywords:
                            negative_keyword_map[keyword] = negative_keyword_map.get(keyword, 0) + 1
        
        return {
            'positiveKeywordMap': positive_keyword_map,
            'negativeKeywordMap': negative_keyword_map
        }



    def _call_ollama_for_analysis(self, stats_data: Dict) -> str:
        """Ollama를 호출하여 평판 분석 리포트 생성"""
        try:
            # Ollama API 설정
            # ollama_url = "http://10.99.2.71:11434/api/generate"
            import ksubscribe_share.config as CONF
            ollama_url = f"{CONF.OLLAMA_URL}/api/generate"
            
            # 프롬프트 생성
            prompt = f"""
            다음은 기관 평판 분석 데이터입니다. 이 데이터를 바탕으로 종합적인 평판 분석 리포트를 작성해주세요.
            
            기관 ID: {stats_data.get('orgId', 'N/A')}
            분석 기간: {stats_data.get('start_date', 'N/A')} ~ {stats_data.get('end_date', 'N/A')}
            총 기사 수: {stats_data.get('totalContentsCounts', 0)}
            긍정 비율: {stats_data.get('averagePositiveRatio', 0.0):.2f}%
            부정 비율: {stats_data.get('averageNegativeRatio', 0.0):.2f}%
            중립 비율: {stats_data.get('averageNeutralRatio', 0.0):.2f}%
            
            긍정 키워드: {', '.join(stats_data.get('totalPositiveKeywordList', []))}
            부정 키워드: {', '.join(stats_data.get('totalNegativeKeywordList', []))}
            
            위 데이터를 바탕으로 기관의 평판 현황과 개선 방안을 제시하는 종합 분석 리포트를 작성해주세요.
            """
            
            # Ollama API 요청
            payload = {
                "model": "llama-3-Korean-Bllossom-8B-Q4_K_M",
                "prompt": prompt,
                "stream": False,
                "num_predict": 200
            }
            
            response = requests.post(ollama_url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', 'Ollama 분석을 완료할 수 없습니다.')
            else:
                return f"Ollama API 오류: {response.status_code}"
                
        except Exception as e:
            return f"Ollama 분석 중 오류 발생: {str(e)}"

    def _calculate_enhanced_stats(self, orgId: str, contents_list: List[ContentsVO], start_date: datetime, end_date: datetime, period: str) -> Dict:
        """향상된 통계 계산 - 새로운 스키마 지원"""
        
        if period == 'day':
            # 일별 통계는 직접 계산
            return self._calculate_daily_enhanced_stats(orgId, contents_list, start_date, end_date)
        elif period == 'week':
            # 주별 통계는 일별 통계를 집계
            return self._aggregate_weekly_stats_from_daily(orgId, start_date, end_date)
        elif period == 'month':
            # 월별 통계는 일별 통계를 집계
            return self._aggregate_monthly_stats_from_daily(orgId, start_date, end_date)
        else:
            raise ValueError(f"Invalid period: {period}")

    def _calculate_daily_enhanced_stats(self, orgId: str, contents_list: List[ContentsVO], start_date: datetime, end_date: datetime) -> Dict:
        """일별 향상된 통계 계산"""
        # 기본 통계 계산
        basic_stats = self._calculate_stats(orgId, contents_list, start_date, end_date, 'day')
        
        # 20251212 유헌수 변경
        # 새로운 스키마 필드들 추가
        # enhanced_stats = basic_stats.copy()
        # 새로운 스키마 필드들 추가 (basic_stats의 불필요한 키 제거)
        enhanced_stats = {
            'orgId': basic_stats['orgId'],
            'last_calculate_date': basic_stats['last_calculate_date']
        }
        
        # 20251212 유헌수 변경
        # Query period and keyword lists
        # enhanced_stats['startDate'] = start_date
        # enhanced_stats['endDate'] = end_date
        enhanced_stats['start_date'] = start_date
        enhanced_stats['end_date'] = end_date
        
        # Content counts and ratios (use actual counts from basic_stats)
        enhanced_stats['totalContentsCounts'] = basic_stats['articles_no']
        enhanced_stats['averagePositiveRatio'] = basic_stats['positive_rate']
        enhanced_stats['averageNegativeRatio'] = basic_stats['negative_rate']
        enhanced_stats['averageNeutralRatio'] = basic_stats['neutral_rate']
        enhanced_stats['totalPositiveContentsCount'] = basic_stats['positive_count']
        enhanced_stats['totalNegativeContentsCount'] = basic_stats['negative_count']
        enhanced_stats['totalNeutralContentsCount'] = basic_stats['neutral_count']
        
        # 20251212 유헌수 변경
        # Calculate past period data
        # past_stats = self._calculate_past_period_stats(orgId, period, start_date, end_date)
        past_stats = self._calculate_past_period_stats(orgId, 'day', start_date, end_date)
        enhanced_stats['pastTotalContentsCounts'] = past_stats['totalContentsCounts']
        enhanced_stats['pastAveragePositiveRatio'] = past_stats['averagePositiveRatio']
        
        # Sentiment sorted maps
        sentiment_maps = self._generate_sentiment_sorted_maps(contents_list, orgId)
        enhanced_stats['positiveSortedMap'] = sentiment_maps['positiveSortedMap']
        enhanced_stats['negativeSortedMap'] = sentiment_maps['negativeSortedMap']
        
        # Keyword maps
        keyword_maps = self._generate_keyword_maps(contents_list, orgId)
        enhanced_stats['positiveKeywordMap'] = keyword_maps['positiveKeywordMap']
        enhanced_stats['negativeKeywordMap'] = keyword_maps['negativeKeywordMap']
        
        # Keyword lists
        enhanced_stats['totalPositiveKeywordList'] = list(keyword_maps['positiveKeywordMap'].keys())
        enhanced_stats['totalNegativeKeywordList'] = list(keyword_maps['negativeKeywordMap'].keys())
        
        # Calendar results (현재 월의 일별 데이터) - CalendarService에서 별도 처리
        enhanced_stats['positiveResult'] = {}
        enhanced_stats['negativeResult'] = {}
        enhanced_stats['neutralResult'] = {}
        
        # Ollama 분석 리포트 생성
        try:
            ollama_report = self._call_ollama_for_analysis(enhanced_stats)
            enhanced_stats['ollamaReputationChangeReason'] = ollama_report
        except Exception as e:
            enhanced_stats['ollamaReputationChangeReason'] = f"Ollama 분석 실패: {str(e)}"
        
        return enhanced_stats

    def _aggregate_weekly_stats_from_daily(self, orgId: str, start_date: datetime, end_date: datetime) -> Dict:
        """일별 통계를 집계하여 주별 통계 생성"""
        # 해당 주의 일별 통계 조회
        daily_stats_list = self._get_daily_stats_for_period(orgId, start_date, end_date)
        
        if not daily_stats_list:
            return self._get_empty_enhanced_stats(orgId, start_date, end_date)
        
        # 집계 계산
        total_contents = sum(stats.totalContentsCounts for stats in daily_stats_list)
        total_positive = sum(stats.totalPositiveContentsCount for stats in daily_stats_list)
        total_negative = sum(stats.totalNegativeContentsCount for stats in daily_stats_list)
        total_neutral = sum(stats.totalNeutralContentsCount for stats in daily_stats_list)
        
        # 비율 계산
        avg_positive_ratio = (total_positive / total_contents * 100) if total_contents > 0 else 0.0
        avg_negative_ratio = (total_negative / total_contents * 100) if total_contents > 0 else 0.0
        avg_neutral_ratio = (total_neutral / total_contents * 100) if total_contents > 0 else 0.0
        
        # 키워드 맵 집계
        positive_keyword_map = {}
        negative_keyword_map = {}
        positive_sorted_map = []
        negative_sorted_map = []
        
        for stats in daily_stats_list:
            # 키워드 맵 집계
            if stats.positiveKeywordMap:
                for keyword, count in stats.positiveKeywordMap.items():
                    positive_keyword_map[keyword] = positive_keyword_map.get(keyword, 0) + count
            
            if stats.negativeKeywordMap:
                for keyword, count in stats.negativeKeywordMap.items():
                    negative_keyword_map[keyword] = negative_keyword_map.get(keyword, 0) + count
            
            # 정렬된 맵 집계 (상위 기사들)
            if stats.positiveSortedMap:
                positive_sorted_map.extend(stats.positiveSortedMap)
            if stats.negativeSortedMap:
                negative_sorted_map.extend(stats.negativeSortedMap)
        
        # 정렬된 맵에서 상위 5개만 선택 (새로운 스키마 구조)
        positive_sorted_map.sort(key=lambda x: x.get('value', {}).get('sentiment', 0), reverse=True)
        negative_sorted_map.sort(key=lambda x: x.get('value', {}).get('sentiment', 0), reverse=True)
        positive_sorted_map = positive_sorted_map[:5]
        negative_sorted_map = negative_sorted_map[:5]
        
        # 키워드 리스트 생성
        positive_keyword_list = sorted(positive_keyword_map.keys(), key=lambda k: positive_keyword_map[k], reverse=True)
        negative_keyword_list = sorted(negative_keyword_map.keys(), key=lambda k: negative_keyword_map[k], reverse=True)
        
        # 20251212 유헌수 변경
        # Ollama 분석 리포트 생성
        stats_data = {
            'orgId': orgId,
            # 'startDate': start_date,
            # 'endDate': end_date,
            'start_date': start_date,
            'end_date': end_date,
            'totalContentsCounts': total_contents,
            'averagePositiveRatio': avg_positive_ratio,
            'averageNegativeRatio': avg_negative_ratio,
            'averageNeutralRatio': avg_neutral_ratio,
            'totalPositiveKeywordList': positive_keyword_list,
            'totalNegativeKeywordList': negative_keyword_list
        }
        
        try:
            ollama_report = self._call_ollama_for_analysis(stats_data)
        except Exception as e:
            ollama_report = f"Ollama 분석 실패: {str(e)}"
        
        # Calculate past period data for weekly stats
        past_stats = self._calculate_past_period_stats(orgId, 'week', start_date, end_date)
        
        # 20251212 유헌수 변경
        return {
            'orgId': orgId,
            # 'startDate': start_date,
            # 'endDate': end_date,
            'start_date': start_date,
            'end_date': end_date,
            'totalContentsCounts': total_contents,
            'pastTotalContentsCounts': past_stats['totalContentsCounts'],
            'averagePositiveRatio': avg_positive_ratio,
            'averageNegativeRatio': avg_negative_ratio,
            'averageNeutralRatio': avg_neutral_ratio,
            'pastAveragePositiveRatio': past_stats['averagePositiveRatio'],
            'totalPositiveContentsCount': total_positive,
            'totalNegativeContentsCount': total_negative,
            'totalNeutralContentsCount': total_neutral,
            'totalPositiveKeywordList': positive_keyword_list,
            'totalNegativeKeywordList': negative_keyword_list,
            'positiveSortedMap': positive_sorted_map,
            'negativeSortedMap': negative_sorted_map,
            'positiveKeywordMap': positive_keyword_map,
            'negativeKeywordMap': negative_keyword_map,
            'ollamaReputationChangeReason': ollama_report,
            'positiveResult': {},  # 주별에서는 일별 캘린더 데이터 사용 안함
            'negativeResult': {},
            'neutralResult': {},
            'last_calculate_date': end_date
        }

    def _aggregate_monthly_stats_from_daily(self, orgId: str, start_date: datetime, end_date: datetime) -> Dict:
        """일별 통계를 집계하여 월별 통계 생성"""
        # 해당 월의 일별 통계 조회
        daily_stats_list = self._get_daily_stats_for_period(orgId, start_date, end_date)
        
        if not daily_stats_list:
            return self._get_empty_enhanced_stats(orgId, start_date, end_date)
        
        # 집계 계산
        total_contents = sum(stats.totalContentsCounts for stats in daily_stats_list)
        total_positive = sum(stats.totalPositiveContentsCount for stats in daily_stats_list)
        total_negative = sum(stats.totalNegativeContentsCount for stats in daily_stats_list)
        total_neutral = sum(stats.totalNeutralContentsCount for stats in daily_stats_list)
        
        # 비율 계산
        avg_positive_ratio = (total_positive / total_contents * 100) if total_contents > 0 else 0.0
        avg_negative_ratio = (total_negative / total_contents * 100) if total_contents > 0 else 0.0
        avg_neutral_ratio = (total_neutral / total_contents * 100) if total_contents > 0 else 0.0
        
        # 키워드 맵 집계
        positive_keyword_map = {}
        negative_keyword_map = {}
        positive_sorted_map = []
        negative_sorted_map = []
        
        for stats in daily_stats_list:
            # 키워드 맵 집계
            if stats.positiveKeywordMap:
                for keyword, count in stats.positiveKeywordMap.items():
                    positive_keyword_map[keyword] = positive_keyword_map.get(keyword, 0) + count
            
            if stats.negativeKeywordMap:
                for keyword, count in stats.negativeKeywordMap.items():
                    negative_keyword_map[keyword] = negative_keyword_map.get(keyword, 0) + count
            
            # 정렬된 맵 집계 (상위 기사들)
            if stats.positiveSortedMap:
                positive_sorted_map.extend(stats.positiveSortedMap)
            if stats.negativeSortedMap:
                negative_sorted_map.extend(stats.negativeSortedMap)
        
        # 정렬된 맵에서 상위 5개만 선택 (새로운 스키마 구조)
        positive_sorted_map.sort(key=lambda x: x.get('value', {}).get('sentiment', 0), reverse=True)
        negative_sorted_map.sort(key=lambda x: x.get('value', {}).get('sentiment', 0), reverse=True)
        positive_sorted_map = positive_sorted_map[:5]
        negative_sorted_map = negative_sorted_map[:5]
        
        # 키워드 리스트 생성
        positive_keyword_list = sorted(positive_keyword_map.keys(), key=lambda k: positive_keyword_map[k], reverse=True)
        negative_keyword_list = sorted(negative_keyword_map.keys(), key=lambda k: negative_keyword_map[k], reverse=True)
        
        # 20251212 유헌수 변경
        # Ollama 분석 리포트 생성
        stats_data = {
            'orgId': orgId,
            # 'startDate': start_date,
            # 'endDate': end_date,
            'start_date': start_date,
            'end_date': end_date,
            'totalContentsCounts': total_contents,
            'averagePositiveRatio': avg_positive_ratio,
            'averageNegativeRatio': avg_negative_ratio,
            'averageNeutralRatio': avg_neutral_ratio,
            'totalPositiveKeywordList': positive_keyword_list,
            'totalNegativeKeywordList': negative_keyword_list
        }
        
        try:
            ollama_report = self._call_ollama_for_analysis(stats_data)
        except Exception as e:
            ollama_report = f"Ollama 분석 실패: {str(e)}"
        
        # Calculate past period data for monthly stats
        past_stats = self._calculate_past_period_stats(orgId, 'month', start_date, end_date)
        
        # 20251212 유헌수 변경
        return {
            'orgId': orgId,
            # 'startDate': start_date,
            # 'endDate': end_date,
            'start_date': start_date,
            'end_date': end_date,
            'totalContentsCounts': total_contents,
            'pastTotalContentsCounts': past_stats['totalContentsCounts'],
            'averagePositiveRatio': avg_positive_ratio,
            'averageNegativeRatio': avg_negative_ratio,
            'averageNeutralRatio': avg_neutral_ratio,
            'pastAveragePositiveRatio': past_stats['averagePositiveRatio'],
            'totalPositiveContentsCount': total_positive,
            'totalNegativeContentsCount': total_negative,
            'totalNeutralContentsCount': total_neutral,
            'totalPositiveKeywordList': positive_keyword_list,
            'totalNegativeKeywordList': negative_keyword_list,
            'positiveSortedMap': positive_sorted_map,
            'negativeSortedMap': negative_sorted_map,
            'positiveKeywordMap': positive_keyword_map,
            'negativeKeywordMap': negative_keyword_map,
            'ollamaReputationChangeReason': ollama_report,
            'positiveResult': {},  # 월별에서는 일별 캘린더 데이터 사용 안함
            'negativeResult': {},
            'neutralResult': {},
            'last_calculate_date': end_date
        }

    def _get_daily_stats_for_period(self, orgId: str, start_date: datetime, end_date: datetime) -> List[DailyStatsVO]:
        """지정된 기간의 일별 통계 조회"""
        collection = self.mongoManager.getCollection("daily_stats")
        
        query = {
            "orgId": orgId,
            "last_calculate_date": {
                "$gte": start_date,
                "$lte": end_date
            }
        }
        
        cursor = collection.find(query).sort("last_calculate_date", 1)
        daily_stats_list = []
        
        for doc in cursor:
            daily_stats = DailyStatsVO.from_mongo(doc)
            daily_stats_list.append(daily_stats)
        
        return daily_stats_list

    def _get_empty_enhanced_stats(self, orgId: str, start_date: datetime, end_date: datetime) -> Dict:
        """빈 향상된 통계 데이터 반환"""
        # 20251212 유헌수 변경
        return {
            'orgId': orgId,
            # 'startDate': start_date,
            # 'endDate': end_date,
            'start_date': start_date,
            'end_date': end_date,
            'totalContentsCounts': 0,
            'pastTotalContentsCounts': 0,
            'averagePositiveRatio': 0.0,
            'averageNegativeRatio': 0.0,
            'averageNeutralRatio': 0.0,
            'pastAveragePositiveRatio': 0.0,
            'totalPositiveContentsCount': 0,
            'totalNegativeContentsCount': 0,
            'totalNeutralContentsCount': 0,
            'totalPositiveKeywordList': [],
            'totalNegativeKeywordList': [],
            'positiveSortedMap': [],
            'negativeSortedMap': [],
            'positiveKeywordMap': {},
            'negativeKeywordMap': {},
            'ollamaReputationChangeReason': '',
            'positiveResult': {},
            'negativeResult': {},
            'neutralResult': {},
            'last_calculate_date': end_date
        }

    def get_enhanced_stats_summary(self, orgId: str, period: str, start_date: datetime = None, end_date: datetime = None) -> Dict:
        """향상된 통계 요약 정보 반환 (Java Controller에서 사용할 형태)"""
        stats = self.get_for_period(orgId, period, start_date, end_date)
        
        # 20251212 유헌수 변경
        if not stats:
            return {
                'orgId': orgId,
                # 'startDate': start_date,
                # 'endDate': end_date,
                'start_date': start_date,
                'end_date': end_date,
                'totalContentsCounts': 0,
                'pastTotalContentsCounts': 0,
                'averagePositiveRatio': 0.0,
                'averageNegativeRatio': 0.0,
                'averageNeutralRatio': 0.0,
                'pastAveragePositiveRatio': 0.0,
                'totalPositiveContentsCount': 0,
                'totalNegativeContentsCount': 0,
                'totalNeutralContentsCount': 0,
                'totalPositiveKeywordList': [],
                'totalNegativeKeywordList': [],
                'positiveSortedMap': [],
                'negativeSortedMap': [],
                'positiveKeywordMap': {},
                'negativeKeywordMap': {},
                'ollamaReputationChangeReason': '',
                'positiveResult': {},
                'negativeResult': {},
                'neutralResult': {}
            }
        
        # 20251212 유헌수 변경
        result = {
            'orgId': stats.orgId,
            # 'startDate': stats.startDate,
            # 'endDate': stats.endDate,
            'start_date': stats.startDate,
            'end_date': stats.endDate,
            'totalContentsCounts': stats.totalContentsCounts,
            'pastTotalContentsCounts': stats.pastTotalContentsCounts,
            'averagePositiveRatio': stats.averagePositiveRatio,
            'averageNegativeRatio': stats.averageNegativeRatio,
            'averageNeutralRatio': stats.averageNeutralRatio,
            'pastAveragePositiveRatio': stats.pastAveragePositiveRatio,
            'totalPositiveContentsCount': stats.totalPositiveContentsCount,
            'totalNegativeContentsCount': stats.totalNegativeContentsCount,
            'totalNeutralContentsCount': stats.totalNeutralContentsCount,
            'totalPositiveKeywordList': stats.totalPositiveKeywordList,
            'totalNegativeKeywordList': stats.totalNegativeKeywordList,
            'positiveSortedMap': stats.positiveSortedMap,
            'negativeSortedMap': stats.negativeSortedMap,
            'positiveKeywordMap': stats.positiveKeywordMap,
            'negativeKeywordMap': stats.negativeKeywordMap,
            'ollamaReputationChangeReason': stats.ollamaReputationChangeReason,
            'positiveResult': stats.positiveResult,
            'negativeResult': stats.negativeResult,
            'neutralResult': stats.neutralResult
        }
        
        return result
