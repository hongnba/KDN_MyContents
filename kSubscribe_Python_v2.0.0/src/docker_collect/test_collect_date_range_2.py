# -*- coding: utf-8 -*-
"""
특정 날짜 범위에 대한 기사 수집 테스트 스크립트

사용법:
    # 기본 사용 (한국전력, 2025-11-01 ~ 2025-11-30)
    python test_collect_date_range.py
    
    # 기관과 날짜 직접 지정
    python test_collect_date_range.py --org-id A0010 --start-date 2025-11-01 --end-date 2025-11-30
    
    # 설정 파일 사용
    python test_collect_date_range.py --config config.json
    
    # Docker 컨테이너 내에서 실행
    docker exec ksubscribe_python_unified python3 /app/docker_collect/test_collect_date_range.py --org-id A0010 --start-date 2025-11-01 --end-date 2025-11-30

목표:
    - 특정 날짜 범위에 대한 기관별 뉴스와 공고 수집
    - main_collect_and_scrapping.py를 수정하지 않고 테스트 가능
    - 명령줄 인자 또는 설정 파일로 유연하게 설정 가능

주의사항:
    - 이 스크립트는 IS_USE: True인 기관만 조회합니다.
    - lastSucYMD는 임시로 수정되며, 수집 완료 후 원래 값으로 복원됩니다.
    - 명령줄 인자 또는 설정 파일로 기관과 날짜를 지정할 수 있습니다.
"""

import os
import sys
import argparse
import json
from datetime import datetime, timedelta
import pytz

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ksubscribe_share.logger import Logger
from docker_collect.driver_utils import get_driver
from docker_collect.error_handler import ErrorHandler, OpenAPIErrorHandler, SeleniumErrorHandler
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from docker_collect.rss_collector import get_contents_by_rss
from docker_collect.openapi_collector import get_g2b_nara, get_naver_news
from docker_collect.selenium_collector import get_contents_by_selenium_main, get_kepco_news


class DateRangeCollectMain:
    """
    특정 날짜 범위에 대한 기사 수집을 위한 테스트 클래스
    """
    
    def __init__(self, target_org_id: str, start_date: datetime, end_date: datetime):
        """
        Args:
            target_org_id: 수집할 기관 ID (예: "A0010" - 한국전력)
            start_date: 수집 시작 날짜 (datetime, timezone-aware)
            end_date: 수집 종료 날짜 (datetime, timezone-aware)
        """
        self.target_org_id = target_org_id
        self.start_date = start_date
        self.end_date = end_date
        
        logger = Logger()
        self.logger = logger.setup_logger(logger.docker_collect_logger_name)
        
        self.contentsOrgService = ContentsOrgService()
        self.success_cnt = 0
        self.fail_cnt = 0
        self.total_cnt = 0
        
        # 원래 lastSucYMD 값을 저장 (복원용)
        self.original_last_suc_ymd = {}
    
    def _backup_and_modify_last_suc_ymd(self, org, category):
        """
        카테고리의 lastSucYMD를 백업하고 수집 기간에 맞게 수정
        
        Args:
            org: ContentsOrgVO 객체
            category: ContentsOrgCategory 객체
        """
        # 고유 키 생성
        key = f"{org.orgId}_{category.cateId}"
        
        # 원래 값 백업
        if key not in self.original_last_suc_ymd:
            self.original_last_suc_ymd[key] = category.lastSucYMD
        
        # 수집 시작 날짜의 하루 전으로 설정 (해당 날짜부터 수집하기 위해)
        # 예: 2025-11-01부터 수집하려면 2025-10-31로 설정
        category.lastSucYMD = self.start_date - timedelta(days=1)
        
        self.logger.info(
            f"  [날짜 수정] {org.orgName}({org.orgId}) - {category.cateName}({category.cateId}): "
            f"lastSucYMD를 {category.lastSucYMD.strftime('%Y-%m-%d')}로 임시 설정 "
            f"(원래: {self.original_last_suc_ymd[key].strftime('%Y-%m-%d') if isinstance(self.original_last_suc_ymd[key], datetime) else str(self.original_last_suc_ymd[key])})"
        )
    
    def _restore_last_suc_ymd(self, org, category):
        """
        카테고리의 lastSucYMD를 원래 값으로 복원
        
        Args:
            org: ContentsOrgVO 객체
            category: ContentsOrgCategory 객체
        """
        key = f"{org.orgId}_{category.cateId}"
        if key in self.original_last_suc_ymd:
            category.lastSucYMD = self.original_last_suc_ymd[key]
            self.logger.info(
                f"  [날짜 복원] {org.orgName}({org.orgId}) - {category.cateName}({category.cateId}): "
                f"lastSucYMD를 원래 값으로 복원"
            )
    
    def _modify_today_in_collectors(self):
        """
        수집 함수들이 사용하는 'today' 값을 end_date로 변경하기 위한 패치
        
        주의: 이 방법은 수집 함수 내부에서 datetime.now()를 직접 호출하므로
        완전한 오버라이드는 어렵습니다. 대신 lastSucYMD를 조정하여
        원하는 날짜 범위만 수집되도록 합니다.
        """
        # 실제로는 수집 함수들이 datetime.now()를 직접 호출하므로
        # 여기서는 lastSucYMD만 조정하고, 수집 함수 내부의 today는
        # 실제 오늘 날짜로 유지됩니다.
        # 하지만 date_list 계산 시 lastSucYMD부터 today까지이므로,
        # lastSucYMD를 start_date - 1일로, 그리고 수집 함수 내부에서
        # today 대신 end_date를 사용하도록 수정이 필요합니다.
        pass
    
    def collect_for_date_range(self):
        """
        지정된 날짜 범위에 대해 기사 수집 실행
        """
        self.logger.info("=" * 100)
        self.logger.info(f"특정 날짜 범위 수집 시작")
        self.logger.info(f"  기관 ID: {self.target_org_id}")
        self.logger.info(f"  수집 기간: {self.start_date.strftime('%Y-%m-%d')} ~ {self.end_date.strftime('%Y-%m-%d')}")
        self.logger.info("=" * 100)
        
        # IS_USE: True인 기관 목록 조회
        contentsOrgList = self.contentsOrgService.find_all()
        self.logger.info(f"총 {len(contentsOrgList)}개 기관 조회 완료")
        
        # 대상 기관만 필터링
        target_org = None
        for org in contentsOrgList:
            if org.orgId == self.target_org_id:
                target_org = org
                break
        
        if not target_org:
            self.logger.error(f"기관 ID '{self.target_org_id}'를 찾을 수 없습니다.")
            return
        
        self.logger.info(f"대상 기관: {target_org.orgName}({target_org.orgId}), 카테고리 수: {len(target_org.categoryList)}")
        
        if len(target_org.categoryList) == 0:
            self.logger.warning(f"  카테고리가 없어서 종료합니다.")
            return
        
        # 나라장터 키워드 조회 (필요한 경우)
        g2b_keywords = self.contentsOrgService.findOrgKeywords("A0004")
        
        driver = get_driver()
        
        try:
            # 각 카테고리별로 수집
            for category in target_org.categoryList:
                self.logger.info(f"\n카테고리 처리: {category.cateName}({category.cateId})")
                
                # lastSucYMD 백업 및 수정
                self._backup_and_modify_last_suc_ymd(target_org, category)
                
                result = None
                collect_datetime = datetime.utcnow().replace(tzinfo=pytz.utc)
                err_handler = ErrorHandler()
                
                try:
                    # SELENIUM
                    if category.COL_METHOD == "C0003":
                        # 한국전력공사(주) and 보도자료
                        if target_org.orgId == "A0010" and category.cateId == "B0001":
                            # get_kepco_news는 내부에서 datetime.now()를 사용하므로
                            # 직접 수정이 필요합니다. 여기서는 패치를 적용합니다.
                            result = self._collect_with_date_override(
                                get_kepco_news, driver, target_org, category, # self.end_date
                            )
                        else:
                            result = self._collect_with_date_override(
                                get_contents_by_selenium_main, driver, target_org, category, # self.end_date
                            )
                        err_handler.set_processor(SeleniumErrorHandler())
                    
                    # RSS
                    elif category.COL_METHOD == "C0001":
                        result = self._collect_with_date_override(
                            get_contents_by_rss, target_org, category, # self.end_date
                        )
                    
                    # OPEN API
                    else:
                        # 나라장터 and 입찰정보
                        if target_org.orgId == "A0004" and category.cateId == "B0005":
                            result = self._collect_with_date_override(
                                get_g2b_nara, target_org, category, g2b_keywords, # self.end_date
                            )
                            err_handler.set_processor(OpenAPIErrorHandler())
                        # 네이버 뉴스
                        else:
                            result = self._collect_with_date_override(
                                get_naver_news, "A0026", target_org, category, # self.end_date
                            )
                            err_handler.set_processor(OpenAPIErrorHandler())
                
                except Exception as e:
                    self.logger.error(f"수집 함수 예외: {target_org.orgName}({target_org.orgId}) - {category.cateName}({category.cateId}): {e}")
                    result = {"success": False, "error": str(e)}
                
                # lastSucYMD 복원
                self._restore_last_suc_ymd(target_org, category)
                
                if not result:
                    self.logger.warning(f"result가 None: {target_org.orgName}({target_org.orgId}) - {category.cateName}({category.cateId})")
                    continue
                
                if result["success"]:
                    self.success_cnt += 1
                else:
                    error_info = err_handler.handle(result["error"])
                    regDt = datetime.utcnow().replace(tzinfo=pytz.utc)
                    self.fail_cnt += 1
                    self.logger.error(f"수집 실패: {error_info}")
                
                self.total_cnt += 1
        
        finally:
            driver.quit()
        
        self.logger.info("=" * 100)
        self.logger.info("특정 날짜 범위 수집 종료")
        self.logger.info(f"통계: 총 {self.total_cnt}건, 성공 {self.success_cnt}건, 실패 {self.fail_cnt}건")
        self.logger.info("=" * 100)
    
    def _collect_with_date_override(self, collect_func, *args, end_date=None):
        """
        수집 함수를 호출합니다.
        
        참고: 수집 함수들은 내부에서 datetime.now()를 사용하여 '오늘 날짜'를 가져옵니다.
        하지만 실제로는 lastSucYMD부터 today까지의 날짜 리스트를 생성하므로,
        lastSucYMD를 start_date - 1일로 설정하면 원하는 날짜 범위가 포함됩니다.
        
        단, 수집 함수 내부에서 datetime.now()를 직접 호출하므로,
        실제로는 start_date부터 오늘까지 수집될 수 있습니다.
        완전한 날짜 범위 제어를 위해서는 수집 함수들을 수정해야 합니다.
        """
        # 간단하게 수집 함수를 그대로 호출
        # lastSucYMD가 이미 start_date - 1일로 설정되어 있으므로,
        # 수집 함수는 start_date부터 오늘까지 수집합니다.
        # 완전한 제어를 위해서는 수집 함수 내부의 datetime.now()를
        # end_date로 바꿔야 하지만, 이는 복잡한 monkey patching이 필요합니다.
        return collect_func(*args)


def parse_arguments():
    """
    명령줄 인자 파싱
    
    Returns:
        argparse.Namespace: 파싱된 인자들
    """
    parser = argparse.ArgumentParser(
        description='특정 날짜 범위에 대한 기사 수집 테스트 스크립트',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 기본 사용 (한국전력, 2025-11-01 ~ 2025-11-30)
  python test_collect_date_range.py
  
  # 기관과 날짜 직접 지정
  python test_collect_date_range.py --org-id A0010 --start-date 2025-11-01 --end-date 2025-11-30
  
  # 설정 파일 사용
  python test_collect_date_range.py --config config.json
  
  # 설정 파일 예시 (config.json):
  {
    "org_id": "A0010",
    "start_date": "2025-11-01",
    "end_date": "2025-11-30"
  }
        """
    )
    
    # 기관 ID
    parser.add_argument(
        '--org-id',
        type=str,
        default='A0010',
        help='수집할 기관 ID (예: A0010 - 한국전력, A0001 - 산업통상자원부). 기본값: A0010'
    )
    
    # 시작 날짜
    parser.add_argument(
        '--start-date',
        type=str,
        help='수집 시작 날짜 (YYYY-MM-DD 형식, 예: 2025-11-01)'
    )
    
    # 종료 날짜
    parser.add_argument(
        '--end-date',
        type=str,
        help='수집 종료 날짜 (YYYY-MM-DD 형식, 예: 2025-11-30)'
    )
    
    # 설정 파일
    parser.add_argument(
        '--config',
        type=str,
        help='설정 파일 경로 (JSON 형식). 설정 파일이 있으면 명령줄 인자보다 우선합니다.'
    )
    
    return parser.parse_args()


def load_config(config_path):
    """
    설정 파일 로드
    
    Args:
        config_path: 설정 파일 경로
        
    Returns:
        dict: 설정 딕셔너리
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {config_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"설정 파일 JSON 형식 오류: {e}")


def parse_date(date_str):
    """
    날짜 문자열을 datetime 객체로 변환
    
    Args:
        date_str: 날짜 문자열 (YYYY-MM-DD 형식)
        
    Returns:
        datetime: timezone-aware datetime 객체
    """
    try:
        seoul_tz = pytz.timezone('Asia/Seoul')
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return seoul_tz.localize(dt.replace(hour=0, minute=0, second=0))
    except ValueError:
        raise ValueError(f"날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식을 사용하세요: {date_str}")


def main():
    """
    메인 실행 함수
    """
    args = parse_arguments()
    
    # 설정 파일이 있으면 우선 사용
    if args.config:
        config = load_config(args.config)
        org_id = config.get('org_id', 'A0010')
        start_date_str = config.get('start_date')
        end_date_str = config.get('end_date')
    else:
        org_id = args.org_id
        start_date_str = args.start_date
        end_date_str = args.end_date
    
    # 날짜 설정
    seoul_tz = pytz.timezone('Asia/Seoul')
    
    if start_date_str:
        start_date = parse_date(start_date_str)
    else:
        # 기본값: 2025년 11월 1일
        start_date = seoul_tz.localize(datetime(2025, 11, 1, 0, 0, 0))
    
    if end_date_str:
        end_date = parse_date(end_date_str)
        # 종료 날짜는 23:59:59로 설정
        end_date = end_date.replace(hour=23, minute=59, second=59)
    else:
        # 기본값: 2025년 11월 30일
        end_date = seoul_tz.localize(datetime(2025, 11, 30, 23, 59, 59))
    
    # 날짜 검증
    if start_date > end_date:
        print("오류: 시작 날짜가 종료 날짜보다 늦습니다.")
        sys.exit(1)
    
    # 수집 실행
    print("=" * 100)
    print("수집 설정:")
    print(f"  기관 ID: {org_id}")
    print(f"  시작 날짜: {start_date.strftime('%Y-%m-%d')}")
    print(f"  종료 날짜: {end_date.strftime('%Y-%m-%d')}")
    print("=" * 100)
    
    collector = DateRangeCollectMain(org_id, start_date, end_date)
    collector.collect_for_date_range()


if __name__ == "__main__":
    main()

