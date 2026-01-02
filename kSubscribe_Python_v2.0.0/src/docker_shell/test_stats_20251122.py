"""
간단한 테스트 스크립트: 2025-11-22 일별 통계 계산 및 daily_stats 저장
"""

from datetime import datetime
import pytz
from ksubscribe_share.db.service.statsService import StatsService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.logger import Logger

if __name__ == "__main__":
    logger = Logger().setup_logger(Logger.docker_scraping_result_logger_name)
    
    seoul_tz = pytz.timezone('Asia/Seoul')
    day_start = datetime(2025, 11, 22, 0, 0, 0, tzinfo=seoul_tz)
    day_end = datetime(2025, 11, 22, 23, 59, 59, 999999, tzinfo=seoul_tz)
    
    logger.info("=" * 80)
    logger.info("2025-11-22 일별 통계 계산 시작")
    logger.info("=" * 80)
    
    stats_service = StatsService()
    contents_org_service = ContentsOrgService()
    orgs = contents_org_service.find_all()
    
    logger.info(f"총 {len(orgs)}개 기관 처리 예정")
    
    success_count = 0
    error_count = 0
    
    for org in orgs:
        try:
            stats = stats_service.count_for_period(org.orgId, 'day', day_start, day_end)
            logger.info(f"✅ {org.orgId}: {stats._id} (기사 {stats.totalContentsCounts}개)")
            success_count += 1
        except Exception as e:
            logger.error(f"❌ {org.orgId}: {str(e)}")
            error_count += 1
    
    logger.info("=" * 80)
    logger.info(f"완료: 성공 {success_count}개, 실패 {error_count}개")
    logger.info("=" * 80)

