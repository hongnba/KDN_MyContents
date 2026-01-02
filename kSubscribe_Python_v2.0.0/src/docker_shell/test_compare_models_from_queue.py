"""
contents_queue에서 3개 URL을 선택하여 두 모델로 비교 분석하는 스크립트
- gpt-oss:20b
- llama-3-Korean-Bllossom-8B-Q4_K_M:latest

사용법:
    docker exec ksubscribe_python_unified python3 /app/compare_models_from_queue.py
    docker exec ksubscribe_python_unified python3 /app/compare_models_from_queue.py --count 5
"""

import sys
import traceback
import time
import logging
import json
from datetime import datetime, timezone
from bson import ObjectId
from typing import List, Dict

from ksubscribe_share.logger import Logger
from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService
from ksubscribe_share.db.service.contentsService import ContentsService
from ksubscribe_share.db.service.predefineKeywordService import PredefineKeywordService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.service.baseQueryService import BaseQueryService
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO, ContentsRaw, ContentsMeta
from ksubscribe_server.analysis.analysis_ollama_generate import AnalysisOllamaGenerateCall
from ksubscribe_server.similarity.simularity_check import SimularityChecker
from ksubscribe_server.models.contentsMetaResult import ContentsMetaResult
from docker_scraping.ai_scraping.trafilaura import TrafilauraScraper
from docker_scraping.web_loader import WebLoaderV3
from docker_collect.driver_utils import get_driver
from langchain_ollama import ChatOllama
import ksubscribe_share.config as CONF


class CustomAnalysisOllamaGenerateCall(AnalysisOllamaGenerateCall):
    """
    format="json" 파라미터 없이 작동하는 커스텀 분석 클래스
    test_model_response_format.py에서 확인한 방식대로 format 파라미터를 제거
    """
    def __init__(self):
        # 부모 클래스의 다른 초기화는 그대로 사용하되, chat_ollama만 format 없이 초기화
        from ksubscribe_share.db.service.predefineKeywordService import PredefineKeywordService
        from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService
        
        # format="json" 없이 ChatOllama 초기화
        self.chat_ollama = ChatOllama(model=CONF.OLLAMA_MODEL, base_url=CONF.OLLAMA_URL)
        self.chat_ollama.client_kwargs["timeout"] = 180
        self.chat_ollama._set_clients()
        
        # 부모 클래스의 다른 속성들 초기화
        self.keywords = PredefineKeywordService().getKeywordList()
        self.contentsQueueService = ContentsQueueService()
        
        # generate 메서드를 래핑하여 format="json" 파라미터 제거
        original_generate = self.chat_ollama._client.generate
        def generate_without_format(*args, **kwargs):
            # format 파라미터가 있으면 제거
            if 'format' in kwargs:
                del kwargs['format']
            return original_generate(*args, **kwargs)
        self.chat_ollama._client.generate = generate_without_format
    
    def analysis_main(self, content, pred_keyword_list, org_name_list, mycontents_logger:logging.Logger, queueContent:ContentsQueueVO):
        """analysis_main 오버라이드 - JSON 파싱 실패 시 None 체크 추가"""
        try: 
            contentsMetaResult = ContentsMetaResult()
            contentsMetaResult.contentsMeta.method = "ollama"
            
            # 사전질의
            verify_start = time.time()
            pre_question_verify = self.question_verify.replace("pred_keywords_from_db", pred_keyword_list).replace("[contents]",content)
            result_verify = self.chat_ollama._client.generate(
                                    model=CONF.OLLAMA_MODEL,
                                    prompt=pre_question_verify)
            is_success_keywords, result_verify_json = self.json_load(result_verify, mycontents_logger)  
            
            # JSON 파싱 실패 체크
            if not is_success_keywords or result_verify_json is None:
                mycontents_logger.error("키워드 검증 JSON 파싱 실패")
                raise Exception("키워드 검증 JSON 파싱 실패")
            
            related = result_verify_json['related']
            ai_keywords = result_verify_json["ai_keyword"]
                        
            verify_end = time.time()
            mycontents_logger.info(f"분석대상 사전검증 소요시간 : {verify_end-verify_start} 초 소요")
                        
            summary_start = time.time()
            new_question_summary = self.question_summary.replace("pred_keywords_from_db", pred_keyword_list).replace("[contents]",content)
            result_summary = self.chat_ollama._client.generate(
                                    model=CONF.OLLAMA_MODEL,
                                    prompt=new_question_summary)
            
            summary_end = time.time()
            is_success, result_summary_json = self.json_load(result_summary, mycontents_logger)  
            
            # JSON 파싱 실패 체크
            if not is_success or result_summary_json is None:
                mycontents_logger.error("요약 JSON 파싱 실패")
                raise Exception("요약 JSON 파싱 실패")
            
            # 키워드 추출
            if related:
                keywords_verify = result_verify_json['reason']
                if isinstance(keywords_verify, list) and len(keywords_verify) > 0:
                    pred_keywords = SimularityChecker().best_keyword_of_summary(result_summary_json["short_summary"],keywords_verify)
                else:
                    pred_keywords = None
                    mycontents_logger.info(f"키워드 추출대상 아님")        
            else:
                pred_keywords = None
                mycontents_logger.info(f"키워드 추출대상 아님")
                
            # article keywords
            try:
                article_keywords = result_verify_json["ai_keyword"]
            except Exception as e:
                article_keywords = None
                mycontents_logger.info(f"ai_keyword 없음")
            
            summary_success = self.summary_to_ollamaModel_v2(result_summary, result_summary_json, contentsMetaResult, pred_keywords, ai_keywords, mycontents_logger) 
            contentsMetaResult.summarySucYN = "Y" if summary_success else "N"
            mycontents_logger.info(f"요약분석 소요시간 : {summary_end-summary_start} 초 소요")

            # 감성 분석
            orgId = queueContent.contentOrgId    
            orgName, combined_keywords = ContentsOrgService().getOrgNameAndKeywords(queueContent.contentOrgId)
            new_question_sentiment_ratio = self.question_sentiment_ratio.replace("[organization]", str(orgName) if orgName else "").replace("[contents]",content)
            if combined_keywords and isinstance(combined_keywords, list):
                synonyms_str = ", ".join(str(item) for item in combined_keywords)
                new_question_sentiment_ratio = new_question_sentiment_ratio.replace("[synonyms]", synonyms_str)
            else:
                new_question_sentiment_ratio = new_question_sentiment_ratio.replace("[synonyms]", str(orgName) if orgName else "")
            
            sentiment_start = time.time()
            #3-1) ratio 추출
            result_sentiment_ratio = self.chat_ollama._client.generate(
                                    model=CONF.OLLAMA_MODEL,
                                    prompt=new_question_sentiment_ratio)
            is_success, result_sentiment_ratio_json = self.json_load(result_sentiment_ratio, mycontents_logger) 
            
            # JSON 파싱 실패 체크
            if not is_success or result_sentiment_ratio_json is None:
                mycontents_logger.warning("감성 비율 JSON 파싱 실패, 기본값 사용")
                positiveRatio = 0
                negativeRatio = 0
            else:
                positiveRatio = self.str_to_double(result_sentiment_ratio_json.get("positiveRatio", "0"))
                negativeRatio = self.str_to_double(result_sentiment_ratio_json.get("negativeRatio", "0"))
            
            #3-2) reason 추출
            new_question_sentiment_reason = self.sentiment_reason.replace("[organization]", str(orgName) if orgName else "").replace("[contents]",content)
            if combined_keywords and isinstance(combined_keywords, list):
                synonyms_str = ", ".join(str(item) for item in combined_keywords)
                new_question_sentiment_reason = new_question_sentiment_reason.replace("[synonyms]", synonyms_str)
            else:
                new_question_sentiment_reason = new_question_sentiment_reason.replace("[synonyms]", str(orgName) if orgName else "")
            new_question_sentiment_reason = new_question_sentiment_reason.replace("[positiveRatio]", str(positiveRatio)).replace("[negativeRatio]", str(negativeRatio))
            
            result_sentiment_reason = self.chat_ollama._client.generate(
                                    model=CONF.OLLAMA_MODEL,
                                    prompt=new_question_sentiment_reason)
            is_success, result_sentiment_reason_json = self.json_load(result_sentiment_reason, mycontents_logger) 
            
            #3-3) keywords 추출
            new_question_sentiment_keywords = self.sentiment_keywords.replace("[organization]", str(orgName) if orgName else "").replace("[contents]",content)
            if combined_keywords and isinstance(combined_keywords, list):
                synonyms_str = ", ".join(str(item) for item in combined_keywords)
                new_question_sentiment_keywords = new_question_sentiment_keywords.replace("[synonyms]", synonyms_str)
            else:
                new_question_sentiment_keywords = new_question_sentiment_keywords.replace("[synonyms]", str(orgName) if orgName else "")
            new_question_sentiment_keywords = new_question_sentiment_keywords.replace("[positiveRatio]", str(positiveRatio)).replace("[negativeRatio]", str(negativeRatio))
            
            result_sentiment_keywords = self.chat_ollama._client.generate(
                                    model=CONF.OLLAMA_MODEL,
                                    prompt=new_question_sentiment_keywords)
            is_success, result_sentiment_keywords_json = self.json_load(result_sentiment_keywords, mycontents_logger) 
            
            # assemble sentiment
            sentiment_separated_success = self.assemble_sentiment_to_ollamaModel_v2(queueContent, orgName, result_sentiment_ratio, result_sentiment_ratio_json, result_sentiment_reason, result_sentiment_reason_json, result_sentiment_keywords, result_sentiment_keywords_json, contentsMetaResult, mycontents_logger) 
            contentsMetaResult.sentimentSucYN = "Y" if sentiment_separated_success else "N"
            sentiment_end = time.time()
            mycontents_logger.info(f"평판분석 소요시간 : {sentiment_end-sentiment_start} 초 소요")

            contentsMetaResult.metaSucYN = "Y" if summary_success else "N"
            contentsMetaResult.metaAnalyzeDt = datetime.now(timezone.utc)  
            
            return True, contentsMetaResult, result_summary, None, None 

        except Exception as e: 
            tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            mycontents_logger.error(f"Exception occurred: {e}, Args: {e.args}, Traceback: {tb_str}")

            error_ollamaMetaResult = self.to_error_ollamaModel() 
            return False, None, None, None, error_ollamaMetaResult


class ModelComparisonAnalyzer:
    """
    두 모델로 비교 분석하는 클래스
    
    이 클래스는 contents_queue에서 URL을 가져와서 스크래핑한 후,
    두 개의 다른 Ollama 모델로 각각 분석을 수행하고 결과를 비교합니다.
    """
    
    def __init__(self):
        """
        초기화 함수
        - 필요한 서비스 객체들을 생성하고 설정합니다.
        - 분석에 필요한 키워드와 기관 목록을 준비합니다.
        """
        # 로거 설정: 분석 결과를 기록할 로거 생성
        # Logger.docker_scraping_result_logger_name: 로그 파일 이름 (docker_scraping_result.log)
        self.logger = Logger().setup_logger(Logger.docker_scraping_result_logger_name)
        
        # MongoDB 서비스 객체들 생성
        # ContentsQueueService: contents_queue 컬렉션에서 URL 목록을 가져오는 서비스
        self.queue_service = ContentsQueueService()
        # ContentsService: contents 컬렉션(최종 저장소)에 접근하는 서비스
        self.contents_service = ContentsService()
        # ContentsOrgService: 기관 정보를 조회하는 서비스
        self.org_service = ContentsOrgService()
        
        # 스크래핑 도구들
        # TrafilauraScraper: AI 기반 웹 스크래퍼 (주로 사용)
        self.trafilaura_scraper = TrafilauraScraper()
        # WebLoaderV3: 대체 스크래퍼 (Trafilaura 실패 시 사용)
        self.web_loader = WebLoaderV3()
        
        # 키워드 목록 준비
        # PredefineKeywordService: 사전 정의된 키워드 목록을 가져오는 서비스
        # getKeywordList(): DB에서 키워드 리스트를 가져옴 (예: ["에너지", "전력", "재생에너지", ...])
        keywords = PredefineKeywordService().getKeywordList()
        # 분석 시 사용할 키워드를 쉼표로 구분한 문자열로 변환
        # 예: "에너지, 전력, 재생에너지, ..."
        self.keyword_name_list = ", ".join(keywords) if isinstance(keywords, list) else str(keywords)
        
        # 기관 목록 준비
        # find_all(): 모든 기관 정보를 가져옴 (예: [ContentsOrgVO, ...])
        all_orgs = self.org_service.find_all()
        # 기관 이름만 추출하여 쉼표로 구분한 문자열로 변환
        # 예: "한국전력공사, 산업통상자원부, ..."
        self.org_name_list = ", ".join([org.orgName for org in all_orgs if org.orgName])
        
        # 비교할 모델 목록
        # Ollama에서 사용할 두 모델의 이름
        self.models_to_compare = [
            "gpt-oss:20b",  # 첫 번째 비교 모델
            "llama-3-Korean-Bllossom-8B-Q4_K_M:latest"  # 두 번째 비교 모델
        ]
        
        # 결과 저장용 리스트 (메모리에 임시 저장)
        self.comparison_results = []
    
    def select_queue_items(self, count: int = 3) -> List[ContentsQueueVO]:
        """
        contents_queue 컬렉션에서 지정된 개수만큼 항목을 선택합니다.
        
        Args:
            count: 선택할 항목의 개수 (기본값: 3)
            
        Returns:
            List[ContentsQueueVO]: 선택된 큐 항목들의 리스트
            각 ContentsQueueVO는 다음 정보를 포함:
            - url: 기사 URL
            - title: 기사 제목
            - contentOrgId: 기관 ID (예: "A0010")
            - cateId: 카테고리 ID (예: "B0010")
            - collectDt: 수집 일시
            
        동작:
            1. MongoDB의 contents_queue 컬렉션에서 모든 항목 조회
            2. collectDt(수집일시) 기준으로 최신순 정렬
            3. 최신 항목부터 count개만 선택
        """
        self.logger.info(f"📋 contents_queue에서 {count}개 항목 선택 중...")
        
        # find_all(): MongoDB contents_queue 컬렉션의 모든 문서를 조회
        # 반환값: ContentsQueueVO 객체들의 리스트
        all_items = self.queue_service.find_all()
        
        if not all_items or len(all_items) == 0:
            self.logger.error("❌ contents_queue가 비어 있습니다.")
            return []
        
        # 최신 항목부터 정렬 (collectDt 기준)
        # collectDt: 기사가 수집된 날짜/시간
        # reverse=True: 내림차순 (최신이 먼저)
        sorted_items = sorted(
            all_items,
            key=lambda x: x.collectDt if hasattr(x, 'collectDt') and x.collectDt else datetime.min,
            reverse=True
        )
        
        # 최신 항목부터 count개만 선택
        selected = sorted_items[:count]
        
        # 선택된 항목 정보 로그 출력
        self.logger.info(f"✅ {len(selected)}개 항목 선택 완료:")
        for idx, item in enumerate(selected, 1):
            self.logger.info(f"   {idx}. {item.url}")
            self.logger.info(f"      제목: {item.title if hasattr(item, 'title') else 'N/A'}")
            self.logger.info(f"      수집일: {item.collectDt if hasattr(item, 'collectDt') else 'N/A'}")
        
        return selected
    
    def scrape_content(self, queue_content: ContentsQueueVO) -> tuple:
        """
        URL에서 기사 본문을 스크래핑합니다.
        
        Args:
            queue_content: 스크래핑할 URL 정보가 담긴 ContentsQueueVO 객체
            
        Returns:
            tuple: (성공여부, 제목, 본문텍스트)
            - 성공 시: (True, "기사 제목", "기사 본문 전체 텍스트...")
            - 실패 시: (False, None, None)
            
        동작:
            1. TrafilauraScraper로 먼저 시도 (AI 기반 스크래퍼, 더 정확함)
            2. 실패 시 WebLoaderV3로 재시도 (Selenium 기반, 대체 방법)
            3. 둘 다 실패하면 False 반환
        """
        self.logger.info(f"📖 스크래핑 시작: {queue_content.url}")
        
        try:
            # Trafilaura로 스크래핑 시도
            # get_newbody(url): URL에서 기사 본문을 추출
            # 반환값: (성공여부, 제목, 본문텍스트)
            is_success, title, text = self.trafilaura_scraper.get_newbody(queue_content.url)
            
            if is_success and text:
                self.logger.info(f"✅ 스크래핑 성공 (길이: {len(text)}자)")
                return True, title, text
            else:
                # Trafilaura 실패 시 WebLoader로 재시도
                self.logger.warning(f"⚠️  Trafilaura 스크래핑 실패, WebLoader 시도...")
                
                # get_driver(): Selenium WebDriver 생성 (Chrome 브라우저)
                driver = get_driver()
                try:
                    # WebLoader로 스크래핑 시도
                    # loadContents(): Selenium으로 웹페이지 접속하여 본문 추출
                    # 주의: 실제로는 contentsOrgVO, contentsOrgCategory가 필요하지만
                    #       여기서는 간단히 None으로 전달 (에러 가능성 있음)
                    is_success, text = self.web_loader.loadContents(
                        None, None, None, driver
                    )
                    if is_success and text:
                        return True, queue_content.title if hasattr(queue_content, 'title') else None, text
                except Exception as e:
                    self.logger.warning(f"WebLoader 스크래핑 실패: {e}")
                finally:
                    # WebDriver 종료 (리소스 해제)
                    driver.quit()
                
                return False, None, None
                
        except Exception as e:
            self.logger.error(f"❌ 스크래핑 오류: {e}")
            self.logger.error(traceback.format_exc())
            return False, None, None
    
    def analyze_with_model(self, queue_content: ContentsQueueVO, content_text: str, model_name: str):
        """
        지정된 Ollama 모델로 기사 본문을 분석합니다.
        
        Args:
            queue_content: 큐 항목 정보 (기관ID, 카테고리ID 등 포함)
            content_text: 분석할 기사 본문 텍스트
            model_name: 사용할 Ollama 모델 이름 (예: "gpt-oss:20b")
            
        Returns:
            dict: 분석 결과 딕셔너리
            {
                "success": True/False,
                "model": "모델이름",
                "result": ContentsMetaResult 객체 (성공 시),
                "summary": 요약 정보,
                "sentiment": 감성 분석 정보,
                "error": 에러 정보 (실패 시)
            }
            
        동작:
            1. 현재 설정된 모델을 백업
            2. CONF.OLLAMA_MODEL을 지정된 모델로 변경
            3. AnalysisOllamaGenerateCall 초기화 (이때 새 모델 사용)
            4. analysis_main() 실행하여 5가지 분석 수행:
               - 키워드 관련성 검증
               - 요약 생성 (짧은/긴 요약)
               - 감성 비율 분석
               - 감성 이유 설명
               - 긍정/부정 키워드 추출
            5. 원래 모델 설정으로 복원
            
        주의:
            CONF.OLLAMA_MODEL을 변경하면 AnalysisOllamaGenerateCall이
            초기화될 때 해당 모델을 사용합니다.
        """
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"🤖 모델: {model_name}로 분석 시작")
        self.logger.info(f"{'='*60}")
        
        # 원래 모델 백업 (나중에 복원하기 위해)
        # CONF.OLLAMA_MODEL: config.py에 정의된 전역 모델 설정
        original_model = CONF.OLLAMA_MODEL
        
        try:
            # 모델 변경: 전역 설정을 임시로 변경
            CONF.OLLAMA_MODEL = model_name
            
            # # AnalysisOllamaGenerateCall.__init__()에서 CONF.OLLAMA_MODEL을 읽어서
            # # ChatOllama 객체를 생성하므로, 여기서 설정한 모델이 사용됨
            # analyzer = AnalysisOllamaGenerateCall()

            # 분석기 초기화 (새 모델로)
            # CustomAnalysisOllamaGenerateCall은 format="json" 없이 작동
            analyzer = CustomAnalysisOllamaGenerateCall()
            
            # 분석 실행
            # analysis_main(): Ollama 모델을 사용하여 기사를 분석하는 메인 함수
            # - content: 분석할 기사 본문
            # - pred_keyword_list: 사전 정의된 키워드 목록 (쉼표로 구분된 문자열)
            # - org_name_list: 기관 이름 목록 (쉼표로 구분된 문자열)
            # - mycontents_logger: 로그 기록용 로거
            # - queueContent: 큐 항목 정보 (기관ID, 카테고리ID 등)
            # 반환값:
            #   - success: 분석 성공 여부 (bool)
            #   - result: ContentsMetaResult 객체 (키워드, 요약, 감성 분석 결과 포함)
            #   - summary: 요약 정보
            #   - sentiment: 감성 분석 정보
            #   - error: 에러 정보 (실패 시)
            success, result, summary, sentiment, error = analyzer.analysis_main(
                content=content_text,
                pred_keyword_list=self.keyword_name_list,
                org_name_list=self.org_name_list,
                mycontents_logger=self.logger,
                queueContent=queue_content
            )
            
            if success and result:
                self.logger.info(f"✅ {model_name} 분석 완료")
                return {
                    "success": True,
                    "model": model_name,
                    "result": result,  # ContentsMetaResult 객체
                    "summary": summary,
                    "sentiment": sentiment
                }
            else:
                self.logger.error(f"❌ {model_name} 분석 실패")
                return {
                    "success": False,
                    "model": model_name,
                    "error": error
                }
                
        except Exception as e:
            self.logger.error(f"❌ {model_name} 분석 중 오류: {e}")
            self.logger.error(traceback.format_exc())
            return {
                "success": False,
                "model": model_name,
                "error": str(e)
            }
        finally:
            # 원래 모델로 복원 (다음 분석을 위해)
            CONF.OLLAMA_MODEL = original_model
    
    def save_comparison_result(self, queue_content: ContentsQueueVO, scraped_data: dict, analysis_results: List[dict]):
        """
        두 모델의 분석 결과를 MongoDB에 저장합니다.
        
        Args:
            queue_content: 큐 항목 정보
            scraped_data: 스크래핑된 데이터 {"title": "...", "text": "..."}
            analysis_results: 각 모델의 분석 결과 리스트
                [
                    {"success": True, "model": "gpt-oss:20b", "result": ContentsMetaResult, ...},
                    {"success": True, "model": "llama-3-...", "result": ContentsMetaResult, ...}
                ]
                
        저장 위치:
            MongoDB 컬렉션: "llm_model_comparison"
            
        저장 형식:
            {
                "queueId": "큐 항목 ID",
                "url": "기사 URL",
                "title": "기사 제목",
                "contentOrgId": "기관 ID",
                "categoryId": "카테고리 ID",
                "scrapedAt": 수집 일시,
                "scrapedContent": {"title": "...", "contentLength": 1234},
                "analysisResults": [
                    {
                        "model": "gpt-oss:20b",
                        "success": True,
                        "keywords": [...],
                        "shortSummary": "...",
                        "longSummary": "...",
                        "sentiments": [...]
                    },
                    ...
                ],
                "createdAt": 생성 일시
            }
        """
        from ksubscribe_share.db.mongoManager import MongoManager
        
        # MongoManager: MongoDB 연결을 관리하는 싱글톤 객체
        mongo_manager = MongoManager()
        # getCollection(): MongoDB 컬렉션 객체 가져오기
        # "llm_model_comparison": 비교 결과를 저장할 컬렉션 이름
        collection = mongo_manager.getCollection("llm_model_comparison")
        
        # MongoDB에 저장할 문서 구조 생성
        comparison_doc = {
            "queueId": str(queue_content._id),  # 큐 항목의 MongoDB ObjectId
            "url": queue_content.url,  # 기사 URL
            "title": scraped_data.get("title") or (queue_content.title if hasattr(queue_content, 'title') else ""),
            "contentOrgId": queue_content.contentOrgId if hasattr(queue_content, 'contentOrgId') else "",  # 기관 ID
            "categoryId": queue_content.cateId if hasattr(queue_content, 'cateId') else "",  # 카테고리 ID
            "scrapedAt": datetime.now(timezone.utc),  # 스크래핑 일시
            "scrapedContent": {
                "title": scraped_data.get("title"),
                "contentLength": len(scraped_data.get("text", ""))  # 본문 길이 (문자 수)
            },
            "analysisResults": [],  # 각 모델의 분석 결과가 여기에 추가됨
            "createdAt": datetime.now(timezone.utc)  # 문서 생성 일시
        }
        
        # 각 모델의 분석 결과를 문서에 추가
        for analysis in analysis_results:
            if analysis.get("success") and analysis.get("result"):
                # 분석 성공한 경우
                result = analysis["result"]  # ContentsMetaResult 객체
                meta = result.contentsMeta  # ContentsMeta 객체 (분석 결과 포함)
                
                # 분석 결과 데이터 추출
                analysis_data = {
                    "model": analysis["model"],  # 모델 이름
                    "success": True,
                    "keywords": meta.keywords if meta and meta.keywords else [],  # AI가 추출한 키워드 리스트
                    "predKeywords": meta.predKeywords if meta and meta.predKeywords else {},  # 사전 정의 키워드와의 유사도
                    "shortSummary": meta.shortSummary if meta and meta.shortSummary else "",  # 한 줄 요약
                    "longSummary": meta.longSummary if meta and meta.longSummary else "",  # 세 줄 요약
                    "sentiments": []  # 감성 분석 결과 리스트
                }
                
                # 감성 분석 결과 추출
                # meta.sentiments: SentimentInfo 객체들의 리스트
                if meta and meta.sentiments:
                    for sent in meta.sentiments:
                        analysis_data["sentiments"].append({
                            "orgName": sent.orgName if hasattr(sent, 'orgName') else "",  # 기관 이름
                            "orgId": sent.orgId if hasattr(sent, 'orgId') else "",  # 기관 ID
                            "positiveRatio": sent.positiveRatio if hasattr(sent, 'positiveRatio') else 0,  # 긍정 비율 (%)
                            "negativeRatio": sent.negativeRatio if hasattr(sent, 'negativeRatio') else 0,  # 부정 비율 (%)
                            "neutralRatio": sent.neutralRatio if hasattr(sent, 'neutralRatio') else 0,  # 중립 비율 (%)
                            "reason": sent.reason if hasattr(sent, 'reason') else "",  # 감성 판단 근거
                            "positiveKeywords": getattr(sent, 'positiveKeywords', []),  # 긍정 키워드 리스트
                            "negativeKeywords": getattr(sent, 'negativeKeywords', [])  # 부정 키워드 리스트
                        })
                
                comparison_doc["analysisResults"].append(analysis_data)
            else:
                # 분석 실패한 경우
                comparison_doc["analysisResults"].append({
                    "model": analysis["model"],
                    "success": False,
                    "error": str(analysis.get("error", "Unknown error"))  # 에러 메시지
                })
        
        # MongoDB에 저장
        try:
            result = collection.insert_one(comparison_doc)
            self.logger.info(f"✅ 비교 결과 저장 완료: {result.inserted_id}")
            return result.inserted_id
        except Exception as e:
            self.logger.error(f"❌ 비교 결과 저장 실패: {e}")
            self.logger.error(traceback.format_exc())
            return None
    
    def print_comparison_summary(self, queue_content: ContentsQueueVO, analysis_results: List[dict]):
        """
        두 모델의 분석 결과를 콘솔에 비교하여 출력합니다.
        
        Args:
            queue_content: 큐 항목 정보
            analysis_results: 각 모델의 분석 결과 리스트
            
        출력 형식:
            ================================================================================
            📊 비교 분석 결과 요약
            ================================================================================
            URL: https://...
            제목: 기사 제목
            --------------------------------------------------------------------------------
            
            🤖 모델: gpt-oss:20b
               ✅ 분석 성공
            
               📝 짧은 요약:
               요약 내용...
            
               🔑 키워드:
               키워드1, 키워드2, ...
            
               💭 감성 분석:
               - 긍정: 70%
               - 부정: 10%
               - 중립: 20%
            
            🤖 모델: llama-3-Korean-Bllossom-8B-Q4_K_M:latest
               ✅ 분석 성공
               ...
            ================================================================================
        """
        print("\n" + "="*80)
        print(f"📊 비교 분석 결과 요약")
        print("="*80)
        print(f"URL: {queue_content.url}")
        print(f"제목: {queue_content.title if hasattr(queue_content, 'title') else 'N/A'}")
        print("-"*80)
        
        # 각 모델의 분석 결과를 순회하며 출력
        for analysis in analysis_results:
            if not analysis.get("success"):
                # 분석 실패한 경우
                print(f"\n❌ {analysis['model']}: 분석 실패")
                print(f"   오류: {analysis.get('error', 'Unknown')}")
                continue
            
            # 분석 성공한 경우
            result = analysis["result"]  # ContentsMetaResult 객체
            meta = result.contentsMeta  # ContentsMeta 객체 (분석 결과 포함)
            
            print(f"\n🤖 모델: {analysis['model']}")
            print(f"   ✅ 분석 성공")
            
            if meta:
                # 짧은 요약 출력 (200자 제한)
                if meta.shortSummary:
                    summary_text = meta.shortSummary
                    if len(summary_text) > 200:
                        summary_text = summary_text[:200] + "..."
                    print(f"\n   📝 짧은 요약:")
                    print(f"   {summary_text}")
                
                # 키워드 출력 (최대 5개)
                if meta.keywords:
                    print(f"\n   🔑 키워드:")
                    keywords_display = ', '.join(meta.keywords[:5])
                    print(f"   {keywords_display}")
                
                # 감성 분석 결과 출력
                # meta.sentiments: SentimentInfo 객체들의 리스트
                if meta.sentiments and len(meta.sentiments) > 0:
                    sent = meta.sentiments[0]  # 첫 번째 감성 분석 결과 사용
                    print(f"\n   💭 감성 분석:")
                    print(f"   - 긍정: {sent.positiveRatio if hasattr(sent, 'positiveRatio') else 0}%")
                    print(f"   - 부정: {sent.negativeRatio if hasattr(sent, 'negativeRatio') else 0}%")
                    print(f"   - 중립: {sent.neutralRatio if hasattr(sent, 'neutralRatio') else 0}%")
        
        print("\n" + "="*80)
    
    def process_queue_items(self, queue_items: List[ContentsQueueVO]):
        """
        선택된 큐 항목들을 순차적으로 처리합니다.
        
        각 항목에 대해:
        1. 스크래핑 (URL에서 본문 추출)
        2. 두 모델로 각각 분석
        3. 결과 비교 출력
        4. MongoDB에 저장
        
        Args:
            queue_items: 처리할 큐 항목들의 리스트
        """
        for idx, queue_content in enumerate(queue_items, 1):
            self.logger.info(f"\n{'#'*80}")
            self.logger.info(f"처리 중: {idx}/{len(queue_items)}")
            self.logger.info(f"{'#'*80}")
            
            # 1. 스크래핑: URL에서 기사 본문 추출
            is_success, title, text = self.scrape_content(queue_content)
            
            if not is_success or not text:
                # 스크래핑 실패 시 해당 항목 건너뛰기
                self.logger.error(f"❌ 스크래핑 실패, 건너뜀: {queue_content.url}")
                continue
            
            # 스크래핑된 데이터 정리
            scraped_data = {
                "title": title or (queue_content.title if hasattr(queue_content, 'title') else ""),
                "text": text  # 기사 본문 전체 텍스트
            }
            
            # 2. 각 모델로 분석
            # self.models_to_compare = ["gpt-oss:20b", "llama-3-Korean-Bllossom-8B-Q4_K_M:latest"]
            analysis_results = []
            for model_name in self.models_to_compare:
                # 각 모델로 동일한 본문을 분석
                result = self.analyze_with_model(queue_content, text, model_name)
                analysis_results.append(result)
            
            # 3. 결과 비교 출력: 콘솔에 두 모델의 분석 결과를 나란히 출력
            self.print_comparison_summary(queue_content, analysis_results)
            
            # 4. 결과 저장: MongoDB의 llm_model_comparison 컬렉션에 저장
            self.save_comparison_result(queue_content, scraped_data, analysis_results)
            
            # 메모리에 결과 저장 (나중에 참조 가능)
            self.comparison_results.append({
                "queue_content": queue_content,
                "scraped_data": scraped_data,
                "analysis_results": analysis_results
            })
    
    def run(self, count: int = 3):
        """
        메인 실행 함수: 전체 비교 분석 프로세스를 실행합니다.
        
        실행 순서:
        1. contents_queue에서 count개 항목 선택
        2. 각 항목에 대해 스크래핑 → 두 모델로 분석 → 결과 저장
        3. 최종 요약 출력
        
        Args:
            count: 처리할 큐 항목의 개수 (기본값: 3)
        """
        self.logger.info("="*80)
        self.logger.info("🚀 모델 비교 분석 시작")
        self.logger.info("="*80)
        self.logger.info(f"비교할 모델: {', '.join(self.models_to_compare)}")
        self.logger.info(f"선택할 항목 수: {count}")
        
        # 1. 큐에서 항목 선택
        # contents_queue 컬렉션에서 최신 count개 항목 가져오기
        queue_items = self.select_queue_items(count)
        
        if not queue_items:
            self.logger.error("❌ 처리할 항목이 없습니다.")
            return
        
        # 2. 각 항목 처리
        # 스크래핑 → 분석 → 저장
        self.process_queue_items(queue_items)
        
        # 3. 최종 요약
        self.logger.info("\n" + "="*80)
        self.logger.info("✅ 모든 비교 분석 완료")
        self.logger.info("="*80)
        self.logger.info(f"처리된 항목 수: {len(self.comparison_results)}")
        self.logger.info(f"\n비교 결과는 MongoDB 'llm_model_comparison' 컬렉션에 저장되었습니다.")
        self.logger.info(f"조회 방법:")
        self.logger.info(f"  db.llm_model_comparison.find().pretty()")


def main():
    """
    프로그램 진입점 (Entry Point)
    
    명령행 인자를 파싱하고 ModelComparisonAnalyzer를 실행합니다.
    
    사용 예:
        python3 compare_models_from_queue.py
        python3 compare_models_from_queue.py --count 5
    """
    import argparse
    
    # 명령행 인자 파서 생성
    parser = argparse.ArgumentParser(description='두 모델로 큐 항목 비교 분석')
    # --count 옵션: 처리할 큐 항목 수 지정 (기본값: 3)
    parser.add_argument('--count', type=int, default=3, help='처리할 큐 항목 수 (기본값: 3)')
    
    # 명령행 인자 파싱
    args = parser.parse_args()
    
    try:
        # 분석기 객체 생성 및 실행
        analyzer = ModelComparisonAnalyzer()
        analyzer.run(count=args.count)
    except KeyboardInterrupt:
        # Ctrl+C로 중단된 경우
        print("\n⚠️  사용자에 의해 중단되었습니다.")
    except Exception as e:
        # 예상치 못한 오류 발생 시
        print(f"\n❌ 오류 발생: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()

