#from langchain_community.chat_models import ChatOllama
import requests
from openai import OpenAI
import traceback
import pandas as pd 
from datetime import datetime, timezone
import logging 
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
#from langchain_ollama.chat_models import ChatOllama 
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    BaseMessage,
    BaseMessageChunk,
    HumanMessage,
    convert_to_messages,
    message_chunk_to_message,
) 
import json
from typing import Tuple, Dict,List
from ollama import GenerateResponse
import time
import re
import ast
import tiktoken 

from ksubscribe_share.logger import Logger
from ksubscribe_server.models.contentsMetaResult import ContentsMetaResult
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsMeta, SentimentInfo
from ksubscribe_share.db.dbmodelV2.llmAnalysisMeta import LLMAnalysisMeta
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsMeta
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.service.contentsQueueService import ContentsQueueService
# 20251113 MariaDB 미사용으로 주석처리
# from ksubscribe_share.db.service.articleKeywordsService import ArticleKeywordsService
# from ksubscribe_share.db.mariadb_model.articleKeywordsVO import ArticleKeywordsVO
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO

from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.predefineKeywordService import PredefineKeywordService
from ksubscribe_share.db.service.contentsService import ContentsService
from ksubscribe_server.similarity.simularity_check import SimularityChecker
from ksubscribe_server.analysis.analysis_ollama_base import AnalysisOllamaBase
from ksubscribe_server.analysis.analysis_ollama_base2 import AnalysisOllamaBase2
from ksubscribe_server.analysis.analysis_ollama_base3 import AnalysisOllamaBase3
import os
import time
import traceback
import ksubscribe_share.config as CONF
from pydantic import BaseModel, PrivateAttr, model_validator
# 20251113 MariaDB 미사용으로 주석처리
# from ksubscribe_share.db.service.articleKeywordsService import ArticleKeywordsService
# from ksubscribe_share.db.service.articleSummaryService import ArticlesSummaryService
# from ksubscribe_share.db.mariadb_model.articleKeywordsVO import ArticleKeywordsVO
# from ksubscribe_share.db.mariadb_model.articleSummaryVO import ArticlesSummaryVO

def count_tokens(text: str, model: str = "llama3"):
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))
 
class AnalysisOllamaGenerateCall(AnalysisOllamaBase):

    def __init__(self, yaml_path: str = None):
        # 부모 클래스에 YAML 경로 전달
        super().__init__(yaml_path=yaml_path)
        
        self.chat_ollama =  ChatOllama(model = CONF.OLLAMA_MODEL,
                                       base_url= CONF.OLLAMA_URL, 
                                       format=(None if "gpt-oss" in CONF.OLLAMA_MODEL else "json")) 
        #self.chat_ollama._client = PrivateAttr(default=None)  # type: ignore
        
        self.keywords = PredefineKeywordService().getKeywordList()
        # 202504101 임형준 : ollama client timeout 조건 추가
        # 2025-11-13 AI: timeout 20초 → 120초 → 180초로 증가 (긴 문서 분석 지원, 감성분석 타임아웃 방지)
        self.chat_ollama.client_kwargs["timeout"] = 180
        self.chat_ollama._set_clients()
        self.contentsQueueService = ContentsQueueService()
        
    #25.03.13 당문간 _test함수 유지     
    def analysis_main_test(self, title,content, pred_keyword_list, org_name_list, mycontents_logger:logging.Logger): #-> tuple[bool, ContentsMetaResult]:
        """Ollama 연계하여 분석 ( 요약분석, 평판분석 )
        """        
        try: 
            contentsMetaResult = ContentsMetaResult()
            contentsMetaResult.contentsMeta.method = "ollama"
            summary_start = time.time()
            
            #pred_keyword_list = [item + " 기술"  for item in pred_keyword_list]
            
            new_question_summary = self.question_summary.replace("pred_keywords_from_db", pred_keyword_list).replace("[contents]",content)
            result_summary = self.chat_ollama._client.generate(
                                    model=CONF.OLLAMA_MODEL,
                                    prompt=new_question_summary,
                                    format=(None if "gpt-oss" in CONF.OLLAMA_MODEL else "json"))
            
            summary_end = time.time()
            _,data = self.json_load(result_summary, mycontents_logger) 
            SimularityChecker().best_keyword_of_summary(data["short_summary"],self.keywords)
            SimularityChecker().best_keyword_of_summary(data["long_summary"],self.keywords)
            
            #print(result_summary.response) 
            return True, contentsMetaResult,result_summary,None  ,None  

        except Exception as e: 
            #trackback logging
            tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            mycontents_logger.error(f"Exception occurred: {e}, Args: {e.args}, Traceback: {tb_str}")

            error_ollamaMetaResult :ContentsMetaResult = self.to_error_ollamaModel() 
            return False, None, None, None, error_ollamaMetaResult


    def analysis_main(self, content, pred_keyword_list, org_name_list, mycontents_logger:logging.Logger, queueContent:ContentsQueueVO): #-> tuple[bool, ContentsMetaResult]:
        """Ollama 연계하여 분석 ( 요약분석, 평판분석 )
        """        
        try: 
            contentsMetaResult = ContentsMetaResult()
            contentsMetaResult.contentsMeta.method = "ollama"
            
            # orgId로 기관 이름 + 약어 등 조회 (Moved to top for usage in all prompts)
            orgId = queueContent.contentOrgId    
            orgName, combined_keywords = ContentsOrgService().getOrgNameAndKeywords(queueContent.contentOrgId)
            mycontents_logger.info(f"🔍 [Debug] orgId: {orgId}, orgName: {orgName}, combined_keywords: {combined_keywords}")

            # 사전질의(주어진 db 키워드와 ai추출 키워드를 추출 및 비교)를 통한 키워드 검증로직 추가 20250429 mcst
            # verify_start = time.time() # Removed timing
            pre_question_verify = self.question_verify.replace("pred_keywords_from_db", pred_keyword_list).replace("[contents]",content)
            result_verify = self.chat_ollama._client.generate(
                                    model=CONF.OLLAMA_MODEL,
                                    prompt=pre_question_verify,
                                    format=(None if "gpt-oss" in CONF.OLLAMA_MODEL else "json"))
            is_success_keywords, result_verify_json = self.json_load(result_verify, mycontents_logger)  
            related = result_verify_json['related']  # True : 관련성 있음, False : 관련성 없음
            
            #20251013 리자: 프롬프트 2)에서 키워드 삭제에 따른 변경:
            ai_keywords = result_verify_json["ai_keyword"]
                        
            # verify_end = time.time() # Removed timing
            # mycontents_logger.info(f"분석대상 사전검증 소요시간 : {verify_end-verify_start} 초 소요")
                        
            # summary_start = time.time() # Removed timing
            #pred_keyword_list = [item + " 기술"  for item in pred_keyword_list]
            # 
            new_question_summary = self.question_summary.replace("pred_keywords_from_db", pred_keyword_list).replace("[contents]",content)
            result_summary = self.chat_ollama._client.generate(
                                    model=CONF.OLLAMA_MODEL,
                                    prompt=new_question_summary,
                                    format=(None if "gpt-oss" in CONF.OLLAMA_MODEL else "json"))
            
            # summary_end = time.time() # Removed timing
            is_success, result_summary_json = self.json_load(result_summary, mycontents_logger)  
            
            # pred_keywords = SimularityChecker().best_keyword_of_summary(result_summary_json["short_summary"],self.keywords)
            # db키워드와 관련성이 없으면 키워드 추출하지 않음
            if related:
                keywords_verify = result_verify_json['reason']  # db_keyword_list 중 관련 키워드 최대 3개
                if isinstance(keywords_verify, list) and len(keywords_verify) > 0:
                    pred_keywords = SimularityChecker().best_keyword_of_summary(result_summary_json["short_summary"],keywords_verify) # 전체 키워드가 아닌 검증된 키워들 통해 유사도 검증 20250429 mcst
                    mycontents_logger.info(f"🔍 [Debug] keywords_verify: {keywords_verify}")
                    mycontents_logger.info(f"🔍 [Debug] pred_keywords: {pred_keywords}")
                else :
                    pred_keywords = None
                    mycontents_logger.info(f"키워드 추출대상 아님")        
            else:
                pred_keywords = None
                mycontents_logger.info(f"키워드 추출대상 아님")
                
            #LIZA: add article keywords (25.10.02)
            try:
                article_keywords = result_verify_json["ai_keyword"]
            except Exception as e:
                article_keywords = None
                mycontents_logger.info(f"ai_keyword 없음")
            
            # 20251113 MariaDB 미사용으로 주석처리 (MongoDB에만 저장)
            # article = ArticleKeywordsVO(
            #     orgId=queueContent.contentOrgId,
            #     keywords=pred_keywords,
            #     ai_keywords=article_keywords,
            #     success=is_success_keywords,
            #     url=queueContent.url
            # )

            # try:
            #     inserted_id = ArticleKeywordsService.insert_one(article)
            #     mycontents_logger.info(f"ArticleKeywords inserted successfully - row id: {inserted_id}")
            # except Exception as e:
            #     mycontents_logger.error(f"Failed to insert ArticleKeywords to MariaDB: {e}")
            #     mycontents_logger.info("Continuing analysis despite MariaDB error...")

        
            
            summary_success = self.summary_to_ollamaModel_v2(result_summary, result_summary_json, contentsMetaResult, pred_keywords, ai_keywords, mycontents_logger) 
            contentsMetaResult.summarySucYN = "Y" if summary_success else "N"
            # mycontents_logger.info(f"요약분석 소요시간 : {summary_end-summary_start} 초 소요") # Removed timing
            
            # 20251113 MariaDB 미사용으로 주석처리 (MongoDB에만 저장)
            # article_sum = ArticlesSummaryVO(
            #     orgId=queueContent.contentOrgId,
            #     long_summary=result_summary_json["long_summary"],
            #     short_summary=result_summary_json["short_summary"],
            #     success=summary_success,
            #     url=queueContent.url
            # )
            
            # try:
            #     inserted_id = ArticlesSummaryService.insert_one(article_sum)
            #     mycontents_logger.info(f"ArticlesSummary inserted successfully - row id: {inserted_id}")
            # except Exception as e:
            #     mycontents_logger.error(f"Failed to insert ArticlesSummary to MariaDB: {e}")
            #     mycontents_logger.info("Continuing analysis despite MariaDB error...")

            # # [New Feature] Long Detail Summary Formats (5 Candidates)
            # # Format 1
            # new_question_longdetail_1 = self.question_longdetail_summary_format1.replace("[organization]", str(orgName) if orgName else "").replace("[contents]",content)
            # result_longdetail_1 = self.chat_ollama._client.generate(
            #                         model=CONF.OLLAMA_MODEL,
            #                         prompt=new_question_longdetail_1,
            #                         format=(None if "gpt-oss" in CONF.OLLAMA_MODEL else "json"))
            # _, result_longdetail_1_json = self.json_load(result_longdetail_1, mycontents_logger)
            # contentsMetaResult.contentsMeta.longDetailSummaryFormat1 = result_longdetail_1_json.get("longDetailSummary")

            # # Format 2
            # new_question_longdetail_2 = self.question_longdetail_summary_format2.replace("[organization]", str(orgName) if orgName else "").replace("[contents]",content)
            # result_longdetail_2 = self.chat_ollama._client.generate(
            #                         model=CONF.OLLAMA_MODEL,
            #                         prompt=new_question_longdetail_2,
            #                         format=(None if "gpt-oss" in CONF.OLLAMA_MODEL else "json"))
            # _, result_longdetail_2_json = self.json_load(result_longdetail_2, mycontents_logger)
            # contentsMetaResult.contentsMeta.longDetailSummaryFormat2 = result_longdetail_2_json.get("longDetailSummary")

            # # Format 3
            # new_question_longdetail_3 = self.question_longdetail_summary_format3.replace("[organization]", str(orgName) if orgName else "").replace("[contents]",content)
            # result_longdetail_3 = self.chat_ollama._client.generate(
            #                         model=CONF.OLLAMA_MODEL,
            #                         prompt=new_question_longdetail_3,
            #                         format=(None if "gpt-oss" in CONF.OLLAMA_MODEL else "json"))
            # _, result_longdetail_3_json = self.json_load(result_longdetail_3, mycontents_logger)
            # contentsMetaResult.contentsMeta.longDetailSummaryFormat3 = result_longdetail_3_json.get("longDetailSummary")

            # # Format 4
            # new_question_longdetail_4 = self.question_longdetail_summary_format4.replace("[organization]", str(orgName) if orgName else "").replace("[contents]",content)
            # result_longdetail_4 = self.chat_ollama._client.generate(
            #                         model=CONF.OLLAMA_MODEL,
            #                         prompt=new_question_longdetail_4,
            #                         format=(None if "gpt-oss" in CONF.OLLAMA_MODEL else "json"))
            # _, result_longdetail_4_json = self.json_load(result_longdetail_4, mycontents_logger)
            # contentsMetaResult.contentsMeta.longDetailSummaryFormat4 = result_longdetail_4_json.get("longDetailSummary")

            # # Format 5
            # new_question_longdetail_5 = self.question_longdetail_summary_format5.replace("[organization]", str(orgName) if orgName else "").replace("[contents]",content)
            # result_longdetail_5 = self.chat_ollama._client.generate(
            #                         model=CONF.OLLAMA_MODEL,
            #                         prompt=new_question_longdetail_5,
            #                         format=(None if "gpt-oss" in CONF.OLLAMA_MODEL else "json"))
            # _, result_longdetail_5_json = self.json_load(result_longdetail_5, mycontents_logger)
            # contentsMetaResult.contentsMeta.longDetailSummaryFormat5 = result_longdetail_5_json.get("longDetailSummary")

            ### sentiment part!
            # 20251013 리자: 프롬프트 3)분리 --> 반복 x 3
            # orgId로 기관 이름 + 약어 등 조회 (Already retrieved at top)
            # orgId = queueContent.contentOrgId    
            # orgName, combined_keywords = ContentsOrgService().getOrgNameAndKeywords(queueContent.contentOrgId)
            mycontents_logger.info(f"🔍 [Debug] orgId: {orgId}, orgName: {orgName}, combined_keywords: {combined_keywords}")
            
            ### Log each time separately???
            # sentiment_start = time.time() # Removed timing



            # [시나리오 1] 감성 비율 + 키워드 통합 (중립 키워드 포함)
            # 2025.12.08: 기존 3단계(비율->이유->키워드)를 1단계로 통합하여 실험
            # new_question_sentiment_scenario_1 = self.question_sentiment_scenario_1.replace("[organization]", str(orgName) if orgName else "").replace("[contents]",content)
            # if combined_keywords and isinstance(combined_keywords, list):
            #     synonyms_str = ", ".join(str(item) for item in combined_keywords)
            #     new_question_sentiment_scenario_1 = new_question_sentiment_scenario_1.replace("[synonyms]", synonyms_str)
            # else:
            #     new_question_sentiment_scenario_1 = new_question_sentiment_scenario_1.replace("[synonyms]", str(orgName) if orgName else "") #if synonyms is empty, use orgName
            
            # result_sentiment_scenario_1 = self.chat_ollama._client.generate(
            #                         model=CONF.OLLAMA_MODEL,
            #                         prompt=new_question_sentiment_scenario_1,
            #                         format=(None if "gpt-oss" in CONF.OLLAMA_MODEL else "json"))
            
            # is_success, result_sentiment_scenario_1_json = self.json_load(result_sentiment_scenario_1, mycontents_logger)
            
            # # 통합 결과를 모델에 조립
            # sentiment_separated_success = self.assemble_sentiment_scenario_1_to_model(queueContent, orgName, result_sentiment_scenario_1, result_sentiment_scenario_1_json, contentsMetaResult, mycontents_logger)

            # --- 기존 로직 복구 (Base Pipeline) ---
            # 2025.12.15: 비율과 근거를 통합한 프롬프트(CoT)로 변경 (기존 분리형 로직 주석 처리)
            
            # [New Integrated Logic - Active]
            new_question_sentiment_integrated = self.question_sentiment_integrated.replace("[organization]", str(orgName) if orgName else "").replace("[contents]",content)
            if combined_keywords and isinstance(combined_keywords, list):
                synonyms_str = ", ".join(str(item) for item in combined_keywords)
                new_question_sentiment_integrated = new_question_sentiment_integrated.replace("[synonyms]", synonyms_str)
            else:
                new_question_sentiment_integrated = new_question_sentiment_integrated.replace("[synonyms]", str(orgName) if orgName else "")

            result_sentiment_integrated = self.chat_ollama._client.generate(
                                    model=CONF.OLLAMA_MODEL,
                                    prompt=new_question_sentiment_integrated,
                                    format=(None if "gpt-oss" in CONF.OLLAMA_MODEL else "json"))
            
            is_success, result_sentiment_integrated_json = self.json_load(result_sentiment_integrated, mycontents_logger)
            
            # 변수 매핑 (기존 로직 호환성 유지)
            result_sentiment_ratio = result_sentiment_integrated
            result_sentiment_ratio_json = result_sentiment_integrated_json
            result_sentiment_reason = result_sentiment_integrated
            result_sentiment_reason_json = result_sentiment_integrated_json

            positiveRatio = self.str_to_double(result_sentiment_integrated_json.get("positiveRatio", "0"))
            negativeRatio = self.str_to_double(result_sentiment_integrated_json.get("negativeRatio", "0"))
            neutralRatio = self.str_to_double(result_sentiment_integrated_json.get("neutralRatio", "0"))

            # [New Logic V2: Reason First -> Ratio Second - Commented Out]
            # Step 1: Reason V2
            # new_sentiment_reason_v2 = self.sentiment_reason_v2.replace("[organization]", str(orgName) if orgName else "").replace("[contents]",content)
            # if combined_keywords and isinstance(combined_keywords, list):
            #     synonyms_str = ", ".join(str(item) for item in combined_keywords)
            #     new_sentiment_reason_v2 = new_sentiment_reason_v2.replace("[synonyms]", synonyms_str)
            # else:
            #     new_sentiment_reason_v2 = new_sentiment_reason_v2.replace("[synonyms]", str(orgName) if orgName else "")

            # result_sentiment_reason = self.chat_ollama._client.generate(
            #                         model=CONF.OLLAMA_MODEL,
            #                         prompt=new_sentiment_reason_v2,
            #                         format=(None if "gpt-oss" in CONF.OLLAMA_MODEL else "json"))
            # is_success, result_sentiment_reason_json = self.json_load(result_sentiment_reason, mycontents_logger)

            # positiveReason = result_sentiment_reason_json.get("positiveReason", "None")
            # negativeReason = result_sentiment_reason_json.get("negativeReason", "None")
            # neutralReason = result_sentiment_reason_json.get("neutralReason", "None")

            # # Step 2: Ratio V2 (Inject Reasons)
            # new_question_sentiment_ratio_v2 = self.question_sentiment_ratio_v2.replace("[organization]", str(orgName) if orgName else "").replace("[contents]",content)
            # if combined_keywords and isinstance(combined_keywords, list):
            #     synonyms_str = ", ".join(str(item) for item in combined_keywords)
            #     new_question_sentiment_ratio_v2 = new_question_sentiment_ratio_v2.replace("[synonyms]", synonyms_str)
            # else:
            #     new_question_sentiment_ratio_v2 = new_question_sentiment_ratio_v2.replace("[synonyms]", str(orgName) if orgName else "")
            
            # new_question_sentiment_ratio_v2 = new_question_sentiment_ratio_v2.replace("[positiveReason]", positiveReason).replace("[negativeReason]", negativeReason).replace("[neutralReason]", neutralReason)

            # result_sentiment_ratio = self.chat_ollama._client.generate(
            #                         model=CONF.OLLAMA_MODEL,
            #                         prompt=new_question_sentiment_ratio_v2,
            #                         format=(None if "gpt-oss" in CONF.OLLAMA_MODEL else "json"))
            # is_success, result_sentiment_ratio_json = self.json_load(result_sentiment_ratio, mycontents_logger)

            # positiveRatio = self.str_to_double(result_sentiment_ratio_json.get("positiveRatio", "0"))
            # negativeRatio = self.str_to_double(result_sentiment_ratio_json.get("negativeRatio", "0"))
            # neutralRatio = self.str_to_double(result_sentiment_ratio_json.get("neutralRatio", "0"))

            # [Old Logic - Commented Out]
            # new_question_sentiment_ratio = self.question_sentiment_ratio.replace("[organization]", str(orgName) if orgName else "").replace("[contents]",content)
            # if combined_keywords and isinstance(combined_keywords, list):
            #     synonyms_str = ", ".join(str(item) for item in combined_keywords)
            #     new_question_sentiment_ratio = new_question_sentiment_ratio.replace("[synonyms]", synonyms_str)
            # else:
            #     new_question_sentiment_ratio = new_question_sentiment_ratio.replace("[synonyms]", str(orgName) if orgName else "") #if synonyms is empty, use orgName
            
            # #3-1) ratio 추출
            # result_sentiment_ratio = self.chat_ollama._client.generate(
            #                         model=CONF.OLLAMA_MODEL,
            #                         prompt=new_question_sentiment_ratio,
            #                         format=(None if "gpt-oss" in CONF.OLLAMA_MODEL else "json"))
            # # sentiment_end = time.time()
            # is_success, result_sentiment_ratio_json = self.json_load(result_sentiment_ratio, mycontents_logger) 
            # positiveRatio = self.str_to_double(result_sentiment_ratio_json.get("positiveRatio", "0"))
            # negativeRatio = self.str_to_double(result_sentiment_ratio_json.get("negativeRatio", "0"))
            # neutralRatio = self.str_to_double(result_sentiment_ratio_json.get("neutralRatio", "0"))
            
            # #3-2) reason 추출
            # new_question_sentiment_reason = self.sentiment_reason.replace("[organization]", str(orgName) if orgName else "").replace("[contents]",content)
            # if combined_keywords and isinstance(combined_keywords, list):
            #     synonyms_str = ", ".join(str(item) for item in combined_keywords)
            #     new_question_sentiment_reason = new_question_sentiment_reason.replace("[synonyms]", synonyms_str)
            # else:
            #     new_question_sentiment_reason = new_question_sentiment_reason.replace("[synonyms]", str(orgName) if orgName else "") #if synonyms is empty, use orgName
            # new_question_sentiment_reason = new_question_sentiment_reason.replace("[positiveRatio]", str(positiveRatio)).replace("[negativeRatio]", str(negativeRatio)).replace("[neutralRatio]", str(neutralRatio))
            
            # result_sentiment_reason = self.chat_ollama._client.generate(
            #                         model=CONF.OLLAMA_MODEL,
            #                         prompt=new_question_sentiment_reason,
            #                         format=(None if "gpt-oss" in CONF.OLLAMA_MODEL else "json"))
            # is_success, result_sentiment_reason_json = self.json_load(result_sentiment_reason, mycontents_logger) 
            
            #3-3) keywords 추출
            new_question_sentiment_keywords = self.sentiment_keywords.replace("[organization]", str(orgName) if orgName else "").replace("[contents]",content)
            if combined_keywords and isinstance(combined_keywords, list):
                synonyms_str = ", ".join(str(item) for item in combined_keywords)
                new_question_sentiment_keywords = new_question_sentiment_keywords.replace("[synonyms]", synonyms_str)
            else:
                new_question_sentiment_keywords = new_question_sentiment_keywords.replace("[synonyms]", str(orgName) if orgName else "") #if synonyms is empty, use orgName
            # new_question_sentiment_keywords = new_question_sentiment_keywords.replace("[positiveRatio]", str(positiveRatio)).replace("[negativeRatio]", str(negativeRatio))
            
            result_sentiment_keywords = self.chat_ollama._client.generate(
                                    model=CONF.OLLAMA_MODEL,
                                    prompt=new_question_sentiment_keywords,
                                    format=(None if "gpt-oss" in CONF.OLLAMA_MODEL else "json"))
            is_success, result_sentiment_keywords_json = self.json_load(result_sentiment_keywords, mycontents_logger) 
            
            # [Keyword Refinement Step] 워드클라우드용 키워드 정제 (2025.01.02 추가)
            # 문장형 키워드를 간결한 키워드로 정제하여 빈도수 통합 가능하도록 처리
            try:
                mycontents_logger.info("🔧 워드클라우드용 키워드 정제 시작...")
                
                # 각 감성별 키워드 정제
                sentiment_types = ['positiveKeywords', 'negativeKeywords', 'neutralKeywords']
                
                for sentiment_type in sentiment_types:
                    original_keywords = result_sentiment_keywords_json.get(sentiment_type, [])
                    
                    # 빈 리스트이거나 None이면 스킵
                    if not original_keywords or not isinstance(original_keywords, list) or len(original_keywords) == 0:
                        continue
                    
                    # 정제 수행
                    refined_keywords = self.refine_keywords_for_wordcloud(
                        original_keywords=original_keywords,
                        org_name=orgName,
                        combined_keywords=combined_keywords,
                        article_content=content,
                        sentiment_type=sentiment_type,
                        mycontents_logger=mycontents_logger
                    )
                    
                    # 정제된 키워드로 업데이트
                    if refined_keywords:
                        result_sentiment_keywords_json[sentiment_type] = refined_keywords
                        mycontents_logger.info(f"✅ {sentiment_type} 정제 완료: {len(original_keywords)}개 → {len(refined_keywords)}개")
                    else:
                        mycontents_logger.warning(f"⚠️ {sentiment_type} 정제 실패, 원본 유지")
                
                mycontents_logger.info("✅ 워드클라우드용 키워드 정제 완료")
                
            except Exception as e:
                mycontents_logger.error(f"❌ 키워드 정제 중 오류 발생 (무시하고 진행): {e}")
                mycontents_logger.error(traceback.format_exc())
            
            # [Translation Step] 모든 결과가 나온 후 한국어 검증 및 번역 수행 (2025.12.12 추가)
            # 2025.12.19: Context length optimization - validate fields individually
            try:
                # Fields to translate individually
                # User requested: keyword, short summary, long summary, positiveReason, negativeReason
                # We also include 'reason' and keyword lists.
                # Format: (key, source_json_dict, default_value)
                fields_to_check = [
                    ("ai_keyword", result_verify_json, []),
                    ("short_summary", result_summary_json, ""),
                    ("long_summary", result_summary_json, ""),
                    ("reason", result_sentiment_reason_json, ""),
                    ("positiveReason", result_sentiment_reason_json, ""),
                    ("negativeReason", result_sentiment_reason_json, ""),
                    ("neutralReason", result_sentiment_reason_json, ""),
                    ("positiveKeywords", result_sentiment_keywords_json, []),
                    ("negativeKeywords", result_sentiment_keywords_json, []),
                    ("neutralKeywords", result_sentiment_keywords_json, [])
                ]

                for key, source_json, default_val in fields_to_check:
                    val = source_json.get(key, default_val)
                    
                    # Skip empty values or empty lists
                    if not val:
                        continue

                    # Construct small JSON for validation
                    target_json = {key: val}
                    
                    new_question_translate = self.question_translate_to_korean.replace("[json_data]", json.dumps(target_json, ensure_ascii=False)).replace("[contents]", content)
                    
                    result_translate = self.chat_ollama._client.generate(
                                            model=CONF.OLLAMA_MODEL,
                                            prompt=new_question_translate,
                                            format=(None if "gpt-oss" in CONF.OLLAMA_MODEL else "json"))
                    
                    is_success_trans, result_translate_json = self.json_load(result_translate, mycontents_logger)
                    
                    if is_success_trans and key in result_translate_json:
                        # Update the source json with translated value
                        source_json[key] = result_translate_json[key]
                        
                        # Special handling for ai_keyword/keywords sync
                        if key == "ai_keyword":
                            source_json["keywords"] = result_translate_json[key]
                            ai_keywords = result_translate_json[key]

                mycontents_logger.info("✅ 한국어 검증 및 번역 완료 (개별 필드)")
                
                # [Summary & Keywords] 모델 재업데이트
                # 이 필드들은 번역 로직 이전에 이미 contentsMetaResult에 할당되었으므로, 번역된 값으로 갱신해야 합니다.
                contentsMetaResult.contentsMeta.summary = result_summary_json.get("short_summary")
                contentsMetaResult.contentsMeta.longSummary = result_summary_json.get("long_summary")
                contentsMetaResult.contentsMeta.keywords = result_verify_json.get("ai_keyword", [])

                # [Sentiment] 관련 필드 (Reason, Sentiment Keywords 등)
                # 이 필드들은 이 블록 이후에 호출되는 'assemble_sentiment_to_ollamaModel_v2' 함수에서 
                # contentsMetaResult에 담기므로, 위 루프에서 JSON 객체(source_json)만 수정해 두면 자동으로 반영됩니다.
                    
            except Exception as e:
                mycontents_logger.error(f"한국어 번역 중 오류 발생 (무시하고 진행): {e}")


            #sentiment_success = self.sentiment_to_ollamaModel_v2(result_sentiment_ratio, result_sentiment_ratio_json, contentsMetaResult,  mycontents_logger) 
            
            #20251013 리자: assemble from separate prompts
            sentiment_separated_success = self.assemble_sentiment_to_ollamaModel_v2(queueContent, orgName, result_sentiment_ratio, result_sentiment_ratio_json, result_sentiment_reason, result_sentiment_reason_json, result_sentiment_keywords, result_sentiment_keywords_json, contentsMetaResult,  mycontents_logger) 
            
            contentsMetaResult.sentimentSucYN = "Y" if sentiment_separated_success else "N"
            # sentiment_end = time.time() # Removed timing
            # mycontents_logger.info(f"평판분석 소요시간 : {sentiment_end-sentiment_start} 초 소요") # Removed timing
            
            # Note: Sentiment persistence to RDBMS is temporarily disabled due to schema/API changes
            

            #요약만 성공해도 성공으로 처리                        
            contentsMetaResult.metaSucYN = "Y" if summary_success else "N"
            contentsMetaResult.metaAnalyzeDt = datetime.now(timezone.utc)  
            
            # durations = {
            #     'preValidationDuration': verify_end - verify_start,
            #     'summaryAnalysisDuration': summary_end - summary_start,
            #     'sentimentAnalysisDuration': sentiment_end - sentiment_start
            # }
            
            # Set durations in contentsMeta
            # contentsMetaResult.contentsMeta.preValidationDuration = durations['preValidationDuration']
            # contentsMetaResult.contentsMeta.summaryAnalysisDuration = durations['summaryAnalysisDuration']
            # contentsMetaResult.contentsMeta.sentimentAnalysisDuration = durations['sentimentAnalysisDuration']
            
            return True, contentsMetaResult, result_summary, None, None, None 

        except Exception as e: 
            #trackback logging
            tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            mycontents_logger.error(f"Exception occurred: {e}, Args: {e.args}, Traceback: {tb_str}")

            error_ollamaMetaResult :ContentsMetaResult = self.to_error_ollamaModel() 
            durations = {
                'preValidationDuration': 0.0,
                'summaryAnalysisDuration': 0.0,
                'sentimentAnalysisDuration': 0.0
            }
            return False, None, None, None, error_ollamaMetaResult, durations


    def analysis_with_pipeline(self, content, pred_keyword_list, org_name_list, mycontents_logger:logging.Logger, queueContent:ContentsQueueVO, pipeline_type:str="hybrid"):
        """
        실험용 파이프라인 실행 메서드 (Base2/Base3 활용)
        pipeline_type: "custom" (Base2) or "hybrid" (Base3)
        """
        try:
            contentsMetaResult = ContentsMetaResult()
            contentsMetaResult.contentsMeta.method = f"ollama_pipeline_{pipeline_type}"
            
            # 1. 파이프라인 엔진 선택 및 설정 로드
            base_dir = os.path.dirname(__file__)
            if pipeline_type == "custom":
                config_path = os.path.join(base_dir, "prompts/pipeline_custom.yaml")
                engine = AnalysisOllamaBase2(config_path)
            else: # hybrid (default)
                config_path = os.path.join(base_dir, "prompts/pipeline_hybrid.yaml")
                engine = AnalysisOllamaBase3(config_path)
                
            # 2. 초기 컨텍스트 구성
            # org_name_list 중 첫 번째를 org_name으로 사용 (단순화)
            org_name = org_name_list[0] if org_name_list else ""
            
            initial_context = {
                "content": content,
                "pred_keyword_list": pred_keyword_list,
                "org_name": org_name,
                "org_name_list": org_name_list
            }
            
            start_time = time.time()
            mycontents_logger.info(f"Starting pipeline analysis ({pipeline_type})...")
            
            # 3. 파이프라인 실행
            result_context = engine.run_pipeline(initial_context)
            
            end_time = time.time()
            total_duration = end_time - start_time
            mycontents_logger.info(f"Pipeline ({pipeline_type}) execution time: {total_duration:.2f}s")
            
            # 4. 결과 매핑 (Pipeline Result -> ContentsMetaResult)
            # YAML 파일의 output_key와 일치해야 함
            
            # 4-1. 검증 결과 (verification_result)
            if "verification_result" in result_context:
                v_res = result_context["verification_result"]
                # ai_keyword -> keywords
                if "ai_keyword" in v_res and isinstance(v_res["ai_keyword"], list):
                    contentsMetaResult.contentsMeta.keywords = v_res["ai_keyword"]
                
                # related 여부에 따라 로직 분기 가능 (현재는 로깅만)
                is_related = v_res.get("related", False)
                mycontents_logger.info(f"Verification Result - Related: {is_related}")
                
                # [Added] predKeywords mapping
                # reason 필드가 리스트라면 predKeywords로 매핑 (키워드: 1.0 형태의 딕셔너리로 변환)
                if is_related and "reason" in v_res and isinstance(v_res["reason"], list):
                     contentsMetaResult.contentsMeta.predKeywords = {k: 1.0 for k in v_res["reason"]}

            # 4-2. 요약 결과 (summary_result)
            if "summary_result" in result_context:
                s_res = result_context["summary_result"]
                contentsMetaResult.contentsMeta.shortSummary = s_res.get("short_summary", "")
                contentsMetaResult.contentsMeta.longSummary = s_res.get("long_summary", "")
                contentsMetaResult.summarySucYN = "Y"
            else:
                contentsMetaResult.summarySucYN = "N"

            # 4-3. 감성 분석 결과 매핑 (Base2/Base3 공통)
            # 3개의 단계 결과를 하나의 SentimentInfo로 통합
            if "sentiment_ratio_result" in result_context:
                ratio_res = result_context.get("sentiment_ratio_result", {})
                reason_res = result_context.get("sentiment_reason_result", {})
                keywords_res = result_context.get("sentiment_keywords_result", {})
                
                sentiment_info = SentimentInfo()
                sentiment_info.orgName = org_name # 초기 컨텍스트의 org_name 사용
                
                # orgId 조회
                try:
                    sentiment_info.orgId = ContentsOrgService().get_orgId_by_synonym(org_name)
                except:
                    sentiment_info.orgId = ""

                # Ratio (문자열일 경우 처리 필요할 수 있음, 일단 float 변환 시도)
                def safe_float(val):
                    try: return float(val)
                    except: return 0.0

                sentiment_info.positiveRatio = safe_float(ratio_res.get("positiveRatio", 0))
                sentiment_info.neutralRatio = safe_float(ratio_res.get("neutralRatio", 0))
                sentiment_info.negativeRatio = safe_float(ratio_res.get("negativeRatio", 0))
                
                # Reason
                sentiment_info.reason = reason_res.get("reason", "")
                sentiment_info.positiveReason = reason_res.get("positiveReason", "")
                sentiment_info.negativeReason = reason_res.get("negativeReason", "")
                
                # Keywords
                sentiment_info.positiveKeywords = keywords_res.get("positiveKeywords", [])
                sentiment_info.negativeKeywords = keywords_res.get("negativeKeywords", [])
                sentiment_info.neutralKeywords = keywords_res.get("neutralKeywords", [])
                
                contentsMetaResult.contentsMeta.sentiments.append(sentiment_info)
            
            contentsMetaResult.metaSucYN = "Y" # 일단 파이프라인이 돌았으면 성공으로 간주
            contentsMetaResult.metaAnalyzeDt = datetime.now(timezone.utc)
            
            # 소요 시간 기록 (전체를 summaryAnalysisDuration에 넣거나 분배)
            contentsMetaResult.contentsMeta.summaryAnalysisDuration = total_duration
            
            # 기존 호출 규격(tuple)에 맞춰 반환
            return True, contentsMetaResult, None, None, None, {"totalDuration": total_duration}

        except Exception as e:
            tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            mycontents_logger.error(f"Pipeline Exception: {e}, Traceback: {tb_str}")
            return False, self.to_error_ollamaModel(), None, None, None, {}

    def refine_keywords_for_wordcloud(self, original_keywords: list, org_name: str, 
                                      combined_keywords: list, article_content: str, 
                                      sentiment_type: str, mycontents_logger: logging.Logger) -> list:
        """
        워드클라우드용 키워드 정제 메서드
        문장형 키워드를 간결한 키워드로 정제하여 빈도수 통합 가능하도록 처리
        
        Context 길이 최적화:
        - 기사 내용은 최대 1500자로 제한
        - 키워드 리스트가 20개 이상이면 배치로 나누어 처리
        """
        try:
            if not original_keywords or len(original_keywords) == 0:
                return []
            
            # 기사 내용은 전체 사용 (잘리지 않음)
            full_content = article_content if article_content else ""
            
            # 1. 키워드를 길이 순으로 정렬 (긴 것부터)
            sorted_keywords = sorted(original_keywords, key=lambda x: len(str(x)), reverse=True)
            
            # 2. 모든 키워드를 정제 대상에 포함 (2단어 이하도 정제 대상)
            # "한국전력" 같은 표현이 많이 들어가 있어서 2단어 이하도 정제 필요
            keywords_to_refine = []
            
            for keyword in sorted_keywords:
                keyword_str = str(keyword).strip()
                if not keyword_str:
                    continue
                
                keywords_to_refine.append(keyword_str)
            
            mycontents_logger.info(f"📊 {sentiment_type} 키워드 정제 대상: {len(keywords_to_refine)}개")
            
            # 3. 정제 대상 키워드가 없으면 빈 리스트 반환
            if not keywords_to_refine:
                return []
            
            # 4. 정제 대상 키워드 배치 처리: 5개 단위로 나누기
            MAX_KEYWORDS_PER_BATCH = 5
            refined_keywords = []
            
            if len(keywords_to_refine) > MAX_KEYWORDS_PER_BATCH:
                mycontents_logger.info(f"📦 키워드 배치 처리: {len(keywords_to_refine)}개 → {MAX_KEYWORDS_PER_BATCH}개씩 배치")
                
                # 배치로 나누어 처리
                for i in range(0, len(keywords_to_refine), MAX_KEYWORDS_PER_BATCH):
                    batch_keywords = keywords_to_refine[i:i + MAX_KEYWORDS_PER_BATCH]
                    batch_refined = self._refine_keywords_batch(
                        batch_keywords=batch_keywords,
                        org_name=org_name,
                        combined_keywords=combined_keywords,
                        article_content=full_content,
                        sentiment_type=sentiment_type,
                        batch_num=i // MAX_KEYWORDS_PER_BATCH + 1,
                        mycontents_logger=mycontents_logger
                    )
                    if batch_refined:
                        refined_keywords.extend(batch_refined)
            else:
                # 키워드가 적으면 한 번에 처리
                refined_keywords = self._refine_keywords_batch(
                    batch_keywords=keywords_to_refine,
                    org_name=org_name,
                    combined_keywords=combined_keywords,
                    article_content=full_content,
                    sentiment_type=sentiment_type,
                    batch_num=1,
                    mycontents_logger=mycontents_logger
                )
                if not refined_keywords:
                    refined_keywords = []
            
            # 5. 정제된 키워드 반환
            return refined_keywords
                
        except Exception as e:
            mycontents_logger.error(f"❌ {sentiment_type} 키워드 정제 중 예외 발생: {e}")
            mycontents_logger.error(traceback.format_exc())
            return original_keywords  # 실패 시 원본 반환

    def _refine_keywords_batch(self, batch_keywords: list, org_name: str, 
                               combined_keywords: list, article_content: str,
                               sentiment_type: str, batch_num: int,
                               mycontents_logger: logging.Logger) -> list:
        """
        키워드 배치 정제 헬퍼 메서드
        """
        try:
            # 프롬프트 준비
            new_question_refine = self.question_refine_keywords_for_wordcloud.replace(
                "[organization]", str(org_name) if org_name else ""
            ).replace(
                "[contents]", str(article_content) if article_content else ""
            ).replace(
                "[keywords_list]", json.dumps(batch_keywords, ensure_ascii=False)
            )
            
            # 동의어 처리
            if combined_keywords and isinstance(combined_keywords, list):
                synonyms_str = ", ".join(str(item) for item in combined_keywords)
                new_question_refine = new_question_refine.replace("[synonyms]", synonyms_str)
            else:
                new_question_refine = new_question_refine.replace("[synonyms]", str(org_name) if org_name else "")
            
            # LLM 호출
            result_refine = self.chat_ollama._client.generate(
                model=CONF.OLLAMA_MODEL,
                prompt=new_question_refine,
                format=(None if "gpt-oss" in CONF.OLLAMA_MODEL else "json")
            )
            
            is_success, result_refine_json = self.json_load(result_refine, mycontents_logger)
            
            if is_success and "refinedKeywords" in result_refine_json:
                refined_keywords = result_refine_json["refinedKeywords"]
                
                # 리스트 타입 검증
                if isinstance(refined_keywords, list):
                    # 빈 문자열 제거 및 중복 제거
                    refined_keywords = [kw.strip() for kw in refined_keywords if kw and kw.strip()]
                    # 중복 제거 (순서 유지)
                    seen = set()
                    unique_refined = []
                    for kw in refined_keywords:
                        if kw not in seen:
                            seen.add(kw)
                            unique_refined.append(kw)
                    
                    return unique_refined
                else:
                    mycontents_logger.warning(f"⚠️ {sentiment_type} 배치 {batch_num} 정제 결과가 리스트가 아님: {type(refined_keywords)}")
                    return batch_keywords
            else:
                mycontents_logger.warning(f"⚠️ {sentiment_type} 배치 {batch_num} 정제 실패, 원본 키워드 반환")
                return batch_keywords
                
        except Exception as e:
            mycontents_logger.error(f"❌ {sentiment_type} 배치 {batch_num} 키워드 정제 중 예외 발생: {e}")
            mycontents_logger.error(traceback.format_exc())
            return batch_keywords  # 실패 시 원본 반환

    def _validate_ratio_keyword_consistency(self, sentiment_info, mycontents_logger):
        """비율과 키워드 간 일관성 검증 (경고 로깅)"""
        warnings = []
        
        if sentiment_info.positiveRatio > 0 and not sentiment_info.positiveKeywords:
            warnings.append(f"positiveRatio={sentiment_info.positiveRatio}% but positiveKeywords is empty")
        
        if sentiment_info.neutralRatio > 0 and not sentiment_info.neutralKeywords:
            warnings.append(f"neutralRatio={sentiment_info.neutralRatio}% but neutralKeywords is empty")
        
        if sentiment_info.negativeRatio > 0 and not sentiment_info.negativeKeywords:
            warnings.append(f"negativeRatio={sentiment_info.negativeRatio}% but negativeKeywords is empty")
        
        if warnings:
            mycontents_logger.warning(f"[3step] 비율-키워드 불일치: {'; '.join(warnings)}")


    def json_load(self, result, mycontents_logger:logging.Logger): 
        """Ollama 분석 결과의 json 로드 (Robust Version)"""          
        try:
            text = result.response
            # 1. Try direct JSON parse
            try:
                return True, json.loads(text)
            except json.JSONDecodeError:
                pass
            
            # 2. Regex extraction (Markdown code blocks or raw JSON)
            cleaned_text = text.strip()
            # ```json ... ``` or ``` ... ```
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned_text, re.DOTALL)
            if match:
                cleaned_text = match.group(1)
            else:
                # Just { ... }
                match = re.search(r"(\{.*\})", cleaned_text, re.DOTALL)
                if match:
                    cleaned_text = match.group(1)
            
            try:
                return True, json.loads(cleaned_text)
            except json.JSONDecodeError:
                pass
                
            # 3. ast.literal_eval (for Python dict syntax)
            try:
                val = ast.literal_eval(cleaned_text)
                if isinstance(val, dict):
                    return True, val
            except:
                pass
                
            raise Exception(f"Failed to parse JSON: {text[:200]}...")

        except Exception as e :
            mycontents_logger.error(f"json_load error: {e}")
            return False, None


    def summary_to_ollamaModel_v2(self,result_summary:GenerateResponse, result_summary_json, contentsMetaResult:ContentsMetaResult, pred_kewords:dict, ai_keywords:list, mycontents_logger:logging.Logger) -> bool:
        """Ollama 분석 결과의 json --> summary 모델 변환 
        """          
        try:
            
            #20251013 리자: 프롬프트 2)에서 키워드 삭제에 따른 변경:
            # keyword = result_summary_json["keyword"]
            # if keyword is not None and isinstance(keyword,list): 
            #     contentsMetaResult.contentsMeta.keywords = keyword
            keyword = ai_keywords
            if keyword is not None and isinstance(keyword,list): 
                contentsMetaResult.contentsMeta.keywords = keyword
                    
            predkeywords = pred_kewords #pre-defined keywords
            if predkeywords is not None and isinstance(predkeywords,dict):
                contentsMetaResult.contentsMeta.predKeywords = self.nomalize_keywords(predkeywords)

            short_summary = result_summary_json["short_summary"]
            if short_summary is not None and isinstance(short_summary,str):
                contentsMetaResult.contentsMeta.shortSummary = short_summary
                    
            long_summary = result_summary_json["long_summary"]
            if long_summary is not None:
                if isinstance(long_summary,str):
                    contentsMetaResult.contentsMeta.longSummary = long_summary

            contentsMetaResult.contentsMeta.llmSummaryMeta = None
            
            return True
        
        except Exception as e :
            mycontents_logger.error(str(e))
            return False 

    def summary_to_ollamaModel(self,result_summary:GenerateResponse, result_summary_json, contentsMetaResult:ContentsMetaResult, mycontents_logger:logging.Logger) -> bool:
        """Ollama 분석 결과의 json --> summary 모델 변환 
        """          
        
        try:
            
            keyword = result_summary_json["keyword"]
            if keyword is not None and isinstance(keyword,list): 
                contentsMetaResult.contentsMeta.keywords = keyword
                    
            predkeywords = result_summary_json["predkeywords"]
            if predkeywords is not None and isinstance(predkeywords,dict):
                contentsMetaResult.contentsMeta.predKeywords = self.nomalize_keywords(predkeywords)

            short_summary = result_summary_json["short_summary"]
            if short_summary is not None and isinstance(short_summary,str):
                contentsMetaResult.contentsMeta.shortSummary = short_summary
                    
            long_summary = result_summary_json["long_summary"]
            if long_summary is not None:
                if isinstance(long_summary,str):
                    contentsMetaResult.contentsMeta.longSummary = long_summary

            llmAnalysisMeta = LLMAnalysisMeta()        
            #total_tokens = prompt_tokens + response_tokens

            try:
                # llmAnalysisMeta.contents_id = contentsId
                llmAnalysisMeta.analyze_type = "ollama"
                llmAnalysisMeta.response_metadata_model = result_summary.model if result_summary.model is not None else ""
                # llmAnalysisMeta.response_metadata_createdDt = result_summary.created_at if result_summary.created_at is not None else ""
                # llmAnalysisMeta.response_metadata_done = result_summary.done if result_summary.done is not None else False
                # llmAnalysisMeta.response_metadata_doneReason = result_summary.done_reason if result_summary.done_reason is not None else ""
                # llmAnalysisMeta.response_metadata_totalDuration = result_summary.total_duration if result_summary.total_duration is not None else ""
                # llmAnalysisMeta.response_metadata_loadDuration = result_summary.load_duration if result_summary.load_duration is not None else ""
                # llmAnalysisMeta.response_metadata_promptEvalCount = result_summary.prompt_eval_count if result_summary.prompt_eval_count is not None else ""
                # llmAnalysisMeta.response_metadata_promptEvalDuration = result_summary.prompt_eval_duration if result_summary.prompt_eval_duration is not None else ""
                # llmAnalysisMeta.response_metadata_evalCount = result_summary.eval_count if result_summary.eval_count is not None else ""
                # llmAnalysisMeta.response_metadata_evalDuration = result_summary.eval_duration if result_summary.eval_duration is not None else ""
                #llmAnalysisMeta.usage_metadata_inputToken = prompt_tokens if prompt_tokens is not None else 0
                #llmAnalysisMeta.usage_metadata_outputToken = response_tokens if response_tokens is not None else 0
                #llmAnalysisMeta.usage_metadata_totalToken = total_tokens if total_tokens is not None else 0
                #llmAnalysisMeta.regDt = datetime.now(timezone.utc)                
            except Exception as e: 
                pass        
            contentsMetaResult.contentsMeta.llmSummaryMeta = llmAnalysisMeta
            
            return True
        
        except Exception as e :
            mycontents_logger.error(str(e))
            return False 


    def extract_double(s):
        match = re.search(r"-?\d+\.\d+|-?\d+", s)  # 소수점 포함 숫자 찾기
        try:
            return float(match.group()) if match else None
        except Exception as e :
            return 0.0

    def extract_int(s):
        match = re.search(r"-?\d+\.\d+|-?\d+", s)  # 소수점 포함 숫자 찾기
        try:
            return int(match.group()) if match else None
        except Exception as e :
            return 0

    def str_to_double(self, strvalue): 
        try:
            return float(strvalue)
        except Exception as e :
            return self.extract_double(strvalue)  # 실패 시 extract_double 호출
    def str_to_int(self, strvalue): 
        try:
            return int(strvalue)
        except Exception as e :
            return self.extract_int(strvalue)  # 실패 시 extract_double 호출

    def nomalize_sentiment(self, positiveRatio, negativeRatio,neutralRatio): 
        sum = positiveRatio + negativeRatio + neutralRatio 
        if not (sum== 100):
            positiveRatio = positiveRatio/sum * 100
            negativeRatio = negativeRatio/sum * 100
            neutralRatio = neutralRatio/sum * 100
            positiveRatio = round(positiveRatio)
            negativeRatio = round(negativeRatio)
            neutralRatio  = round(neutralRatio)

        return  positiveRatio, negativeRatio, neutralRatio
        
    
    def nomalize_keywords(self,keyword_list:dict):
        sum = 0
        result_dict = {}
        for keyword,value in keyword_list.items():
            value = self.str_to_double(value)
            result_dict[keyword] = value
            sum += value 
        
        # If sum is 0, avoid division by zero
        if sum == 0:
            return result_dict

        # Normalize values so they sum to 1.0 (or 100?)
        # SimularityChecker returns cosine similarity (-1 to 1).
        # If we want to keep raw scores, we should just return result_dict.
        # But the function name implies normalization.
        # If the user complains about 1.0, maybe previous logic was normalizing?
        # But wait, if sum is small (e.g. 0.3), dividing by sum makes them larger.
        # If there is only 1 keyword, value/sum = 1.0.
        # If there are multiple keywords, they will sum to 1.0.
        
        # The user says: "predKeywords에서 각 키워드 마다 점수가 1.0으로 획일화 되어 있어"
        # This happens if normalization is applied and there is only 1 keyword, OR if the logic is wrong.
        # But here I see `sum += value` but NO division.
        # So the current code does NOT normalize.
        
        # However, if the input `keyword_list` has values as strings "1.0", then `str_to_double` returns 1.0.
        
        return  result_dict


    def assemble_sentiment_to_ollamaModel_v2(self, queueContent:ContentsQueueVO, orgName:str, result_sentiment_ratio:GenerateResponse, result_sentiment_ratio_json, result_sentiment_reason:GenerateResponse, result_sentiment_reason_json, result_sentiment_keywords:GenerateResponse, result_sentiment_keywords_json, contentsMetaResult:ContentsMetaResult, mycontents_logger:logging.Logger) -> bool:
        """Ollama 분석 3개의 결과의 json을 통합하여 --> sentiment 모델 변환"""           
        try:
            contentsMetaResult.contentsMeta.sentiments = []
            singleSentimentInfo = SentimentInfo()
            singleSentimentInfo.orgName = orgName
            singleSentimentInfo.orgId = queueContent.contentOrgId
            singleSentimentInfo.positiveRatio = self.str_to_double(result_sentiment_ratio_json.get("positiveRatio", "0"))
            singleSentimentInfo.negativeRatio = self.str_to_double(result_sentiment_ratio_json.get("negativeRatio", "0"))
            singleSentimentInfo.neutralRatio = self.str_to_double(result_sentiment_ratio_json.get("neutralRatio", "0"))
            # Safe handling for list fields
            positiveKeywords = result_sentiment_keywords_json.get("positiveKeywords", [])
            singleSentimentInfo.positiveKeywords = positiveKeywords if isinstance(positiveKeywords, list) else []
            
            negativeKeywords = result_sentiment_keywords_json.get("negativeKeywords", [])
            singleSentimentInfo.negativeKeywords = negativeKeywords if isinstance(negativeKeywords, list) else []
            
            neutralKeywords = result_sentiment_keywords_json.get("neutralKeywords", [])
            singleSentimentInfo.neutralKeywords = neutralKeywords if isinstance(neutralKeywords, list) else []

            # 키워드 개수 및 비율 계산 (중복 포함)
            p_count = len(singleSentimentInfo.positiveKeywords)
            n_count = len(singleSentimentInfo.negativeKeywords)
            neu_count = len(singleSentimentInfo.neutralKeywords)
            total_count = p_count + n_count + neu_count
            
            singleSentimentInfo.positiveKeywordCount = p_count
            singleSentimentInfo.negativeKeywordCount = n_count
            singleSentimentInfo.neutralKeywordCount = neu_count
            
            if total_count > 0:
                singleSentimentInfo.positiveKeywordRatio = round((p_count / total_count) * 100, 2)
                singleSentimentInfo.negativeKeywordRatio = round((n_count / total_count) * 100, 2)
                singleSentimentInfo.neutralKeywordRatio = round((neu_count / total_count) * 100, 2)
            else:
                singleSentimentInfo.positiveKeywordRatio = 0.0
                singleSentimentInfo.negativeKeywordRatio = 0.0
                singleSentimentInfo.neutralKeywordRatio = 0.0

            # Safe handling for string fields
            singleSentimentInfo.positiveReason = str(result_sentiment_reason_json.get("positiveReason", ""))
            singleSentimentInfo.negativeReason = str(result_sentiment_reason_json.get("negativeReason", ""))
            singleSentimentInfo.neutralReason = str(result_sentiment_reason_json.get("neutralReason", ""))
            singleSentimentInfo.reason = str(result_sentiment_reason_json.get("reason", ""))
            contentsMetaResult.contentsMeta.sentiments.append(singleSentimentInfo) 
            return True
        except Exception as e :
            mycontents_logger.error(str(e))
            return False 

    def sentiment_to_ollamaModel_v2(self,result_sentiment:GenerateResponse, result_sentiment_json, contentsMetaResult:ContentsMetaResult, mycontents_logger:logging.Logger) -> bool:
        """Ollama 분석 결과의 json --> sentiment 모델 변환"""           
        try:            
            sentiments = result_sentiment_json["sentiments"]
            contentsMetaResult.contentsMeta.sentiments = []        
            
            if sentiments is not None and isinstance(sentiments, list):
                #organization = sentiments["organization"]
                for sentiment in sentiments:
                    sentiment_info = SentimentInfo()
                    #sentiment = self.validation_check_sentiment(sentiment)
                    if sentiment["organization"] == None:
                        sentiment_info.orgName = ""
                    elif isinstance(sentiment["organization"],list):
                        if len(sentiment["organization"]) == 1:
                            if isinstance(sentiment["organization"][0],str):
                                sentiment_info.orgName= sentiment["organization"][0]        
                            else: 
                                sentiment_info.orgName = ""   
                        else: 
                            sentiment_info.orgName = ""
                    elif isinstance(sentiment["organization"],str):
                        sentiment_info.orgName= sentiment["organization"]
                    else:
                        raise Exception(f"올라마의 답변이 잘못되었습니다. (orgName : {sentiment['organization']})")
                    
                    if sentiment_info.orgName:
                        sentiment_info.orgId = ContentsOrgService().get_orgId_by_synonym(sentiment_info.orgName)
                    else :
                        sentiment_info.orgId = ""
                    sentiment_info.reason= sentiment.get("reason", "") 

                    positiveRatioStr = self.str_to_double(sentiment.get("positiveRatio", "")) 
                    negativeRatioStr = self.str_to_double(sentiment.get("negativeRatio", "") )
                    neutralRatioStr = self.str_to_double(sentiment.get("neutralRatio", "") )

                    positiveRatio, negativeRatio, neutralRatio = self.nomalize_sentiment(positiveRatioStr, negativeRatioStr, neutralRatioStr)

                    sentiment_info.positiveRatio = positiveRatio
                    sentiment_info.negativeRatio = negativeRatio  
                    sentiment_info.neutralRatio = neutralRatio 
                     
                    sentiment_info.positiveKeywords = sentiment.get("positiveKeywords", "") 
                    if not isinstance(sentiment_info.positiveKeywords,list):                        
                        sentiment_info.positiveKeywords = [""]
                    sentiment_info.negativeKeywords = sentiment.get("negativeKeywords", "") 
                    if not isinstance(sentiment_info.negativeKeywords,list):                        
                        sentiment_info.negativeKeywords = [""] 

                    sentiment_info.positiveReason= sentiment.get("positiveReason", "")     
                    if not isinstance(sentiment_info.positiveReason,str):
                        sentiment_info.positiveReason = ""
                    
                    sentiment_info.negativeReason = sentiment.get("negativeReason", "") 
                    if not isinstance(sentiment_info.negativeReason,str):
                        sentiment_info.negativeReason = ""
                    
                    contentsMetaResult.contentsMeta.sentiments.append(sentiment_info)                     
                
            contentsMetaResult.contentsMeta.llmSentimentMeta = None
            
            return True
        
        except Exception as e :
            mycontents_logger.error(str(e))
            return False 
    

    def sentiment_to_ollamaModel(self,result_sentiment:GenerateResponse, result_sentiment_json, contentsMetaResult:ContentsMetaResult, mycontents_logger:logging.Logger) -> bool:
        """Ollama 분석 결과의 json --> sentiment 모델 변환"""           
        try:            
            sentiments = result_sentiment_json["sentiments"]
            contentsMetaResult.contentsMeta.sentiments = []        
            
            if sentiments is not None and isinstance(sentiments, list):
                #organization = sentiments["organization"]
                for sentiment in sentiments:
                    sentiment_info = SentimentInfo()
                    #sentiment = self.validation_check_sentiment(sentiment)
                    if sentiment["organization"] == None:
                        sentiment_info.orgName = ""
                    elif isinstance(sentiment["organization"],list):
                        if len(sentiment["organization"]) == 1:
                            if isinstance(sentiment["organization"][0],str):
                                sentiment_info.orgName= sentiment["organization"][0]        
                            else: 
                                sentiment_info.orgName = ""   
                        else: 
                            sentiment_info.orgName = ""
                    elif isinstance(sentiment["organization"],str):
                        sentiment_info.orgName= sentiment["organization"]
                    else:
                        raise Exception(f"올라마의 답변이 잘못되었습니다. (orgName : {sentiment['organization']})")
                    
                    if sentiment_info.orgName:
                        sentiment_info.orgId = ContentsOrgService().get_orgId_by_synonym(sentiment_info.orgName)
                    else :
                        sentiment_info.orgId = ""
                    sentiment_info.reason= sentiment.get("reason", "") 

                    positiveRatioStr = self.str_to_double(sentiment.get("positiveRatio", "")) 
                    negativeRatioStr = self.str_to_double(sentiment.get("negativeRatio", "") )
                    neutralRatioStr = self.str_to_double(sentiment.get("neutralRatio", "") )

                    positiveRatio, negativeRatio, neutralRatio = self.nomalize_sentiment(positiveRatioStr, negativeRatioStr, neutralRatioStr)

                    sentiment_info.positiveRatio = positiveRatio
                    sentiment_info.negativeRatio = negativeRatio  
                    sentiment_info.neutralRatio = neutralRatio 
                     
                    sentiment_info.positiveKeywords = sentiment.get("positiveKeywords", "") 
                    if not isinstance(sentiment_info.positiveKeywords,list):                        
                        sentiment_info.positiveKeywords = [""]
                    sentiment_info.negativeKeywords = sentiment.get("negativeKeywords", "") 
                    if not isinstance(sentiment_info.negativeKeywords,list):                        
                        sentiment_info.negativeKeywords = [""] 

                    sentiment_info.positiveReason= sentiment.get("positiveReason", "")     
                    if not isinstance(sentiment_info.positiveReason,str):
                        sentiment_info.positiveReason = ""
                    
                    sentiment_info.negativeReason = sentiment.get("negativeReason", "") 
                    if not isinstance(sentiment_info.negativeReason,str):
                        sentiment_info.negativeReason = ""
                    
                    contentsMetaResult.contentsMeta.sentiments.append(sentiment_info)                     

            llmAnalysisMeta = LLMAnalysisMeta()     
            #total_tokens = prompt_tokens + response_tokens
               
            try:
                # llmAnalysisVO.contents_id = contentsId
                llmAnalysisMeta.analyze_type = "ollama"
                llmAnalysisMeta.response_metadata_model = result_sentiment.model if result_sentiment.model is not None else ""
                # llmAnalysisMeta.response_metadata_createdDt = result_sentiment.created_at if result_sentiment.created_at is not None else ""
                # llmAnalysisMeta.response_metadata_done = result_sentiment.done if result_sentiment.done is not None else False
                # llmAnalysisMeta.response_metadata_doneReason = result_sentiment.done_reason if result_sentiment.done_reason is not None else ""
                # llmAnalysisMeta.response_metadata_totalDuration = result_sentiment.total_duration if result_sentiment.total_duration is not None else ""
                # llmAnalysisMeta.response_metadata_loadDuration = result_sentiment.load_duration if result_sentiment.load_duration is not None else ""
                # llmAnalysisMeta.response_metadata_promptEvalCount = result_sentiment.prompt_eval_count if result_sentiment.prompt_eval_count is not None else ""
                # llmAnalysisMeta.response_metadata_promptEvalDuration = result_sentiment.prompt_eval_duration if result_sentiment.prompt_eval_duration is not None else ""
                # llmAnalysisMeta.response_metadata_evalCount = result_sentiment.eval_count if result_sentiment.eval_count is not None else ""
                # llmAnalysisMeta.response_metadata_evalDuration = result_sentiment.eval_duration if result_sentiment.eval_duration is not None else ""
                #llmAnalysisMeta.usage_metadata_inputToken = prompt_tokens if prompt_tokens is not None else 0
                #llmAnalysisMeta.usage_metadata_outputToken = response_tokens if response_tokens is not None else 0
                #llmAnalysisMeta.usage_metadata_totalToken = total_tokens if total_tokens is not None else 0
                llmAnalysisMeta.regDt = datetime.now(timezone.utc)                
            except Exception as e: 
                pass    
                
            contentsMetaResult.contentsMeta.llmSentimentMeta = llmAnalysisMeta
            
            return True
        
        except Exception as e :
            mycontents_logger.error(str(e))
            return False 
    
    
        
    def validation_check_sentiment(self,sentiment):
        reason = sentiment.get("reason", "") 
        if not isinstance(reason,str):
            reason = "" 
        # positiveRatio = sentiment.get("positiveRatio", "") 
        # if not isinstance(positiveRatio,str):
        #     if isinstance(positiveRatio,str):
        # 1. typecheck
        # 2.  0 ~ 9 in str
        negativeRatio = sentiment.get("negativeRatio", "") 
        if not isinstance(reason,str):
            reason = ""
        neutralRatio = sentiment.get("neutralRatio", "") 
        if not isinstance(reason,str):
            reason = ""
        positiveKeywords = sentiment.get("positiveKeywords", "") 
        if not isinstance(reason,str):
            reason = ""
        negativeKeywords = sentiment.get("negativeKeywords", "") 
        if not isinstance(reason,str):
            reason = ""
        positiveReason = sentiment.get("positiveReason", "") 
        if not isinstance(reason,str):
            reason = ""
        negativeReason = sentiment.get("negativeReason", "") 
        if not isinstance(reason,str):
            reason = ""
        pass 
    
    def to_error_ollamaModel(self) -> ContentsMetaResult:
        
        ollamaModel = ContentsMetaResult()
        ollamaModel.contentsMeta = None
        ollamaModel.metaSucYN = "N" 
        ollamaModel.metaAnalyzeDt = datetime.now(timezone.utc)
        return ollamaModel
  
if __name__ =="__main__":
    
    analysisOllamaGenerateCall = AnalysisOllamaGenerateCall()
    analysisOllamaGenerateCall.analysis_main()
    
    pass 