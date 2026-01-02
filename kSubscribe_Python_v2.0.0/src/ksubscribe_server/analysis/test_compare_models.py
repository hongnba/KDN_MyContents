"""
리스트의 URL들에 대해 스크래핑/분석 후 두 모델로 비교 분석
"""

import sys
import time
import logging
from datetime import datetime
from bson import ObjectId
from langchain_ollama import ChatOllama
import ksubscribe_share.config as CONF
from ksubscribe_server.analysis.analysis_ollama_generate import AnalysisOllamaGenerateCall
from ksubscribe_server.analysis.ollama_alive import OllamaAlive
from docker_scraping.contents_scraping_ollama_trafilaura import ContentsScrapingOllamaTrafilaura
from docker_collect.driver_utils import get_driver
from docker_scraping.web_loader import WebLoaderV3
from ksubscribe_share.db.service.contentsService import ContentsService
from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.predefineKeywordService import PredefineKeywordService
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO

URLS = [
    "https://news.kbs.co.kr/news/pc/view/view.do?ncd=8379101&ref=A",
    "http://www.todaykorea.co.kr/news/articleView.html?idxno=335246",
    "https://www.gokorea.kr/news/articleView.html?idxno=842077"
]

MODELS = ["gpt-oss:20b", "llama-3-Korean-Bllossom-8B-Q4_K_M:latest"]


def get_or_create_queue_content(url):
    """contents_queue에서 URL 찾거나 생성"""
    queue_service = ContentsQueueService()
    
    # queue에서 찾기
    queue_dict = queue_service.findByURL(url)
    if queue_dict:
        return ContentsQueueVO(**queue_dict)
    
    # queue에 없으면 생성
    queue_vo = ContentsQueueVO(
        _id=ObjectId(),
        url=url,
        contentOrgId="A0001",
        cateId="B0001",
        title="수동 입력 기사",
        collectDt=datetime.utcnow()
    )
    queue_service.insert_queue(queue_vo)
    print(f"Queue에 추가: {url}")
    return queue_vo


def scrape_and_analyze_url(url):
    """특정 URL 스크래핑 및 분석"""
    queue_content = get_or_create_queue_content(url)
    
    checker = OllamaAlive(op_mode="docker_server", keep_alive=False)
    checker.start_thread()
    
    try:
        scraper = ContentsScrapingOllamaTrafilaura()
        web_loader = WebLoaderV3()
        driver = get_driver()
        ollama_analysis = AnalysisOllamaGenerateCall()
        
        scraper.crawl_and_analyze_one_ollama(
            queueContent=queue_content,
            webLoader=web_loader,
            driver=driver,
            ollamaAnalysis=ollama_analysis
        )
        
        driver.quit()
        return True
    except Exception as e:
        print(f"스크래핑 오류: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        checker.stop_thread()


def get_content(url, retry_count=5, retry_delay=3):
    """URL로 문서와 원문 가져오기 (재시도 포함)"""
    contentsService = ContentsService()
    
    for i in range(retry_count):
        contents_dict = contentsService.findByURL(url)
        if contents_dict:
            contentsVO = ContentsVO(**contents_dict)
            
            # 원문 텍스트 추출
            if isinstance(contentsVO.contentsRaw, dict):
                text = contentsVO.contentsRaw.get('contents', '')
            else:
                text = contentsVO.contentsRaw.contents if hasattr(contentsVO.contentsRaw, 'contents') else ''
            
            if text:
                queueContent = ContentsQueueVO()
                queueContent.contentOrgId = contentsVO.contentsOrgId
                queueContent.cateId = contentsVO.categoryId
                queueContent.url = contentsVO.url
                queueContent.title = contentsVO.title
                return contentsVO, queueContent, text
            else:
                print(f"원문이 없습니다. {retry_delay}초 후 재시도... ({i+1}/{retry_count})")
        else:
            print(f"문서를 찾을 수 없습니다. {retry_delay}초 후 재시도... ({i+1}/{retry_count})")
        
        if i < retry_count - 1:
            time.sleep(retry_delay)
    
    return None, None, None


def analyze(model_name, content, queueContent, keyword_list, org_list):
    print(f"\n[{model_name}] 분석 중...")
    
    try:
        logger = logging.getLogger(f"analyze_{model_name}")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            logger.addHandler(logging.StreamHandler())
        
        if "gpt-oss" in model_name:
            chat_ollama = ChatOllama(model=model_name, base_url=CONF.OLLAMA_URL)
        else:
            chat_ollama = ChatOllama(model=model_name, base_url=CONF.OLLAMA_URL, format="json")
        chat_ollama.client_kwargs["timeout"] = 180
        chat_ollama._set_clients()
        
        original_model = CONF.OLLAMA_MODEL
        CONF.OLLAMA_MODEL = model_name
        
        try:
            analysis = AnalysisOllamaGenerateCall()
            analysis.chat_ollama = chat_ollama
            
            isSuccess, result, _, _, _ = analysis.analysis_main(
                queueContent=queueContent,
                content=content,
                pred_keyword_list=keyword_list,
                org_name_list=org_list,
                mycontents_logger=logger
            )
            
            if isSuccess and result:
                meta = result.contentsMeta
                print(f"성공")
                print(f"요약: {meta.shortSummary[:150] if meta.shortSummary else 'N/A'}")
                if meta.sentiments:
                    for s in meta.sentiments:
                        org = s.orgName if hasattr(s, 'orgName') else 'N/A'
                        print(f"{org}: 긍정 {s.positiveRatio}%, 부정 {s.negativeRatio}%, 중립 {s.neutralRatio}%")
                return result
            else:
                print(f"실패")
                return None
        finally:
            CONF.OLLAMA_MODEL = original_model
            
    except Exception as e:
        print(f"오류: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    print("="*80)
    print("URL 리스트 테스트 시작")
    print("="*80)
    
    org_list = CommCodeService().get_org_name_list()
    keywords = PredefineKeywordService().getKeywordList()
    keyword_list = ", ".join(keywords)
    org_list_str = ", ".join([org["codeName"] for org in org_list])
    
    for url in URLS:
        print(f"\n{'='*80}")
        print(f"URL: {url}")
        print(f"{'='*80}")
        
        print("\nStep 1: 스크래핑 및 분석")
        print("-"*80)
        scrape_and_analyze_url(url)
        
        # 스크래핑 후 저장 대기
        print("저장 대기 중...")
        time.sleep(5)
        
        print("\nStep 2: 모델 비교 분석")
        print("-"*80)
        
        contentsVO, queueContent, content_text = get_content(url)
        if not content_text:
            print("문서를 찾을 수 없습니다.")
            continue
        
        print(f"제목: {contentsVO.title}")
        
        results = {}
        for model in MODELS:
            results[model] = analyze(model, content_text, queueContent, keyword_list, org_list_str)
        
        print(f"\n비교 결과:")
        for model, result in results.items():
            print(f"\n[{model}]")
            if result and result.contentsMeta:
                meta = result.contentsMeta
                print(f"요약: {meta.shortSummary[:200] if meta.shortSummary else 'N/A'}")
                if meta.sentiments:
                    for s in meta.sentiments:
                        org = s.orgName if hasattr(s, 'orgName') else 'N/A'
                        print(f"{org}: 긍정 {s.positiveRatio}%, 부정 {s.negativeRatio}%, 중립 {s.neutralRatio}%")
    
    print(f"\n{'='*80}")
    print("전체 분석 완료")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()