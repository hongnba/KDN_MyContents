"""
2025-12-24 ~ 2025-12-30 일별 통계 계산 및 daily_stats 저장
각 날짜별로 순차적으로 처리하여 daily_stats가 제대로 쌓이도록 함
"""

from datetime import datetime, timedelta
import pytz
from ksubscribe_share.db.service.statsService import StatsService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.logger import Logger

if __name__ == "__main__":
    logger = Logger().setup_logger(Logger.docker_scraping_result_logger_name)
    
    seoul_tz = pytz.timezone('Asia/Seoul')
    
    # 시작 날짜와 종료 날짜 설정
    start_date = datetime(2025, 12, 24, 0, 0, 0, tzinfo=seoul_tz)
    end_date = datetime(2025, 12, 30, 23, 59, 59, 999999, tzinfo=seoul_tz)
    
    logger.info("=" * 80)
    logger.info(f"{start_date.date()} ~ {end_date.date()} 일별 통계 계산 시작")
    logger.info("각 날짜별로 순차적으로 처리하여 daily_stats 생성")
    logger.info("=" * 80)
    
    stats_service = StatsService()
    contents_org_service = ContentsOrgService()
    orgs = contents_org_service.find_all()
    
    logger.info(f"총 {len(orgs)}개 기관 처리 예정")
    
    # 각 날짜별로 처리
    current_date = start_date
    total_success = 0
    total_error = 0
    
    while current_date <= end_date:
        # 각 날짜의 시작과 끝 시간 설정
        day_start = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = current_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        logger.info("-" * 80)
        logger.info(f"📅 {day_start.date()} 일별 통계 계산 시작")
        logger.info(f"   기간: {day_start} ~ {day_end}")
        logger.info("-" * 80)
        
        day_success = 0
        day_error = 0
        
        # 각 기관별로 해당 날짜의 daily_stats 생성
        for org in orgs:
            try:
                # count_for_period를 호출하면:
                # 1. 해당 날짜의 contents 조회
                # 2. 통계 계산
                # 3. daily_stats에 저장 (기존 데이터가 있으면 업데이트, 없으면 생성)
                stats = stats_service.count_for_period(org.orgId, 'day', day_start, day_end)
                logger.info(f"✅ {org.orgId}: {stats._id} (기사 {stats.totalContentsCounts}개)")
                day_success += 1
                total_success += 1
            except Exception as e:
                logger.error(f"❌ {org.orgId}: {str(e)}")
                day_error += 1
                total_error += 1
        
        logger.info(f"📅 {day_start.date()} 완료: 성공 {day_success}개, 실패 {day_error}개")
        
        # 다음 날로 이동
        current_date += timedelta(days=1)
    
    logger.info("=" * 80)
    logger.info(f"전체 완료: 총 성공 {total_success}개, 총 실패 {total_error}개")
    logger.info("=" * 80)
    logger.info("이제 weekly_stats를 다시 계산하면 정확한 값이 나올 것입니다.")