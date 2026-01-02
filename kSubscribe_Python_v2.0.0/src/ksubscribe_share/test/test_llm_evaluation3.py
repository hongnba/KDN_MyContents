#!/usr/bin/env python3
"""
test_llm_evaluation3.py

목적: 3단계 통합 분석 (analysis_main_3step) 테스트
작성일: 2025-12-05

기능:
  - 5단계 분석 vs 3단계 통합 분석 비교
  - analysis_main_3step() 메서드 테스트
  - 비율-키워드-이유 간 일관성 검증
  - 소요 시간 비교

3단계 통합 분석이란?
--------------------
[기존 5단계]
1️⃣ question_verify           → 검증
2️⃣ question_summary          → 요약
3️⃣ question_sentiment_ratio  → 비율
4️⃣ sentiment_reason          → 이유
5️⃣ sentiment_keywords        → 키워드

[3단계 통합]
1️⃣ question_verify           → 검증
2️⃣ question_summary          → 요약
3️⃣ question_sentiment_all    → 비율 + 키워드 + 이유 통합

장점: LLM 호출 횟수 감소, 비율-키워드-이유 간 일관성 보장

사용법:
  # 기본 테스트 (3개 문서)
  python3 test_llm_evaluation3.py --ollama-model gpt-oss:20b
  
  # 5단계 vs 3단계 비교
  python3 test_llm_evaluation3.py --ollama-model gpt-oss:20b --compare
  
  # 파일에서 ID 읽기
  python3 test_llm_evaluation3.py --test-ids test_ids.txt --ollama-model gpt-oss:20b
  
  # 프롬프트 오버라이딩
  python3 test_llm_evaluation3.py --ollama-model gpt-oss:20b --prompt-overrides my_prompts.json
"""

import os
import sys
import json
import argparse
import traceback
import time
import pymongo
from pathlib import Path
from bson import ObjectId
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict

# 프로젝트 루트를 Python path에 추가
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR.parent))
sys.path.insert(0, str(SCRIPT_DIR.parent.parent))

from ksubscribe_share.logger import Logger
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
from ksubscribe_server.analysis.analysis_ollama_generate import AnalysisOllamaGenerateCall
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.service.predefineKeywordService import PredefineKeywordService

# 웹 스크래핑 관련 import
from docker_collect.driver_utils import get_driver
from docker_scraping.web_loader import WebLoaderV3
from docker_scraping.contents_scraping_ollama_trafilaura import ContentsScrapingOllamaTrafilaura

try:
    import ksubscribe_share.config as CONF
except ImportError:
    CONF = None


# =============================================================================
# 기본 설정
# =============================================================================

DEFAULT_TEST_IDS = [
    "68edc849ae3da00bfe2d0cef",  # 한국전력 '부실 급식' 논란
    "68edc849ae3da00bfe2d0cf3",  # 한국전력, 5년간 안전·환경 법령 110건 위반
    "68edc84aae3da00bfe2d0cf7"   # 한국전력-한수원, 368억원 소송전
]

OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://ollama:11434')


# =============================================================================
# 프롬프트 오버라이딩
# =============================================================================

def load_prompt_overrides_from_python(module_path: str) -> Dict[str, str]:
    """
    Python 파일에서 프롬프트 오버라이드 로드
    
    지원 형식:
      - 클래스명 (PromptsExperimental)
      - 파일경로 (prompts/prompts_experimental.py)
      - 파일경로:클래스명 (prompts/prompts_experimental.py:PromptsExperimental)
    
    Returns:
        Dict[str, str]: {프롬프트명: 프롬프트내용}
    """
    import importlib.util
    
    # 클래스명 분리
    class_name = None
    if ':' in module_path:
        module_path, class_name = module_path.rsplit(':', 1)
    
    # 파일 경로 확인
    path = Path(module_path).expanduser()
    candidates = [path]
    if not path.is_absolute():
        candidates.append((SCRIPT_DIR / path).resolve())
        if "prompts" not in path.parts:
            candidates.append((SCRIPT_DIR / "prompts" / path).resolve())
    
    found_path = None
    for candidate in candidates:
        if candidate.is_file():
            found_path = candidate
            break
    
    if not found_path:
        raise FileNotFoundError(f"프롬프트 Python 파일을 찾을 수 없습니다: {module_path}")
    
    # 모듈 로드
    spec = importlib.util.spec_from_file_location("prompts_module", found_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # 클래스 찾기
    if class_name:
        if not hasattr(module, class_name):
            raise ValueError(f"클래스를 찾을 수 없습니다: {class_name}")
        prompt_class = getattr(module, class_name)
    else:
        # 클래스명 자동 탐색 (Prompts로 시작하는 클래스)
        prompt_classes = [
            name for name in dir(module) 
            if name.startswith('Prompts') and isinstance(getattr(module, name), type)
        ]
        if not prompt_classes:
            raise ValueError(f"Prompts로 시작하는 클래스를 찾을 수 없습니다: {found_path}")
        prompt_class = getattr(module, prompt_classes[0])
    
    # 프롬프트 속성 추출 (question_ 또는 sentiment_ 로 시작하는 문자열 속성)
    overrides: Dict[str, str] = {}
    for attr_name in dir(prompt_class):
        if attr_name.startswith('_'):
            continue
        attr_value = getattr(prompt_class, attr_name)
        if isinstance(attr_value, str) and (attr_name.startswith('question_') or attr_name.startswith('sentiment_')):
            overrides[attr_name] = attr_value
    
    return overrides


def load_prompt_overrides_file(filepath: str) -> Dict[str, str]:
    """프롬프트 오버라이드 정의를 JSON 파일에서 로드."""
    path = Path(filepath).expanduser()
    candidates = [path]
    if not path.is_absolute():
        candidates.append((SCRIPT_DIR / path).resolve())
        if "prompts" not in path.parts:
            candidates.append((SCRIPT_DIR / "prompts" / path).resolve())

    for candidate in candidates:
        if candidate.is_file():
            path = candidate
            break
    else:
        raise FileNotFoundError(f"프롬프트 오버라이드 파일을 찾을 수 없습니다: {path}")

    try:
        raw = path.read_text(encoding='utf-8')
    except Exception as exc:
        raise IOError(f"프롬프트 오버라이드 파일을 읽을 수 없습니다: {path}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"프롬프트 오버라이드 파일이 유효한 JSON이 아닙니다: {path}") from exc

    if not isinstance(data, dict):
        raise ValueError("프롬프트 오버라이드 파일 최상위 구조는 객체(JSON dict)여야 합니다.")

    overrides: Dict[str, str] = {}
    for key, value in data.items():
        if not isinstance(value, str):
            raise ValueError(f"프롬프트 '{key}' 값은 문자열이어야 합니다.")
        overrides[key] = value

    return overrides


def apply_prompt_overrides(target, overrides: Dict[str, str], logger=None) -> List[str]:
    """AnalysisOllama 객체에 프롬프트 오버라이드를 적용."""
    applied: List[str] = []
    for attr, value in overrides.items():
        if hasattr(target, attr):
            setattr(target, attr, value)
            applied.append(attr)
        elif logger:
            logger.warning(f"⚠️  존재하지 않는 프롬프트 키 무시: {attr}")
    return applied


# =============================================================================
# 데이터 클래스
# =============================================================================

@dataclass
class AnalysisResult:
    """분석 결과 데이터"""
    article_id: str
    title: str
    url: str
    method: str  # "5step" or "3step"
    
    # 시간 측정
    preValidationDuration: float
    summaryAnalysisDuration: float
    sentimentAnalysisDuration: float
    totalDuration: float
    
    # 요약 결과
    shortSummary: str
    longSummary: str
    keywords: List[str]
    
    # 감성 분석 결과
    positiveRatio: float
    neutralRatio: float
    negativeRatio: float
    
    positiveKeywords: List[str]
    neutralKeywords: List[str]
    negativeKeywords: List[str]
    
    reason: str
    positiveReason: str
    neutralReason: str
    negativeReason: str
    
    # 일관성 검증
    consistency_warnings: List[str]
    
    # 성공 여부
    success: bool
    error_message: str = ""


# =============================================================================
# MongoDB 유틸리티
# =============================================================================

def get_mongo_client():
    """MongoDB 클라이언트 반환"""
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://ksubscribe_mongodb:27017')
    return pymongo.MongoClient(mongo_uri)


def fetch_document_for_analysis(id_str: str, logger, scraper=None, web_loader=None, driver=None) -> Optional[Tuple[ContentsQueueVO, str]]:
    """
    분석에 필요한 문서 정보 조회 및 본문 스크래핑
    
    1) contents_queue 또는 contents에서 문서 메타 정보 조회
    2) 본문이 DB에 없으면 URL에서 스크래핑
    
    Returns:
        (ContentsQueueVO, article_text) 또는 None
    """
    mongo_db = os.getenv('MONGO_DB', 'mycontents')
    
    try:
        client = get_mongo_client()
        db = client.get_database(mongo_db)
        
        # contents_queue에서 조회
        doc = db.get_collection('contents_queue').find_one({"_id": ObjectId(id_str)})
        
        if not doc:
            # contents에서도 시도
            doc = db.get_collection('contents').find_one({"_id": ObjectId(id_str)})
        
        if not doc:
            logger.warning(f"문서를 찾을 수 없음: {id_str}")
            client.close()
            return None
        
        # ContentsQueueVO 생성
        queue_vo = ContentsQueueVO()
        queue_vo._id = str(doc['_id'])
        queue_vo.url = doc.get('url', '')
        queue_vo.title = doc.get('title', 'N/A')
        queue_vo.contentOrgId = doc.get('contentOrgId', doc.get('orgId', 'kepco'))
        queue_vo.cateId = doc.get('cateId', doc.get('categoryId', 'B0010'))
        
        client.close()
        
        # 본문 확인 - DB에 있으면 사용
        article_text = doc.get('rawContent', '') or doc.get('content', '') or ''
        
        # DB에 본문이 없으면 웹에서 스크래핑
        if not article_text:
            if scraper and web_loader and driver:
                logger.info(f"   🔄 본문이 DB에 없어 URL에서 스크래핑 중...")
                success, text, title = collect_raw_content_from_url(queue_vo, scraper, web_loader, driver, logger)
                if success and text:
                    article_text = text
                    if title:
                        queue_vo.title = title
                else:
                    logger.warning(f"스크래핑 실패: {id_str}")
                    return None
            else:
                logger.warning(f"본문이 비어있음 (scraper 미설정): {id_str}")
                return None
        
        return queue_vo, article_text
        
    except Exception as e:
        logger.error(f"MongoDB 조회 실패: {e}")
        return None


def collect_raw_content_from_url(queue_vo: ContentsQueueVO, scraper, web_loader, driver, logger) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    URL에서 본문 텍스트 스크래핑
    
    Returns:
        (success, text, title)
    """
    try:
        contentsOrgVO, contentsOrgCategory = scraper.contentsOrgService.findOrgAndCategory(
            queue_vo.contentOrgId, queue_vo.cateId
        )
    except Exception as e:
        logger.error(f"조직/카테고리 조회 실패: {e}")
        return False, None, queue_vo.title

    contentsVO = scraper.generateContentVO(queue_vo)
    title = queue_vo.title or contentsVO.title or ""
    text = None

    try:
        if contentsOrgCategory.cateId == "B0010":
            isSuccess, fetched_title, text = scraper.trafilauraScraper.get_newbody(contentsVO.url)
            if fetched_title:
                title = fetched_title
        else:
            method = (contentsOrgCategory.collectMethod or "textInBody").lower()
            if method == "onlypdf":
                isSuccess, text = web_loader.loadContents(contentsVO, contentsOrgVO, contentsOrgCategory, driver)
            elif method == "textintag":
                isSuccess, fetched_title, text = scraper.trafilauraScraper.get_newbody(contentsVO.url)
                if fetched_title:
                    title = fetched_title
            else:  # textInBody 또는 기타 기본 로더
                isSuccess, text = web_loader.loadContents(contentsVO, contentsOrgVO, contentsOrgCategory, driver)
    except Exception as e:
        logger.error(f"본문 수집 중 예외 발생: {e}")
        return False, None, title

    if not isSuccess or not text:
        return False, text, title

    return True, text, title


def get_pred_keyword_list(org_id: str) -> str:
    """사전 정의 키워드 리스트 문자열 반환"""
    try:
        keywords = PredefineKeywordService().getKeywordList()
        if keywords:
            return ", ".join([str(k) for k in keywords[:50]])  # 최대 50개
    except Exception:
        pass
    return "에너지, 전력, 신재생, 태양광, 풍력, ESS, 배터리"


def load_test_ids(test_ids_arg: str) -> List[str]:
    """테스트 ID 로드"""
    if not test_ids_arg:
        return DEFAULT_TEST_IDS
    
    # 파일인지 확인
    path = Path(test_ids_arg).expanduser()
    candidates = [path]
    if not path.is_absolute():
        candidates.append((SCRIPT_DIR / path).resolve())
    
    for candidate in candidates:
        if candidate.is_file():
            ids = []
            with open(candidate, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        ids.append(line)
            return ids
    
    # 쉼표 구분 문자열
    return [id.strip() for id in test_ids_arg.split(',') if id.strip()]


# =============================================================================
# 분석 실행
# =============================================================================

def run_5step_analysis(
    analyzer: AnalysisOllamaGenerateCall,
    content: str,
    pred_keyword_list: str,
    org_name_list: str,
    logger,
    queue_vo: ContentsQueueVO
) -> AnalysisResult:
    """5단계 분석 실행"""
    
    start_time = time.time()
    
    try:
        success, meta_result, result_summary, _, _, durations = analyzer.analysis_main(
            content=content,
            pred_keyword_list=pred_keyword_list,
            org_name_list=org_name_list,
            mycontents_logger=logger,
            queueContent=queue_vo
        )
        
        total_time = time.time() - start_time
        
        if not success or not meta_result:
            return AnalysisResult(
                article_id=queue_vo._id,
                title=queue_vo.title,
                url=queue_vo.url,
                method="5step",
                preValidationDuration=0, summaryAnalysisDuration=0,
                sentimentAnalysisDuration=0, totalDuration=total_time,
                shortSummary="", longSummary="", keywords=[],
                positiveRatio=0, neutralRatio=0, negativeRatio=0,
                positiveKeywords=[], neutralKeywords=[], negativeKeywords=[],
                reason="", positiveReason="", neutralReason="", negativeReason="",
                consistency_warnings=[], success=False, error_message="분석 실패"
            )
        
        # 결과 추출
        meta = meta_result.contentsMeta
        sentiment = meta.sentiments[0] if meta.sentiments else None
        
        # 일관성 검증
        warnings = validate_consistency(sentiment) if sentiment else []
        
        return AnalysisResult(
            article_id=queue_vo._id,
            title=queue_vo.title,
            url=queue_vo.url,
            method="5step",
            preValidationDuration=durations.get('preValidationDuration', 0),
            summaryAnalysisDuration=durations.get('summaryAnalysisDuration', 0),
            sentimentAnalysisDuration=durations.get('sentimentAnalysisDuration', 0),
            totalDuration=total_time,
            shortSummary=meta.shortSummary or "",
            longSummary=meta.longSummary or "",
            keywords=meta.keywords or [],
            positiveRatio=sentiment.positiveRatio if sentiment else 0,
            neutralRatio=sentiment.neutralRatio if sentiment else 0,
            negativeRatio=sentiment.negativeRatio if sentiment else 0,
            positiveKeywords=sentiment.positiveKeywords if sentiment else [],
            neutralKeywords=sentiment.neutralKeywords if sentiment else [],
            negativeKeywords=sentiment.negativeKeywords if sentiment else [],
            reason=sentiment.reason if sentiment else "",
            positiveReason=sentiment.positiveReason if sentiment else "",
            neutralReason=getattr(sentiment, 'neutralReason', "") if sentiment else "",
            negativeReason=sentiment.negativeReason if sentiment else "",
            consistency_warnings=warnings,
            success=True
        )
        
    except Exception as e:
        return AnalysisResult(
            article_id=queue_vo._id,
            title=queue_vo.title,
            url=queue_vo.url,
            method="5step",
            preValidationDuration=0, summaryAnalysisDuration=0,
            sentimentAnalysisDuration=0, totalDuration=time.time() - start_time,
            shortSummary="", longSummary="", keywords=[],
            positiveRatio=0, neutralRatio=0, negativeRatio=0,
            positiveKeywords=[], neutralKeywords=[], negativeKeywords=[],
            reason="", positiveReason="", neutralReason="", negativeReason="",
            consistency_warnings=[], success=False, error_message=str(e)
        )


def run_3step_analysis(
    analyzer: AnalysisOllamaGenerateCall,
    content: str,
    pred_keyword_list: str,
    org_name_list: str,
    logger,
    queue_vo: ContentsQueueVO
) -> AnalysisResult:
    """3단계 통합 분석 실행"""
    
    start_time = time.time()
    
    try:
        success, meta_result, result_summary, _, _, durations = analyzer.analysis_main_3step(
            content=content,
            pred_keyword_list=pred_keyword_list,
            org_name_list=org_name_list,
            mycontents_logger=logger,
            queueContent=queue_vo
        )
        
        total_time = time.time() - start_time
        
        if not success or not meta_result:
            return AnalysisResult(
                article_id=queue_vo._id,
                title=queue_vo.title,
                url=queue_vo.url,
                method="3step",
                preValidationDuration=0, summaryAnalysisDuration=0,
                sentimentAnalysisDuration=0, totalDuration=total_time,
                shortSummary="", longSummary="", keywords=[],
                positiveRatio=0, neutralRatio=0, negativeRatio=0,
                positiveKeywords=[], neutralKeywords=[], negativeKeywords=[],
                reason="", positiveReason="", neutralReason="", negativeReason="",
                consistency_warnings=[], success=False, error_message="분석 실패"
            )
        
        # 결과 추출
        meta = meta_result.contentsMeta
        sentiment = meta.sentiments[0] if meta.sentiments else None
        
        # 일관성 검증
        warnings = validate_consistency(sentiment) if sentiment else []
        
        return AnalysisResult(
            article_id=queue_vo._id,
            title=queue_vo.title,
            url=queue_vo.url,
            method="3step",
            preValidationDuration=durations.get('preValidationDuration', 0),
            summaryAnalysisDuration=durations.get('summaryAnalysisDuration', 0),
            sentimentAnalysisDuration=durations.get('sentimentAnalysisDuration', 0),
            totalDuration=total_time,
            shortSummary=meta.shortSummary or "",
            longSummary=meta.longSummary or "",
            keywords=meta.keywords or [],
            positiveRatio=sentiment.positiveRatio if sentiment else 0,
            neutralRatio=sentiment.neutralRatio if sentiment else 0,
            negativeRatio=sentiment.negativeRatio if sentiment else 0,
            positiveKeywords=sentiment.positiveKeywords if sentiment else [],
            neutralKeywords=sentiment.neutralKeywords if sentiment else [],
            negativeKeywords=sentiment.negativeKeywords if sentiment else [],
            reason=sentiment.reason if sentiment else "",
            positiveReason=sentiment.positiveReason if sentiment else "",
            neutralReason=getattr(sentiment, 'neutralReason', "") if sentiment else "",
            negativeReason=sentiment.negativeReason if sentiment else "",
            consistency_warnings=warnings,
            success=True
        )
        
    except Exception as e:
        return AnalysisResult(
            article_id=queue_vo._id,
            title=queue_vo.title,
            url=queue_vo.url,
            method="3step",
            preValidationDuration=0, summaryAnalysisDuration=0,
            sentimentAnalysisDuration=0, totalDuration=time.time() - start_time,
            shortSummary="", longSummary="", keywords=[],
            positiveRatio=0, neutralRatio=0, negativeRatio=0,
            positiveKeywords=[], neutralKeywords=[], negativeKeywords=[],
            reason="", positiveReason="", neutralReason="", negativeReason="",
            consistency_warnings=[], success=False, error_message=str(e)
        )


def validate_consistency(sentiment) -> List[str]:
    """비율-키워드 일관성 검증"""
    warnings = []
    
    if sentiment.positiveRatio > 0 and not sentiment.positiveKeywords:
        warnings.append(f"positiveRatio={sentiment.positiveRatio}% but positiveKeywords is empty")
    
    if sentiment.neutralRatio > 0 and not getattr(sentiment, 'neutralKeywords', []):
        warnings.append(f"neutralRatio={sentiment.neutralRatio}% but neutralKeywords is empty")
    
    if sentiment.negativeRatio > 0 and not sentiment.negativeKeywords:
        warnings.append(f"negativeRatio={sentiment.negativeRatio}% but negativeKeywords is empty")
    
    return warnings


# =============================================================================
# 결과 출력 및 저장
# =============================================================================

def print_result(result: AnalysisResult, logger):
    """단일 결과 출력"""
    logger.info(f"\n{'─'*60}")
    logger.info(f"📰 {result.title[:50]}...")
    logger.info(f"   방식: {result.method} | 성공: {'✅' if result.success else '❌'}")
    
    if result.success:
        logger.info(f"   ⏱️  시간: 검증={result.preValidationDuration:.2f}s, 요약={result.summaryAnalysisDuration:.2f}s, 감성={result.sentimentAnalysisDuration:.2f}s")
        logger.info(f"   📊 비율: 긍정={result.positiveRatio}%, 중립={result.neutralRatio}%, 부정={result.negativeRatio}%")
        logger.info(f"   🔑 키워드: 긍정={len(result.positiveKeywords)}개, 중립={len(result.neutralKeywords)}개, 부정={len(result.negativeKeywords)}개")
        
        if result.consistency_warnings:
            logger.warning(f"   ⚠️  일관성 경고: {'; '.join(result.consistency_warnings)}")
    else:
        logger.error(f"   ❌ 오류: {result.error_message}")


def print_comparison_table(results_5step: List[AnalysisResult], results_3step: List[AnalysisResult], logger):
    """5단계 vs 3단계 비교 테이블"""
    logger.info("\n" + "=" * 100)
    logger.info("📊 5단계 vs 3단계 비교 결과")
    logger.info("=" * 100)
    
    # 헤더
    logger.info(f"{'Article':<25} | {'Method':<6} | {'Total(s)':>8} | {'Sentiment(s)':>12} | {'Pos%':>5} | {'Neu%':>5} | {'Neg%':>5} | {'Warnings':>8}")
    logger.info("-" * 100)
    
    # 결과 쌍으로 출력
    for r5, r3 in zip(results_5step, results_3step):
        title_short = r5.title[:23] + ".." if len(r5.title) > 25 else r5.title
        
        # 5단계
        logger.info(
            f"{title_short:<25} | {'5step':<6} | {r5.totalDuration:>8.2f} | {r5.sentimentAnalysisDuration:>12.2f} | "
            f"{r5.positiveRatio:>5.1f} | {r5.neutralRatio:>5.1f} | {r5.negativeRatio:>5.1f} | {len(r5.consistency_warnings):>8}"
        )
        
        # 3단계
        logger.info(
            f"{'':<25} | {'3step':<6} | {r3.totalDuration:>8.2f} | {r3.sentimentAnalysisDuration:>12.2f} | "
            f"{r3.positiveRatio:>5.1f} | {r3.neutralRatio:>5.1f} | {r3.negativeRatio:>5.1f} | {len(r3.consistency_warnings):>8}"
        )
        
        # 차이
        time_diff = r5.totalDuration - r3.totalDuration
        logger.info(f"{'':<25} | {'차이':<6} | {time_diff:>+8.2f} | {'':<12} | {'':<5} | {'':<5} | {'':<5} |")
        logger.info("-" * 100)
    
    # 평균
    if results_5step and results_3step:
        avg_5step = sum(r.totalDuration for r in results_5step) / len(results_5step)
        avg_3step = sum(r.totalDuration for r in results_3step) / len(results_3step)
        avg_warn_5 = sum(len(r.consistency_warnings) for r in results_5step) / len(results_5step)
        avg_warn_3 = sum(len(r.consistency_warnings) for r in results_3step) / len(results_3step)
        
        logger.info(f"{'평균':<25} | {'5step':<6} | {avg_5step:>8.2f} | {'':<12} | {'':<5} | {'':<5} | {'':<5} | {avg_warn_5:>8.1f}")
        logger.info(f"{'':<25} | {'3step':<6} | {avg_3step:>8.2f} | {'':<12} | {'':<5} | {'':<5} | {'':<5} | {avg_warn_3:>8.1f}")
        logger.info(f"{'':<25} | {'절감':<6} | {avg_5step - avg_3step:>+8.2f} | {'':<12} | {'':<5} | {'':<5} | {'':<5} |")
    
    logger.info("=" * 100)


def save_results(results: List[AnalysisResult], model_name: str, output_dir: Path) -> str:
    """결과 JSON 저장"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_model = model_name.replace(':', '-').replace('/', '_')
    filename = f"3step_test_{safe_model}_{timestamp}.json"
    filepath = output_dir / filename
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    data = {
        'meta': {
            'model': model_name,
            'timestamp': timestamp,
            'count': len(results)
        },
        'results': [asdict(r) for r in results]
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return str(filepath)


# =============================================================================
# 메인 함수
# =============================================================================

def main():
    """메인 함수"""
    
    parser = argparse.ArgumentParser(
        description='3단계 통합 분석 테스트 (analysis_main_3step)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 3단계 분석만 실행
  python3 test_llm_evaluation3.py --ollama-model gpt-oss:20b
  
  # 5단계 vs 3단계 비교
  python3 test_llm_evaluation3.py --ollama-model gpt-oss:20b --compare
  
  # 파일에서 ID 읽기
  python3 test_llm_evaluation3.py --test-ids test_ids.txt --ollama-model gpt-oss:20b
        """
    )
    
    parser.add_argument(
        '--test-ids',
        type=str,
        default=None,
        help='테스트할 문서 ID (파일 경로 또는 쉼표 구분 ID)'
    )
    
    parser.add_argument(
        '--ollama-model',
        type=str,
        required=True,
        help='(필수) 테스트할 Ollama 모델. 예: gpt-oss:20b'
    )
    
    parser.add_argument(
        '--compare',
        action='store_true',
        help='5단계와 3단계 방식 모두 실행하여 비교'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='상세 로그 출력'
    )
    
    parser.add_argument(
        '--prompt-overrides',
        type=str,
        default=None,
        help='(선택) 프롬프트 오버라이드 JSON 파일 경로'
    )
    
    parser.add_argument(
        '--prompt-module',
        type=str,
        default=None,
        help='(선택) 프롬프트 Python 모듈 (예: prompts_experimental.py 또는 prompts_experimental.py:PromptsExperimental)'
    )
    
    args = parser.parse_args()
    
    # Logger 설정
    logger = Logger().setup_logger("3step_test")
    
    logger.info("=" * 80)
    logger.info("🚀 3단계 통합 분석 테스트 시작")
    logger.info("=" * 80)
    logger.info(f"모델: {args.ollama_model}")
    logger.info(f"비교 모드: {'활성화' if args.compare else '비활성화 (3단계만 실행)'}")
    logger.info(f"프롬프트 오버라이드 (JSON): {args.prompt_overrides or 'No'}")
    logger.info(f"프롬프트 모듈 (Python): {args.prompt_module or 'No'}")
    logger.info(f"시작 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 프롬프트 오버라이드 로드 (JSON 또는 Python 모듈)
    prompt_overrides: Optional[Dict[str, str]] = None
    
    # 1) Python 모듈에서 로드 (우선)
    if args.prompt_module:
        try:
            prompt_overrides = load_prompt_overrides_from_python(args.prompt_module)
            logger.info(f"🐍 프롬프트 Python 모듈 로드 완료 ({len(prompt_overrides)}개): {args.prompt_module}")
            for key in prompt_overrides.keys():
                logger.info(f"   - {key}")
        except Exception as e:
            logger.error(f"❌ 프롬프트 Python 모듈 로드 실패: {e}")
            return 1
    
    # 2) JSON 파일에서 로드 (prompt_module이 없을 때만)
    elif args.prompt_overrides:
        try:
            prompt_overrides = load_prompt_overrides_file(args.prompt_overrides)
            logger.info(f"🧪 프롬프트 JSON 로드 완료 ({len(prompt_overrides)}개): {Path(args.prompt_overrides).expanduser()}")
        except Exception as e:
            logger.error(f"❌ 프롬프트 JSON 로드 실패: {e}")
            return 1
    
    # 모델 설정
    os.environ['OLLAMA_MODEL'] = args.ollama_model
    
    # 테스트 ID 로드
    test_ids = load_test_ids(args.test_ids)
    logger.info(f"테스트 대상: {len(test_ids)}개 문서")
    
    # 분석기 생성
    logger.info("분석기 초기화 중...")
    analyzer = AnalysisOllamaGenerateCall()
    
    # 웹 스크래핑 준비 (본문이 DB에 없을 경우 URL에서 수집)
    logger.info("웹 스크래퍼 초기화 중...")
    scraper = ContentsScrapingOllamaTrafilaura()
    web_loader = WebLoaderV3()
    driver = get_driver()
    
    # 프롬프트 오버라이드 적용
    if prompt_overrides:
        applied = apply_prompt_overrides(analyzer, prompt_overrides, logger)
        if applied:
            logger.info(f"✅ 프롬프트 오버라이드 적용됨: {', '.join(applied)}")
    
    results_5step: List[AnalysisResult] = []
    results_3step: List[AnalysisResult] = []
    
    for idx, id_str in enumerate(test_ids, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"[{idx}/{len(test_ids)}] 문서 ID: {id_str}")
        logger.info(f"{'='*60}")
        
        # 문서 조회 (DB에 본문 없으면 URL에서 스크래핑)
        doc_info = fetch_document_for_analysis(id_str, logger, scraper, web_loader, driver)
        if not doc_info:
            continue
            continue
        
        queue_vo, article_text = doc_info
        logger.info(f"제목: {queue_vo.title}")
        logger.info(f"본문 길이: {len(article_text)}자")
        
        # 사전 키워드 리스트
        pred_keyword_list = get_pred_keyword_list(queue_vo.contentOrgId)
        org_name_list = ""  # 현재 미사용
        
        # 5단계 분석 (비교 모드인 경우)
        if args.compare:
            logger.info("\n📍 5단계 분석 실행 중...")
            result_5 = run_5step_analysis(analyzer, article_text, pred_keyword_list, org_name_list, logger, queue_vo)
            results_5step.append(result_5)
            print_result(result_5, logger)
        
        # 3단계 분석
        logger.info("\n📍 3단계 통합 분석 실행 중...")
        result_3 = run_3step_analysis(analyzer, article_text, pred_keyword_list, org_name_list, logger, queue_vo)
        results_3step.append(result_3)
        print_result(result_3, logger)
    
    # 결과 요약
    if args.compare and results_5step:
        print_comparison_table(results_5step, results_3step, logger)
    else:
        # 3단계 결과만 요약
        logger.info("\n" + "=" * 80)
        logger.info("📊 3단계 통합 분석 결과 요약")
        logger.info("=" * 80)
        
        total_time = sum(r.totalDuration for r in results_3step)
        total_warnings = sum(len(r.consistency_warnings) for r in results_3step)
        success_count = sum(1 for r in results_3step if r.success)
        
        logger.info(f"성공: {success_count}/{len(results_3step)}")
        logger.info(f"총 소요시간: {total_time:.2f}초")
        logger.info(f"평균 소요시간: {total_time/len(results_3step):.2f}초" if results_3step else "N/A")
        logger.info(f"일관성 경고: {total_warnings}건")
    
    # 결과 저장
    if results_3step:
        output_dir = SCRIPT_DIR / 'result'
        all_results = results_5step + results_3step if args.compare else results_3step
        filepath = save_results(all_results, args.ollama_model, output_dir)
        logger.info(f"\n💾 결과 저장됨: {filepath}")
    
    # 웹 드라이버 정리
    try:
        if driver:
            driver.quit()
            logger.info("🔌 웹 드라이버 종료됨")
    except Exception as e:
        logger.warning(f"웹 드라이버 종료 중 오류: {e}")
    
    logger.info("\n✅ 테스트 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
