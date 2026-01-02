"""
테스트용 스크립트: 특정 pubDt 날짜의 contents_queue 데이터만 처리

사용법:
    python test_scraping_by_pubdt.py
    
    또는 날짜를 지정:
    python test_scraping_by_pubdt.py --pub-dates 2025-11-22 2025-11-26
"""

from datetime import datetime, timedelta
import sys
from typing import List

from docker_scraping.contents_scraping_ollama_trafilaura import ContentsScrapingOllamaTrafilaura
from docker_scraping.web_loader import WebLoaderV3
from docker_collect.driver_utils import get_driver
from ksubscribe_server.analysis.analysis_ollama_generate import AnalysisOllamaGenerateCall
from ksubscribe_server.analysis.ollama_alive import OllamaAlive
from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
from ksubscribe_share.logger import Logger


def process_queue_by_pub_dates(pub_dates: List[str]):
    """
    특정 pubDt 날짜의 contents_queue 데이터만 처리
    
    Args:
        pub_dates: pubDt 필터링할 날짜 리스트 (예: ["2025-11-22", "2025-11-26"])
    """
    logger = Logger().setup_logger(Logger.docker_scraping_result_logger_name)
    logger.info(f"=== 테스트: pubDt 필터링 처리 시작 ===")
    logger.info(f"대상 날짜: {pub_dates}")
    
    try:
        # 1. Ollama alive thread 시작
        checker = OllamaAlive(op_mode="docker_server", keep_alive=False)
        checker.start_thread()
        logger.info("Ollama alive thread started")
        
        # 2. ContentsScrapingOllamaTrafilaura 초기화
        contentsScrapingOllamaTrafilaura = ContentsScrapingOllamaTrafilaura()
        
        # 3. pubDt로 필터링된 큐 데이터 가져오기
        contentsQueueService = ContentsQueueService()
        queueContents: List[ContentsQueueVO] = contentsQueueService.find_by_pub_dates(pub_dates)
        
        logger.info(f"필터링된 Queue 개수: {len(queueContents)}")
        
        if len(queueContents) == 0:
            logger.info("필터링된 Queue가 비어있습니다.")
            checker.stop_thread()
            return
        
        # 4. WebLoader, Driver, OllamaAnalysis 초기화
        webLoader = WebLoaderV3()
        driver = get_driver()
        ollamaAnalysis = AnalysisOllamaGenerateCall()
        
        # 5. 각 큐 아이템 처리
        scrapping_cnt = 0
        analysis_cnt = 0
        
        for index, contentsQueueVO in enumerate(queueContents):
            try:
                logger.info(f"[{index + 1}/{len(queueContents)}] 처리 중: {contentsQueueVO.url}")
                logger.info(f"  - pubDt: {contentsQueueVO.pubDt}")
                logger.info(f"  - title: {contentsQueueVO.title}")
                
                # 개별 아이템 처리
                result = contentsScrapingOllamaTrafilaura.crawl_and_analyze_one_ollama(
                    contentsQueueVO, webLoader, driver, ollamaAnalysis
                )
                
                # crawl_and_analyze_one_ollama는 성공 시 None을 반환하고, 실패 시 False를 반환
                # 따라서 result가 False가 아니면 성공으로 간주
                if result is not False:
                    scrapping_cnt += 1
                    # result가 True이거나 None이면 분석도 성공으로 간주
                    # (실제로는 로그에서 "Contents 요약 및 분석 성공" 메시지로 확인 가능)
                    if result is True or result is None:
                        analysis_cnt += 1
                    
            except Exception as e:
                logger.error(f"아이템 처리 중 오류 발생: {contentsQueueVO.url}")
                logger.error(f"오류 내용: {str(e)}")
                continue
        
        # 6. Driver 종료
        driver.quit()
        
        # 7. 결과 로깅
        logger.info("=" * 80)
        logger.info(f"처리 완료 요약")
        logger.info(f"필터링된 Queue 개수: {len(queueContents)}")
        logger.info(f"스크랩 성공 개수: {scrapping_cnt}")
        logger.info(f"요약 및 분석 성공 개수: {analysis_cnt}")
        logger.info("=" * 80)
        
        # 8. Ollama alive thread 종료
        checker.stop_thread()
        logger.info("=== 테스트 완료 ===")
        
    except Exception as e:
        logger.error(f"처리 중 오류 발생: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        if 'checker' in locals():
            checker.stop_thread()
        if 'driver' in locals():
            try:
                driver.quit()
            except:
                pass


def parse_args():
    """명령줄 인자 파싱"""
    pub_dates = []
    
    if len(sys.argv) > 1:
        if "--pub-dates" in sys.argv:
            idx = sys.argv.index("--pub-dates")
            # --pub-dates 다음의 모든 인자를 날짜로 간주
            for i in range(idx + 1, len(sys.argv)):
                if sys.argv[i].startswith("--"):
                    break
                pub_dates.append(sys.argv[i])
        else:
            # 인자가 있지만 --pub-dates가 없으면 첫 번째 인자를 날짜로 간주
            pub_dates = [sys.argv[1]]
    
    # 기본값: 2025-11-22, 2025-11-26
    if not pub_dates:
        pub_dates = ["2025-11-22", "2025-11-26"]
    
    return pub_dates


if __name__ == "__main__":
    # 명령줄 인자에서 날짜 가져오기
    pub_dates = parse_args()
    
    print("=" * 80)
    print("테스트 스크립트: pubDt 필터링 처리")
    print(f"대상 날짜: {pub_dates}")
    print("=" * 80)
    print()
    
    # 처리 실행
    process_queue_by_pub_dates(pub_dates)

