#!/usr/bin/env python3
"""
Stats Service 테스트 예제
기관 평판 통계 서비스 사용법을 보여주는 예제 파일
"""

from datetime import datetime
import pytz
from ksubscribe_share.db.service.statsService import StatsService
from ksubscribe_share.db.dbmodelV2.dailyStatsVO import DailyStatsVO
from ksubscribe_share.db.dbmodelV2.weeklyStatsVO import WeeklyStatsVO
from ksubscribe_share.db.dbmodelV2.monthlyStatsVO import MonthlyStatsVO

def test_stats_service():
    """StatsService 사용 예제"""
    
    # 서비스 인스턴스 생성
    stats_service = StatsService()
    
    # 테스트용 기관 ID
    org_id = "test_org_001"
    
    print("=== 기관 평판 통계 서비스 테스트 ===")
    
    # 1. 일별 통계 계산 및 저장
    print("\n1. 일별 통계 계산 중...")
    daily_stats = stats_service.count_for_period(org_id, 'day')
    print(f"일별 통계 생성 완료: {daily_stats.articles_no}개 기사, 긍정률 {daily_stats.positive_rate:.2f}%")
    
    # 2. 주별 통계 계산 및 저장
    print("\n2. 주별 통계 계산 중...")
    weekly_stats = stats_service.count_for_period(org_id, 'week')
    print(f"주별 통계 생성 완료: {weekly_stats.articles_no}개 기사, 긍정률 {weekly_stats.positive_rate:.2f}%")
    
    # 3. 월별 통계 계산 및 저장
    print("\n3. 월별 통계 계산 중...")
    monthly_stats = stats_service.count_for_period(org_id, 'month')
    print(f"월별 통계 생성 완료: {monthly_stats.articles_no}개 기사, 긍정률 {monthly_stats.positive_rate:.2f}%")
    
    # 4. 기존 통계 데이터 조회
    print("\n4. 기존 통계 데이터 조회...")
    existing_daily = stats_service.get_for_period(org_id, 'day')
    if existing_daily:
        print(f"기존 일별 통계: {existing_daily.articles_no}개 기사")
    else:
        print("기존 일별 통계 없음")
    
    # 5. 통계 요약 정보 조회 (Java Controller에서 사용할 형태)
    print("\n5. 통계 요약 정보 조회...")
    summary = stats_service.get_stats_summary(org_id, 'day')
    print(f"일별 요약 정보: {summary}")
    
    # 주별 요약 정보 (일별 세부 데이터 포함)
    weekly_summary = stats_service.get_stats_summary(org_id, 'week')
    print(f"주별 요약 정보 (일별 세부 데이터 포함): {weekly_summary}")
    
    # 월별 요약 정보 (주별 세부 데이터 포함)
    monthly_summary = stats_service.get_stats_summary(org_id, 'month')
    print(f"월별 요약 정보 (주별 세부 데이터 포함): {monthly_summary}")
    
    # 6. 특정 날짜 범위로 통계 조회
    print("\n6. 특정 날짜 범위로 통계 조회...")
    kst = pytz.timezone('Asia/Seoul')
    start_date = datetime(2024, 1, 1, tzinfo=kst)
    end_date = datetime(2024, 1, 31, tzinfo=kst)
    
    custom_stats = stats_service.get_for_period(org_id, 'month', start_date, end_date)
    if custom_stats:
        print(f"2024년 1월 통계: {custom_stats.articles_no}개 기사")
    else:
        print("2024년 1월 통계 없음")

def example_usage():
    """실제 사용 예제"""
    
    stats_service = StatsService()
    org_id = "your_org_id_here"
    
    # Java Controller에서 사용할 수 있는 형태로 데이터 조회
    def get_org_reputation_data(org_id, period):
        """기관 평판 데이터 조회 (Java Controller 호환)"""
        
        # 통계 계산 (필요시)
        stats_service.count_for_period(org_id, period)
        
        # 통계 요약 정보 반환
        summary = stats_service.get_stats_summary(org_id, period)
        
        return {
            'averagePositiveRatio': summary['averagePositiveRatio'],
            'averageNegativeRatio': summary['averageNegativeRatio'],
            'totalContentsCounts': summary['totalContentsCounts'],
            'positiveKeywords': summary['positiveKeywords'],
            'negativeKeywords': summary['negativeKeywords']
        }
    
    # 사용 예제
    reputation_data = get_org_reputation_data(org_id, 'day')
    print(f"기관 평판 데이터: {reputation_data}")

if __name__ == "__main__":
    # 테스트 실행
    test_stats_service()
    
    print("\n" + "="*50)
    print("실제 사용 예제:")
    example_usage()
