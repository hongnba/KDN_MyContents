#!/usr/bin/env python3
"""
새로 추가한 단일 문서에 대해 Ollama 분석만 실행하는 스크립트
특정 URL 또는 ObjectId의 문서만 처리

사용법:
    # URL을 인자로 전달
    python3 run_single_url_ollama.py https://www.yna.co.kr/view/AKR20251021023400003
    
    # 인자 없으면 기본 URL 사용
    python3 run_single_url_ollama.py

필요한 정보:
    1. URL: 분석할 기사의 URL (필수)
    2. MongoDB에 이미 저장된 문서여야 함
    3. rawCollectSucYN='Y' (원문 수집 완료)
    4. metaSucYN='N' (아직 Ollama 분석 안됨)

사전 요구사항:
    - MongoDB에 문서가 이미 저장되어 있어야 함
    - contentsRaw.contents에 원문이 있어야 함
"""
import sys
import argparse
sys.path.insert(0, '/app')

from docker_scraping.contents_scraping_ollama_trafilaura import ContentsScrapingOllamaTrafilaura

def main():
    # 명령행 인자 파싱
    parser = argparse.ArgumentParser(
        description='MongoDB에 저장된 문서에 대해 Ollama 5가지 분석 실행',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
    # 특정 URL의 문서 분석
    python3 run_single_url_ollama.py https://www.yna.co.kr/view/AKR20251021023400003
    
    # 기본 URL 사용
    python3 run_single_url_ollama.py
        """
    )
    parser.add_argument(
        'url',
        nargs='?',
        default="https://www.yna.co.kr/view/AKR20251021023400003",
        help='분석할 기사의 URL (MongoDB에 이미 저장되어 있어야 함)'
    )
    
    args = parser.parse_args()
    url = args.url
    
    print("=" * 80)
    print(f"🔍 단일 URL Ollama 분석")
    print(f"URL: {url}")
    print("=" * 80)
    
    # ContentsScrapingOllamaTrafilaura의 crawl_and_analyze_one_ollama 메서드 사용
    # 이 메서드는 URL만 받아서 스크래핑 + Ollama 분석 + MongoDB 저장까지 모두 처리
    scraper = ContentsScrapingOllamaTrafilaura()
    
    # 하지만 이 메서드는 contentsQueueVO가 필요...
    # 더 간단하게: MongoDB에서 해당 URL의 문서를 직접 찾아서 분석
    
    from ksubscribe_share.db.service.contentsService import ContentsService
    from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO
    
    contentsService = ContentsService()
    
    # URL로 문서 찾기
    contents_dict = contentsService.findByURL(url)
    
    if not contents_dict:
        print(f"❌ URL에 해당하는 문서를 찾을 수 없습니다: {url}")
        return
    
    # dict를 ContentsVO 객체로 변환
    contentsVO = ContentsVO(**contents_dict)
    
    print(f"\n✅ 문서 발견!")
    print(f"   제목: {contentsVO.title}")
    print(f"   rawCollectSucYN: {contentsVO.rawCollectSucYN}")
    print(f"   metaSucYN: {contentsVO.metaSucYN}")
    print(f"\n📝 Ollama 5가지 분석 시작...\n")
    
    # 기존 코드의 로직을 그대로 활용
    from ksubscribe_server.analysis.analysis_ollama_generate import AnalysisOllamaGenerateCall
    from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
    from datetime import datetime
    import logging
    
    # 필요한 객체들 생성
    analysisOllama = AnalysisOllamaGenerateCall()
    
    # Logger 생성
    logger = logging.getLogger("ollama_test")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    
    # queueContent 생성 (분석에 필요)
    queueContent = ContentsQueueVO()
    queueContent.contentOrgId = contentsVO.contentsOrgId
    queueContent.cateId = contentsVO.categoryId
    queueContent.url = contentsVO.url
    queueContent.title = contentsVO.title
    
    # 🔑 키워드 리스트와 기관 이름 리스트 - scraper에서 로드
    # scraper 초기화 시 DB에서 자동으로 로드됨
    print(f"📋 키워드 리스트 로딩 중...")
    keyword_name_list = scraper.keyword_name_list if scraper.keyword_name_list else []
    org_name_list = scraper.org_name_list if scraper.org_name_list else []
    
    print(f"   - 키워드 {len(keyword_name_list)}개 로드됨")
    print(f"   - 기관명 {len(org_name_list)}개 로드됨")
    
    # keyword_name_list는 문자열이어야 함 (리스트가 아니라)
    # analysis_ollama_generate.py에서 replace() 사용
    if isinstance(keyword_name_list, list):
        keyword_string = ", ".join(keyword_name_list) if keyword_name_list else ""
    else:
        keyword_string = keyword_name_list
        
    if isinstance(org_name_list, list):
        org_string = ", ".join(org_name_list) if org_name_list else ""
    else:
        org_string = org_name_list
    
    # 원문 텍스트 (contentsRaw가 dict일 수 있음)
    if isinstance(contentsVO.contentsRaw, dict):
        text = contentsVO.contentsRaw.get('contents', '')
    else:
        text = contentsVO.contentsRaw.contents
    
    try:
        # Ollama 분석 실행!
        contentsVO.metaAnalyzeDt = datetime.now()
        print(f"⏳ Ollama 분석 중... (최대 60초 소요)")
        
        isSuccess, contentsMetaResult, summary, sentiment, error_ollamaMetaResult = analysisOllama.analysis_main(
            queueContent=queueContent,
            content=text,
            pred_keyword_list=keyword_string,
            org_name_list=org_string,
            mycontents_logger=logger
        )
        
        if isSuccess:
            print(f"\n✅ Ollama 분석 성공!")
            
            # ContentsVO에 메타데이터 설정
            contentsVO.metaSucYN = "Y"
            contentsVO.contentsMeta = contentsMetaResult
            
            # 결과 출력
            print(f"\n{'='*80}")
            print(f"📊 분석 결과:")
            print(f"{'='*80}")
            print(f"✅ metaSucYN: {contentsVO.metaSucYN}")
            
            # ContentsMetaResult 객체 내용 확인
            print(f"\n� contentsMeta 객체:")
            print(f"   타입: {type(contentsVO.contentsMeta)}")
            if contentsVO.contentsMeta:
                # 객체의 속성 출력
                print(f"   속성: {dir(contentsVO.contentsMeta)}")
                
                # dict로 변환 가능하면 출력
                if hasattr(contentsVO.contentsMeta, '__dict__'):
                    print(f"\n� 분석 결과 상세:")
                    for key, value in contentsVO.contentsMeta.__dict__.items():
                        if not key.startswith('_'):
                            print(f"   {key}: {value}")
            
            # MongoDB 업데이트 - 직접 업데이트
            print(f"\n💾 MongoDB 업데이트 중...")
            
            # contentsMeta를 dict로 변환
            meta_dict = {
                "keywords": contentsMetaResult.contentsMeta.keywords,
                "shortSummary": contentsMetaResult.contentsMeta.shortSummary,
                "longSummary": contentsMetaResult.contentsMeta.longSummary,
                "predKeywords": contentsMetaResult.contentsMeta.predKeywords,
                "sentiments": [
                    {
                        "orgId": s.orgId,
                        "orgName": s.orgName,
                        "positiveRatio": s.positiveRatio,
                        "negativeRatio": s.negativeRatio,
                        "neutralRatio": s.neutralRatio,
                        "reason": s.reason,
                        "positiveKeywords": s.positiveKeywords if hasattr(s, 'positiveKeywords') else [],
                        "negativeKeywords": s.negativeKeywords if hasattr(s, 'negativeKeywords') else []
                    }
                    for s in contentsMetaResult.contentsMeta.sentiments
                ],
                "errorInfo": contentsMetaResult.contentsMeta.errorInfo
            }
            
            # MongoDB 직접 업데이트 (mongoManager 사용)
            collection = contentsService.mongoManager.getCollection("contents")
            from bson import ObjectId
            
            update_result = collection.update_one(
                {"url": url},  # URL로 찾기
                {
                    "$set": {
                        "metaSucYN": "Y",
                        "contentsMeta": meta_dict,
                        "metaAnalyzeDt": contentsVO.metaAnalyzeDt
                    }
                }
            )
            
            print(f"✅ 저장 완료! (매칭: {update_result.matched_count}, 수정: {update_result.modified_count})")
            print(f"\n🎉 Ollama 5가지 분석이 성공적으로 완료되었습니다!")
            print(f"   - 검증 완료 ({summary})")
            print(f"   - 요약 완료 (keywords: {len(contentsMetaResult.contentsMeta.keywords)}개)")
            print(f"   - 감성분석 완료 (sentiments: {len(contentsMetaResult.contentsMeta.sentiments)}개)")
            print(f"   - MongoDB contents 컬렉션 업데이트 완료")
            
        else:
            print(f"❌ Ollama 분석 실패")
            print(f"   Summary: {summary}")
            print(f"   Sentiment: {sentiment}")
            
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*80}")
    print(f"🎉 완료!")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
