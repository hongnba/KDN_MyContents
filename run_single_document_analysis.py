#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
단일 문서 Ollama 분석 실행 스크립트
================================================================================

목적:
    MongoDB contents_queue에 있는 단일 문서를 선택하여
    Ollama 기반 5가지 분석 업무를 수행합니다.

5가지 분석 업무:
    1. 검증 (question_verify): 문서가 DB 키워드와 관련 있는지 확인
    2. 요약 (question_summary): 짧은 요약(1줄) + 긴 요약(5줄 이상) 생성
    3. 감성 비율 (question_sentiment_ratio): 긍정/부정/중립 비율 분석
    4. 감성 이유 (sentiment_reason): 비율 판단 근거 설명
    5. 감성 키워드 (sentiment_keywords): 긍정/부정 키워드 추출

의존성:
    - 1번, 2번: 독립적으로 실행 (서로 무관)
    - 3번 실행 후 → 4번, 5번이 3번 결과를 입력으로 받아 실행
    - 최종: 3, 4, 5번 결과를 하나로 통합

필요한 컨테이너:
    - ksubscribe_mongodb (문서 저장소)
    - ksubscribe_ollama (LLM 분석 엔진)
    - ksubscribe_mariadb (분석 결과 저장)
    - parsing-container (문서 파싱)

실행 방법:
    1. 기본 실행 (선택된 문서 ID로 실행):
       python run_single_document_analysis.py

    2. 특정 문서 ID 지정:
       python run_single_document_analysis.py --document-id <MongoDB ObjectId>

    3. 최신 문서 선택:
       python run_single_document_analysis.py --latest

작성일: 2025-11-12
작성자: AI Assistant
용도: 회사 동료가 코드 수정 없이 그대로 실행 가능하도록 작성됨
================================================================================
"""

import sys
import os
import traceback
from datetime import datetime
from bson import ObjectId

# ============================================================================
# 프로젝트 경로 설정
# ============================================================================
# 현재 스크립트 위치: /home/mycontents/KDN_MyContents/
# 프로젝트 루트: /home/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src
"""
자동 경로 감지:
 - 컨테이너 내부에서는 코드가 일반적으로 `/app`에 마운트되어 있습니다.
 - 개발 환경(호스트)에서는 `/home/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src`에 위치합니다.
스크립트는 실행 환경에 맞춰 적절한 PROJECT_ROOT를 자동으로 선택합니다.
"""

POSSIBLE_PATHS = [
    "/app",  # 컨테이너에서의 일반적인 마운트 위치
    "/home/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src",  # 호스트 개발 환경
    os.path.abspath(os.path.join(os.path.dirname(__file__), "kSubscribe_Python_v2.0.0", "src")),
]

PROJECT_ROOT = None
for p in POSSIBLE_PATHS:
    if p and os.path.isdir(p) and os.path.isdir(os.path.join(p, "docker_scraping")):
        PROJECT_ROOT = p
        break

if PROJECT_ROOT is None:
    # 마지막 수단: 현재 파일의 상위 폴더에서 src를 찾기
    guessed = os.path.abspath(os.path.join(os.path.dirname(__file__), "kSubscribe_Python_v2.0.0", "src"))
    if os.path.isdir(guessed):
        PROJECT_ROOT = guessed

if PROJECT_ROOT is None:
    raise RuntimeError(
        "프로젝트 루트를 찾을 수 없습니다. 컨테이너 내부라면 /app 경로에 프로젝트가 마운트되어 있는지 확인하세요."
    )

# Python import 경로에 프로젝트 루트 추가
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ============================================================================
# 필요한 모듈 import
# ============================================================================
from docker_scraping.contents_scraping_ollama_trafilaura import ContentsScrapingOllamaTrafilaura
from docker_scraping.web_loader import WebLoaderV3
from docker_collect.driver_utils import get_driver
from ksubscribe_server.analysis.analysis_ollama_generate import AnalysisOllamaGenerateCall
from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService
from ksubscribe_share.logger import Logger


# ============================================================================
# 전역 설정
# ============================================================================
# 기본 선택 문서 ID (MongoDB ObjectId)
# 이 ID는 "한국전력기술, 생성형 AI 실무·보안 교육으로 디지털 혁신 가속화" 문서
DEFAULT_DOCUMENT_ID = "68edc849ae3da00bfe2d0cf2"


# ============================================================================
# 메인 함수
# ============================================================================
def main():
    """
    메인 실행 함수
    
    단계:
        1. 명령줄 인자 파싱 (문서 ID 선택)
        2. MongoDB에서 선택된 문서 조회
        3. 필요한 객체 생성 (스크래퍼, 웹로더, 드라이버, Ollama 분석기)
        4. 단일 문서 분석 실행
        5. 결과 출력 및 정리
    """
    
    # ------------------------------------------------------------------------
    # 1. 로거 설정
    # ------------------------------------------------------------------------
    logger = Logger().setup_logger(Logger.docker_scraping_result_logger_name)
    logger.info("=" * 80)
    logger.info("단일 문서 Ollama 분석 시작")
    logger.info("=" * 80)
    
    # ------------------------------------------------------------------------
    # 2. 명령줄 인자 파싱
    # ------------------------------------------------------------------------
    document_id = DEFAULT_DOCUMENT_ID
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--latest":
            # 최신 문서 선택 옵션
            logger.info("옵션: 최신 문서 선택")
            document_id = None  # 나중에 최신 문서로 설정
        elif sys.argv[1] == "--document-id" and len(sys.argv) > 2:
            # 특정 문서 ID 지정
            document_id = sys.argv[2]
            logger.info(f"옵션: 지정된 문서 ID = {document_id}")
        else:
            logger.warning(f"알 수 없는 옵션: {sys.argv[1]}")
            logger.info(f"기본 문서 ID 사용: {DEFAULT_DOCUMENT_ID}")
    else:
        logger.info(f"기본 문서 ID 사용: {DEFAULT_DOCUMENT_ID}")
    
    # ------------------------------------------------------------------------
    # 3. MongoDB에서 문서 조회
    # ------------------------------------------------------------------------
    try:
        logger.info("-" * 80)
        logger.info("Step 1: MongoDB contents_queue에서 문서 조회")
        logger.info("-" * 80)
        
        queue_service = ContentsQueueService()
        
        # 최신 문서 선택 옵션 처리
        if document_id is None:
            logger.info("최신 문서 조회 중...")
            all_docs = queue_service.find_all()
            if not all_docs or len(all_docs) == 0:
                logger.error("❌ contents_queue가 비어 있습니다.")
                return
            # 가장 최근 collectDt를 가진 문서 선택
            queue_content = max(all_docs, key=lambda x: x.collectDt if hasattr(x, 'collectDt') else datetime.min)
            logger.info(f"✅ 최신 문서 선택: {queue_content._id}")
        else:
            # 지정된 ID로 문서 조회
            queue_content = queue_service.find_by_id(ObjectId(document_id))
        
        if queue_content is None:
            logger.error(f"❌ 문서를 찾을 수 없습니다. ID: {document_id}")
            logger.error("   MongoDB contents_queue에 해당 ID의 문서가 존재하지 않습니다.")
            return
        
        # 조회된 문서 정보 출력
        logger.info("✅ 문서 조회 성공")
        logger.info(f"   - 문서 ID: {queue_content._id}")
        logger.info(f"   - 제목: {queue_content.title}")
        logger.info(f"   - URL: {queue_content.url}")
        logger.info(f"   - 기관 ID: {queue_content.contentOrgId}")
        logger.info(f"   - 카테고리 ID: {queue_content.cateId}")
        logger.info(f"   - 수집 키워드: {queue_content.collectKeyword}")
        logger.info(f"   - 발행일: {queue_content.pubDt}")
        logger.info(f"   - 수집일: {queue_content.collectDt}")
        
    except Exception as e:
        logger.error(f"❌ 문서 조회 중 오류 발생: {e}")
        logger.error(traceback.format_exc())
        return
    
    # ------------------------------------------------------------------------
    # 4. 필요한 객체 생성
    # ------------------------------------------------------------------------
    try:
        logger.info("-" * 80)
        logger.info("Step 2: 분석에 필요한 객체 생성")
        logger.info("-" * 80)
        
        # 웹 스크래퍼 생성
        # - Trafilatura 기반 콘텐츠 스크래핑
        # - 키워드, 기관 목록 등 초기화
        logger.info("ContentsScrapingOllamaTrafilaura 생성 중...")
        scraper = ContentsScrapingOllamaTrafilaura()
        logger.info("✅ Scraper 생성 완료")
        
        # 웹 로더 생성
        # - HTML/PDF 콘텐츠 로딩 담당
        logger.info("WebLoaderV3 생성 중...")
        web_loader = WebLoaderV3()
        logger.info("✅ WebLoader 생성 완료")
        
        # Selenium 드라이버 생성
        # - 동적 웹페이지 렌더링용
        logger.info("Selenium 드라이버 생성 중...")
        driver = get_driver()
        logger.info("✅ Selenium 드라이버 생성 완료")
        
        # Ollama 분석기 생성
        # - 5가지 분석 업무 수행 (검증, 요약, 감성 분석)
        logger.info("AnalysisOllamaGenerateCall 생성 중...")
        ollama_analysis = AnalysisOllamaGenerateCall()
        logger.info("✅ Ollama 분석기 생성 완료")
        logger.info(f"   - 사용 모델: {ollama_analysis.chat_ollama.model}")
        logger.info(f"   - Ollama URL: {ollama_analysis.chat_ollama.base_url}")
        
    except Exception as e:
        logger.error(f"❌ 객체 생성 중 오류 발생: {e}")
        logger.error(traceback.format_exc())
        return
    
    # ------------------------------------------------------------------------
    # 5. 단일 문서 분석 실행
    # ------------------------------------------------------------------------
    try:
        logger.info("-" * 80)
        logger.info("Step 3: 단일 문서 분석 실행")
        logger.info("-" * 80)
        logger.info("분석 시작 시각: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        logger.info("")
        logger.info("📊 5가지 분석 업무 순서:")
        logger.info("   1️⃣  검증 (question_verify)")
        logger.info("       → 문서가 DB 키워드와 관련 있는지 확인")
        logger.info("       → 출력: ai_keyword, related, reason")
        logger.info("")
        logger.info("   2️⃣  요약 (question_summary)")
        logger.info("       → 짧은 요약 + 긴 요약 생성")
        logger.info("       → 출력: short_summary, long_summary")
        logger.info("")
        logger.info("   3️⃣  감성 비율 (question_sentiment_ratio)")
        logger.info("       → 긍정/부정/중립 비율 분석")
        logger.info("       → 출력: positiveRatio, negativeRatio, neutralRatio")
        logger.info("")
        logger.info("   4️⃣  감성 이유 (sentiment_reason) [3번 결과 사용]")
        logger.info("       → 비율 판단 근거 설명")
        logger.info("       → 출력: reason, positiveReason, negativeReason")
        logger.info("")
        logger.info("   5️⃣  감성 키워드 (sentiment_keywords) [3번 결과 사용]")
        logger.info("       → 긍정/부정 키워드 추출")
        logger.info("       → 출력: positiveKeywords, negativeKeywords")
        logger.info("")
        logger.info("   최종: 3, 4, 5번 결과를 하나의 SentimentInfo로 통합")
        logger.info("-" * 80)
        
        # 실제 분석 함수 호출
        # crawl_and_analyze_one_ollama는 다음 작업을 수행:
        #   1. URL에서 콘텐츠 스크래핑 (Trafilatura 사용)
        #   2. Ollama로 5가지 분석 업무 실행
        #   3. 결과를 MongoDB (contents 컬렉션)에 저장
        #   4. 결과를 MariaDB (ARTICLES_SUMMARY, ARTICLE_KEYWORDS 테이블)에 저장
        scraper.crawl_and_analyze_one_ollama(
            queueContent=queue_content,
            webLoader=web_loader,
            driver=driver,
            ollamaAnalysis=ollama_analysis
        )
        
        logger.info("-" * 80)
        logger.info("✅ 분석 완료")
        logger.info("분석 종료 시각: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        logger.info("-" * 80)
        
    except Exception as e:
        logger.error(f"❌ 분석 실행 중 오류 발생: {e}")
        logger.error(traceback.format_exc())
    
    # ------------------------------------------------------------------------
    # 6. 정리 (Cleanup)
    # ------------------------------------------------------------------------
    finally:
        try:
            logger.info("-" * 80)
            logger.info("Step 4: 리소스 정리")
            logger.info("-" * 80)
            
            # Selenium 드라이버 종료
            if 'driver' in locals():
                logger.info("Selenium 드라이버 종료 중...")
                driver.quit()
                logger.info("✅ Selenium 드라이버 종료 완료")
            
            logger.info("=" * 80)
            logger.info("단일 문서 Ollama 분석 종료")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"정리 중 오류 발생: {e}")


# ============================================================================
# 유틸리티 함수: 문서 목록 출력
# ============================================================================
def print_available_documents():
    """
    MongoDB contents_queue에 있는 모든 문서 목록을 출력합니다.
    
    사용 예:
        python run_single_document_analysis.py --list
    """
    try:
        logger = Logger().setup_logger(Logger.docker_scraping_result_logger_name)
        logger.info("=" * 80)
        logger.info("MongoDB contents_queue 문서 목록")
        logger.info("=" * 80)
        
        queue_service = ContentsQueueService()
        all_docs = queue_service.find_all()
        
        if not all_docs or len(all_docs) == 0:
            logger.info("❌ contents_queue가 비어 있습니다.")
            return
        
        logger.info(f"총 {len(all_docs)}개 문서 발견")
        logger.info("-" * 80)
        
        for idx, doc in enumerate(all_docs, 1):
            logger.info(f"{idx}. ID: {doc._id}")
            logger.info(f"   제목: {doc.title}")
            logger.info(f"   URL: {doc.url}")
            logger.info(f"   키워드: {doc.collectKeyword}")
            logger.info(f"   발행일: {doc.pubDt}")
            logger.info("-" * 80)
        
        logger.info(f"\n특정 문서 분석 실행 방법:")
        logger.info(f"python run_single_document_analysis.py --document-id <위의 ID 중 하나>")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print(traceback.format_exc())


# ============================================================================
# 스크립트 진입점
# ============================================================================
if __name__ == "__main__":
    # --list 옵션: 사용 가능한 문서 목록 출력
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        print_available_documents()
    else:
        # 기본 동작: 단일 문서 분석 실행
        main()
