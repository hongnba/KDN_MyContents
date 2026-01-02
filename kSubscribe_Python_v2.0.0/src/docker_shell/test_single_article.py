#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 기사 분석 테스트 스크립트
URL 또는 원문 텍스트를 입력받아 Ollama 분석 실행

사용법:
  # URL만으로 테스트 (자동 스크래핑)
  python test_single_article.py --url "https://example.com/article" --org A0001 --category B0002

  # 원문 텍스트 직접 입력 (스크래핑 생략)
  python test_single_article.py --text "기사 원문..." --org A0001 --category B0002
"""

import sys
import argparse
from datetime import datetime
import pytz
import json

from docker_scraping.contents_scraping_ollama_trafilaura import ContentsScrapingOllamaTrafilaura
from docker_scraping.ai_scraping.trafilaura import TrafilauraScraper
from docker_collect.driver_utils import get_driver
from ksubscribe_server.analysis.analysis_ollama_generate import AnalysisOllamaGenerateCall
from ksubscribe_server.analysis.ollama_alive import OllamaAlive
from ksubscribe_share.logger import Logger
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.predefineKeywordService import PredefineKeywordService


def test_with_url(url: str, org_id: str, category_id: str):
    """
    URL만 제공받아 스크래핑 + 분석 실행
    """
    logger = Logger().setup_logger(Logger.docker_scraping_result_logger_name)
    logger.info(f"=== URL 기반 테스트 시작 ===")
    logger.info(f"URL: {url}")
    logger.info(f"기관: {org_id}, 카테고리: {category_id}")
    
    # Ollama 헬스체크 시작
    checker = OllamaAlive(op_mode="docker_server", keep_alive=False)
    checker.start_thread()
    
    try:
        # 1. 웹 스크래핑 (URL → 본문)
        logger.info("1단계: 웹 스크래핑 중...")
        scraper = TrafilauraScraper()
        is_success, title, raw_text = scraper.get_newbody(url)
        
        if not is_success or not raw_text:
            logger.error(f"스크래핑 실패: {url}")
            return None
        
        logger.info(f"✅ 스크래핑 성공!")
        logger.info(f"제목: {title[:100]}...")
        logger.info(f"본문 길이: {len(raw_text)} 자")
        
        # 2. Ollama 분석
        result = analyze_text(raw_text, org_id, category_id, url, logger)
        
        return result
        
    finally:
        checker.stop_thread()


def test_with_text(text: str, org_id: str, category_id: str, url: str = "https://test.example.com"):
    """
    원문 텍스트를 직접 제공받아 분석만 실행 (스크래핑 생략)
    """
    logger = Logger().setup_logger(Logger.docker_scraping_result_logger_name)
    logger.info(f"=== 원문 직접 입력 테스트 시작 ===")
    logger.info(f"기관: {org_id}, 카테고리: {category_id}")
    logger.info(f"본문 길이: {len(text)} 자")
    
    # Ollama 헬스체크 시작
    checker = OllamaAlive(op_mode="docker_server", keep_alive=False)
    checker.start_thread()
    
    try:
        result = analyze_text(text, org_id, category_id, url, logger)
        return result
    finally:
        checker.stop_thread()


def analyze_text(text: str, org_id: str, category_id: str, url: str, logger):
    """
    공통 분석 로직: 원문 텍스트 → Ollama 분석
    """
    logger.info("2단계: Ollama 분석 중...")
    
    # 키워드 및 기관 목록 준비
    keywords = PredefineKeywordService().getKeywordList()
    keyword_list = ", ".join(keywords)
    
    org_list = CommCodeService().get_org_name_list()
    org_name_list = ", ".join([org["codeName"] for org in org_list])
    
    # Queue 정보 생성 (메타데이터용)
    queue_content = ContentsQueueVO()
    queue_content.url = url
    queue_content.contentOrgId = org_id
    queue_content.cateId = category_id
    queue_content.pubDt = datetime.now(pytz.UTC)
    queue_content.collectDt = datetime.now(pytz.UTC)
    queue_content.title = "테스트 기사"
    
    # Ollama 분석 실행
    analyzer = AnalysisOllamaGenerateCall()
    success, result, summary, sentiment, error = analyzer.analysis_main(
        content=text,
        pred_keyword_list=keyword_list,
        org_name_list=org_name_list,
        mycontents_logger=logger,
        queueContent=queue_content
    )
    
    if success and result:
        logger.info("✅ Ollama 분석 성공!")
        
        # 결과 출력
        print("\n" + "="*60)
        print("📊 분석 결과")
        print("="*60)
        
        meta = result.contentsMeta
        
        print(f"\n🔑 키워드:")
        if meta.keywords:
            for kw in meta.keywords:
                print(f"  - {kw}")
        
        print(f"\n📝 짧은 요약:")
        print(f"  {meta.shortSummary}")
        
        print(f"\n📄 긴 요약:")
        print(f"  {meta.longSummary}")
        
        print(f"\n💡 사전정의 키워드:")
        if meta.predKeywords:
            for key, value in meta.predKeywords.items():
                print(f"  - {key}: {value}")
        
        print(f"\n😊 감성 분석:")
        if meta.sentiments:
            for sent in meta.sentiments:
                print(f"  기관: {sent.orgName} ({sent.orgId})")
                print(f"    긍정: {sent.positiveRatio}%")
                print(f"    부정: {sent.negativeRatio}%")
                print(f"    중립: {sent.neutralRatio}%")
                print(f"    이유: {sent.reason}")
        
        print("\n" + "="*60)
        
        # JSON으로도 저장
        result_json = {
            "url": url,
            "keywords": meta.keywords,
            "shortSummary": meta.shortSummary,
            "longSummary": meta.longSummary,
            "predKeywords": meta.predKeywords,
            "sentiments": [
                {
                    "orgId": s.orgId,
                    "orgName": s.orgName,
                    "positiveRatio": s.positiveRatio,
                    "negativeRatio": s.negativeRatio,
                    "neutralRatio": s.neutralRatio,
                    "reason": s.reason
                } for s in (meta.sentiments or [])
            ]
        }
        
        output_file = "test_result.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result_json, f, ensure_ascii=False, indent=2)
        
        logger.info(f"결과를 {output_file}에 저장했습니다.")
        return result
    
    else:
        logger.error("❌ Ollama 분석 실패!")
        if error:
            logger.error(f"오류: {error}")
        return None


def infer_org_from_url(url: str) -> str:
    """
    URL에서 기관을 자동 추론
    """
    url_lower = url.lower()
    
    # URL 도메인 기반 매핑
    org_mappings = {
        'motie.go.kr': 'A0001',  # 산업통상자원부
        'msit.go.kr': 'A0003',   # 과학기술정보통신부
        'pipc.go.kr': 'A0002',   # 개인정보보호위원회
        'g2b.go.kr': 'A0004',    # 나라장터
        'ketep.re.kr': 'A0005',  # 한국에너지기술평가원
        'kepco.co.kr': 'A0010',  # 한국전력공사
        'me.go.kr': 'A0003',     # 환경부 (임시)
    }
    
    for domain, org_id in org_mappings.items():
        if domain in url_lower:
            return org_id
    
    return None  # 추론 실패


def infer_category_from_url(url: str) -> str:
    """
    URL에서 카테고리를 자동 추론 (간단한 휴리스틱)
    """
    url_lower = url.lower()
    
    # URL 패턴 기반 카테고리 추론
    if any(keyword in url_lower for keyword in ['news', 'press', '보도', 'release']):
        return 'B0001'  # 보도자료
    elif any(keyword in url_lower for keyword in ['notice', 'announce', '공고', 'bid']):
        return 'B0002'  # 사업공고
    elif any(keyword in url_lower for keyword in ['policy', '정책']):
        return 'B0003'  # 정책자료
    
    return 'B0001'  # 기본값: 보도자료


def main():
    parser = argparse.ArgumentParser(
        description='단일 기사 Ollama 분석 테스트',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  # URL만으로 테스트 (기관/카테고리 자동 추론)
  python test_single_article.py --url "https://www.motie.go.kr/kor/article/..."

  # 기관/카테고리 직접 지정
  python test_single_article.py --url "https://..." --org A0001 --category B0002

  # 원문 직접 입력 (기관/카테고리 필수)
  python test_single_article.py --text "산업통상자원부는..." --org A0001 --category B0002

  # 원문을 파일에서 읽기
  python test_single_article.py --file article.txt --org A0001 --category B0002
        """
    )
    
    # 입력 방식 선택
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--url', help='기사 URL (자동 스크래핑, 기관/카테고리 자동 추론 가능)')
    input_group.add_argument('--text', help='기사 원문 텍스트 (직접 입력)')
    input_group.add_argument('--file', help='기사 원문이 담긴 텍스트 파일 경로')
    
    # 메타데이터 (이제 선택사항)
    parser.add_argument('--org', help='기관 ID (예: A0001, 생략 시 URL에서 자동 추론)')
    parser.add_argument('--category', help='카테고리 ID (예: B0002, 생략 시 자동 추론 또는 기본값)')
    parser.add_argument('--url-meta', help='원문 직접 입력 시 URL 메타데이터 (선택)')
    
    args = parser.parse_args()
    
    # 기관 및 카테고리 결정
    org_id = args.org
    category_id = args.category
    
    # 입력 방식에 따라 실행
    if args.url:
        # URL에서 기관/카테고리 자동 추론 (지정하지 않은 경우)
        if not org_id:
            org_id = infer_org_from_url(args.url)
            if org_id:
                print(f"✅ URL에서 기관 자동 추론: {org_id}")
            else:
                print("⚠️  URL에서 기관을 추론할 수 없습니다.")
                print("다음 중 하나를 선택하여 --org 옵션으로 지정하세요:")
                print("  A0001: 산업통상자원부")
                print("  A0002: 개인정보보호위원회")
                print("  A0003: 과학기술정보통신부")
                print("  A0004: 나라장터")
                print("  A0005: 한국에너지기술평가원")
                return
        
        if not category_id:
            category_id = infer_category_from_url(args.url)
            print(f"✅ URL에서 카테고리 자동 추론: {category_id} (보도자료/공고/정책 키워드 기반)")
        
        test_with_url(args.url, org_id, category_id)
    
    elif args.text:
        # 원문 직접 입력 시에는 기관/카테고리 필수
        if not org_id or not category_id:
            print("❌ 원문 직접 입력 시에는 --org와 --category를 반드시 지정해야 합니다.")
            print("\n사용 가능한 기관 ID:")
            print("  A0001: 산업통상자원부")
            print("  A0002: 개인정보보호위원회")
            print("  A0003: 과학기술정보통신부")
            print("\n사용 가능한 카테고리 ID:")
            print("  B0001: 보도자료")
            print("  B0002: 사업공고")
            print("  B0003: 정책자료")
            return
        
        url_meta = args.url_meta or "https://test.example.com"
        test_with_text(args.text, org_id, category_id, url_meta)
    
    elif args.file:
        # 파일 입력 시에도 기관/카테고리 필수
        if not org_id or not category_id:
            print("❌ 파일 입력 시에는 --org와 --category를 반드시 지정해야 합니다.")
            return
        
        with open(args.file, 'r', encoding='utf-8') as f:
            text = f.read()
        url_meta = args.url_meta or "https://test.example.com"
        test_with_text(text, org_id, category_id, url_meta)


if __name__ == "__main__":
    main()
