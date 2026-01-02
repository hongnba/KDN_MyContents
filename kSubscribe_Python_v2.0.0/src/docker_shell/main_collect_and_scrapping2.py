    

from datetime import datetime,timedelta
import sys
import argparse

from docker_collect.collect_v2 import DockerCollectMain
from docker_scraping.contents_scraping_ollama_trafilaura import ContentsScrapingOllamaTrafilaura
from ksubscribe_server.analysis.ollama_alive import OllamaAlive
from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService
from ksubscribe_share.db.service.contentsService import ContentsService
from ksubscribe_share.db.service.statsService import StatsService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.service.calendarService import CalendarService
from ksubscribe_share.logger import Logger
#from ksubscribe_share import config as Conf
import ksubscribe_share.config as Conf


def process_single_url_mode(url: str, org_id: str, cate_id: str):
    """
    단일 URL을 처리하는 모드
    
    Args:
        url: 처리할 기사 URL
        org_id: 기관 ID (예: A0001)
        cate_id: 카테고리 ID (예: B0001)
    
    작동 과정:
        1. URL을 contents_queue에 삽입
        2. Ollama 서버 alive 체크 시작
        3. 스크래핑 및 5개 프롬프트 분석 실행
        4. MongoDB contents 컬렉션에 저장
    """
    logger = Logger().setup_logger(Logger.docker_scraping_result_logger_name)
    logger.info("=== 단일 URL 처리 모드 시작 ===")
    logger.info(f"URL: {url}")
    logger.info(f"기관 ID: {org_id}")
    logger.info(f"카테고리 ID: {cate_id}")
    
    try:
        from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
        from bson import ObjectId
        
        # 1. URL을 contents_queue에 임시 삽입
        logger.info("Step 1: URL을 contents_queue에 삽입")
        queue_vo = ContentsQueueVO(
            _id=ObjectId(),
            url=url,
            contentOrgId=org_id,
            cateId=cate_id,
            title="수동 입력 기사",  # 제목은 스크래핑 시 자동 추출됨
            collectDt=datetime.utcnow()
        )
        
        queue_service = ContentsQueueService()
        
        # 이미 존재하는 URL인지 확인
        if ContentsService().isExistContents(url):
            logger.warning(f"⚠️  이미 contents에 존재하는 URL입니다: {url}")
            logger.info("기존 데이터를 확인하려면 MongoDB에서 조회하세요:")
            logger.info(f'  db.contents.findOne({{url: "{url}"}})')
            return
        
        # Queue에 삽입
        queue_service.insert_queue(queue_vo)
        logger.info(f"✅ Queue 삽입 완료: {queue_vo._id}")
        
        # 2. Ollama alive 체크 시작
        logger.info("Step 2: Ollama 서버 연결 확인")
        checker = OllamaAlive(op_mode="docker_server", keep_alive=False)
        checker.start_thread()
        logger.info("✅ Ollama 서버 연결 완료")
        
        # 3. 스크래핑 및 Ollama 분석 실행
        logger.info("Step 3: 스크래핑 및 Ollama 5개 프롬프트 분석 시작")
        logger.info("  - Trafilaura로 본문 스크래핑")
        logger.info("  - Prompt 1: 키워드 관련성 검증 (question_verify)")
        logger.info("  - Prompt 2: 요약 생성 (question_summary)")
        logger.info("  - Prompt 3: 감성 비율 분석 (question_sentiment_ratio)")
        logger.info("  - Prompt 4: 감성 이유 설명 (sentiment_reason)")
        logger.info("  - Prompt 5: 긍정/부정 키워드 추출 (sentiment_keywords)")
        
        scraper = ContentsScrapingOllamaTrafilaura()
        scraper.crawl_and_analyze_ollama()
        
        # 4. 결과 확인
        logger.info("Step 4: 처리 결과 확인")
        logger.info(f"✅ 스크래핑 성공: {scraper.scrapping_cnt_for_once}건")
        logger.info(f"✅ Ollama 분석 성공: {scraper.analysis_cnt_for_once}건")
        
        # Ollama 종료
        checker.stop_thread()
        
        # MongoDB에서 결과 확인
        logger.info("\n=== MongoDB 저장 결과 확인 방법 ===")
        logger.info("다음 명령으로 저장된 데이터를 확인할 수 있습니다:")
        logger.info(f'docker exec -i ksubscribe_mongodb mongo mycontents --quiet --eval \'db.contents.findOne({{url: "{url}"}})\'')
        
        logger.info("\n=== 단일 URL 처리 완료 ===")
        
    except Exception as e:
        logger.error(f"❌ 처리 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        if 'checker' in locals():
            checker.stop_thread()
        raise


def auto_infer_org_from_url(url: str) -> str:
    """URL 도메인에서 기관 ID를 자동 추론"""
    url_lower = url.lower()
    
    org_mappings = {
        'motie.go.kr': 'A0001',      # 산업통상자원부
        'msit.go.kr': 'A0003',       # 과학기술정보통신부
        'pipc.go.kr': 'A0002',       # 개인정보보호위원회
        'g2b.go.kr': 'A0004',        # 나라장터
        'ketep.re.kr': 'A0005',      # 한국에너지기술평가원
    }
    
    for domain, org_id in org_mappings.items():
        if domain in url_lower:
            return org_id
    
    return None


def auto_infer_category_from_url(url: str) -> str:
    """URL 키워드에서 카테고리 ID를 자동 추론"""
    url_lower = url.lower()
    
    # B0001: 보도자료
    if any(keyword in url_lower for keyword in ['news', 'press', '보도', 'release']):
        return 'B0001'
    # B0002: 사업공고
    elif any(keyword in url_lower for keyword in ['notice', 'announce', '공고', 'bid']):
        return 'B0002'
    # B0003: 정책자료
    elif any(keyword in url_lower for keyword in ['policy', '정책']):
        return 'B0003'
    
    # 기본값: 보도자료
    return 'B0001'
 
        
if __name__ == "__main__":
    
    # 인자 파싱
    parser = argparse.ArgumentParser(description='MyContents 수집/스크래핑 메인 스크립트')
    parser.add_argument('--today-json', action='store_true', 
                       help='today.json 파일의 URL만 처리')
    parser.add_argument('--single-url', type=str, 
                       help='단일 URL 처리 모드 (URL 입력)')
    parser.add_argument('--org', type=str, 
                       help='기관 ID (예: A0001) - 자동 추론 가능')
    parser.add_argument('--category', type=str, 
                       help='카테고리 ID (예: B0001) - 자동 추론 가능')
    
    args = parser.parse_args()
    
    # 모드 1: 단일 URL 처리
    if args.single_url:
        url = args.single_url
        
        # 기관 ID 추론 또는 사용자 입력
        org_id = args.org
        if not org_id:
            org_id = auto_infer_org_from_url(url)
            if org_id:
                print(f"✅ URL에서 기관 자동 추론: {org_id}")
            else:
                print("⚠️  URL에서 기관을 추론할 수 없습니다.")
                print("사용 가능한 기관 ID:")
                print("  A0001: 산업통상자원부")
                print("  A0002: 개인정보보호위원회")
                print("  A0003: 과학기술정보통신부")
                print("  A0004: 나라장터")
                print("  A0005: 한국에너지기술평가원")
                print("\n--org 옵션으로 기관 ID를 지정하세요:")
                print(f'  python3 main_collect_and_scrapping2.py --single-url "{url}" --org A0001 --category B0001')
                sys.exit(1)
        
        # 카테고리 ID 추론 또는 사용자 입력
        cate_id = args.category
        if not cate_id:
            cate_id = auto_infer_category_from_url(url)
            print(f"✅ URL에서 카테고리 자동 추론: {cate_id}")
        
        process_single_url_mode(url, org_id, cate_id)
        sys.exit(0)
    
    # 모드 2: today.json 처리
    # Check if we should process only today.json URLs
    process_today_json_only = len(sys.argv) > 1 and sys.argv[1] == "--today-json"
    
    if process_today_json_only or args.today_json:
        logger = Logger().setup_logger(Logger.docker_scraping_result_logger_name)
        logger.info("=== Processing URLs from today.json only ===")
        try:
            # Start ollama alive thread
            checker = OllamaAlive(op_mode="docker_server",keep_alive=False)
            checker.start_thread()
            
            # Process articles from today.json and save to contents_backup
            contentsScrapingOllamaTrafilaura = ContentsScrapingOllamaTrafilaura()
            logger.info("contentsScrapingOllamaTrafilaura.process_articles_from_today_json()")
            contentsScrapingOllamaTrafilaura.process_articles_from_today_json()
            
            checker.stop_thread()
            logger.info("=== Processing complete ===")
            
        except Exception as e:
            logger.error(f"Error processing today.json: {e}")
            if 'checker' in locals():
                checker.stop_thread()
        sys.exit(0)
    
    # 모드 3: 전체 파이프라인 (기본)
    else:
        logger = Logger().setup_logger(Logger.docker_scraping_result_logger_name)
        logger.info("=== Running full pipeline (collect + scrape) ===")

        # try:
        #     # 1. docker collect
        #     dockerCollectMain = DockerCollectMain()
        #     logger.info("dockerCollectMain.distribute()")
        #     dockerCollectMain.distribute()
        #     
        # except Exception as e:
        #     pass 

        # try:
        #     #Queue의 중복성 검사   
        #     ContentsQueueService().removeDuplicateUrl() 
        # except Exception as e:
        #     pass 

        try:
            # 2. start ollama alive thread
            checker = OllamaAlive(op_mode="docker_server",keep_alive=False)
            checker.start_thread()    
            # 3. docker scrapping
            contentsScrapingOllamaTrafilaura = ContentsScrapingOllamaTrafilaura()
            logger.info("contentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama()")
            contentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama()
        except Exception as e:
            logger.error(f"error : {e}") #error : Message: Service /root/.wdm/drivers/chromedriver/linux64/114.0.5735.90/chromedriver unexpectedly exited. Status code was: 127

        # try:
        #     #contents의 중복성 검사 
        #     logger = Logger().setup_logger(Logger.docker_scraping_result_logger_name)    
        #     ContentsService().removeDuplicateUrl(logger)
        #     pass 
        # except Exception as e:
        #     pass  
        try:
            #7시간전 ~ 지금 까지의 contents 중 ollama 요약 안된 데이터 다시 요약(collectDT 기준)
            logger.info("contentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama() - second time....")
            contentsScrapingOllamaTrafilaura = ContentsScrapingOllamaTrafilaura()
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(hours=7)

            #코드 재개발 필요함 
            contentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama()#(start_date=start_date,end_date=end_date,is_all=False)
        except Exception as e:
            logger.error(f"Second scraping error: {str(e)}")

        try:
            # 4. Calculate statistics for all organizations
            logger = Logger().setup_logger(Logger.docker_scraping_result_logger_name)
            logger.info("=== Calculating statistics ===")
            
            stats_service = StatsService()
            calendar_service = CalendarService()
            contents_org_service = ContentsOrgService()
            
            # Get all organizations
            orgs = contents_org_service.find_all()
            logger.info(f"Found {len(orgs)} organizations")
            
            for org in orgs:
                try:
                    org_id = org.orgId
                    logger.info(f"Processing statistics for {org_id}...")
                    
                    # Calculate statistics for each period
                    for period in ['day', 'week', 'month']:
                        try:
                            # Calculate main statistics
                            stats = stats_service.count_for_period(org_id, period)
                            logger.info(f"  - {period}: {stats._id}")
                            
                            # Calculate calendar results
                            calendar_results = calendar_service.get_calendar_results(org_id)
                            logger.info(f"  - calendar: {len(calendar_results['positiveResult'])} days")
                            
                        except Exception as e:
                            logger.error(f"  - {period}: Error - {str(e)}")
                            
                except Exception as e:
                    logger.error(f"Error processing {org.orgId}: {str(e)}")
            
            logger.info("=== Statistics calculation complete ===")
            
        except Exception as e:
            logger.error(f"Error in statistics calculation: {str(e)}")

        checker.stop_thread()
    


        