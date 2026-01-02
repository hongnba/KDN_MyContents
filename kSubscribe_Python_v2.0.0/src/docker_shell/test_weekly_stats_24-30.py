"""
2025-12-24 ~ 2025-12-30 주별 통계 계산 및 weekly_stats 저장
daily_stats를 집계하여 weekly_stats 생성
"""

from datetime import datetime
import pytz
from ksubscribe_share.db.service.statsService import StatsService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.logger import Logger

if __name__ == "__main__":
    logger = Logger().setup_logger(Logger.docker_scraping_result_logger_name)
    
    seoul_tz = pytz.timezone('Asia/Seoul')
    
    # 주별 통계 기간 설정 (2025-12-24 ~ 2025-12-30)
    # weekly_stats는 start_date부터 end_date까지의 daily_stats를 집계
    start_date = datetime(2025, 12, 24, 0, 0, 0, tzinfo=seoul_tz)
    end_date = datetime(2025, 12, 30, 23, 59, 59, 999999, tzinfo=seoul_tz)
    
    logger.info("=" * 80)
    logger.info(f"{start_date.date()} ~ {end_date.date()} 주별 통계 계산 시작")
    logger.info("daily_stats를 집계하여 weekly_stats 생성")
    logger.info("=" * 80)
    
    stats_service = StatsService()
    contents_org_service = ContentsOrgService()
    orgs = contents_org_service.find_all()
    
    logger.info(f"총 {len(orgs)}개 기관 처리 예정")
    
    success_count = 0
    error_count = 0
    
    # 각 기관별로 주별 통계 생성
    for org in orgs:
        try:
            # count_for_period를 'week'로 호출하면:
            # 1. 해당 기간의 daily_stats 조회
            # 2. daily_stats를 집계하여 weekly_stats 계산
            # 3. weekly_stats에 저장 (기존 데이터가 있으면 업데이트, 없으면 생성)
            stats = stats_service.count_for_period(org.orgId, 'week', start_date, end_date)
            logger.info(f"✅ {org.orgId}: {stats._id} (기사 {stats.totalContentsCounts}개)")
            success_count += 1
        except Exception as e:
            logger.error(f"❌ {org.orgId}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            error_count += 1
    
    logger.info("=" * 80)
    logger.info(f"완료: 성공 {success_count}개, 실패 {error_count}개")
    logger.info("=" * 80)
    logger.info("weekly_stats 생성 완료!")