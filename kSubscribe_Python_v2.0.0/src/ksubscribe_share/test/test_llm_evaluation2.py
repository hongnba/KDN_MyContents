#!/usr/bin/env python3
"""
test_llm_evaluation2.py

목적: LLM 감성 분석의 Comprehensiveness / Sufficiency 평가
작성일: 2025-12-05

기능:
  - 원문 전체에 대한 감성 예측 + 확률 추정
  - 근거(Rationale) 문장 추출
  - 근거 삭제/근거만 남긴 버전으로 확률 재측정
  - Comprehensiveness & Sufficiency 지표 계산

이론적 배경:
  - Comprehensiveness = p_full(y_base) - p_no_rationale(y_base)
    → 클수록 좋음: 근거를 지우면 모델이 확신을 잃는다 = 진짜 중요한 근거
  - Sufficiency = p_full(y_base) - p_rationale_only(y_base)
    → 작을수록 좋음: 근거만 있어도 거의 같은 확신 = 근거만으로 충분

사용법:
  # 기본 3개 문서 평가
  python3 test_llm_evaluation2.py --ollama-model gpt-oss:20b
  
  # 파일에서 ID 목록 읽기
  python3 test_llm_evaluation2.py --test-ids test_ids.txt --ollama-model gpt-oss:20b
  
  # 상세 로그 + JSON 결과 저장
  python3 test_llm_evaluation2.py --test-ids test_ids.txt --ollama-model gpt-oss:20b --verbose
"""

import os
import sys
import json
import re
import argparse
import traceback
import subprocess
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

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

from ksubscribe_share.logger import Logger
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO

try:
    from ksubscribe_share import config as CONF
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
# 데이터 클래스
# =============================================================================

@dataclass
class SentimentProbability:
    """감성 확률 데이터"""
    positive: float
    neutral: float
    negative: float
    
    def get_prob(self, label: str) -> float:
        """라벨에 해당하는 확률 반환"""
        label_lower = label.lower()
        if label_lower in ['긍정', 'positive']:
            return self.positive
        elif label_lower in ['중립', 'neutral']:
            return self.neutral
        elif label_lower in ['부정', 'negative']:
            return self.negative
        return 0.0
    
    def get_dominant_label(self) -> str:
        """가장 높은 확률의 라벨 반환"""
        probs = {'긍정': self.positive, '중립': self.neutral, '부정': self.negative}
        return max(probs, key=probs.get)


@dataclass
class EvaluationResult:
    """평가 결과 데이터"""
    article_id: str
    title: str
    url: str
    
    # 기본 예측
    base_label: str
    p_full: SentimentProbability
    
    # 근거 정보
    sentences: List[str]
    rationale_ids: List[int]
    rationale_sentences: List[str]
    
    # Comprehensiveness
    p_no_rationale: SentimentProbability
    comprehensiveness: float
    
    # Sufficiency
    p_rationale_only: SentimentProbability
    sufficiency: float
    
    # 해석
    interpretation: str


# =============================================================================
# 프롬프트 정의
# =============================================================================

# Step 1: 감성 라벨 + 확률 예측
PROMPT_SENTIMENT_WITH_PROB = """
다음 기사를 읽고 전반적인 감성을 판단해줘.

기사:
{article}

아래 JSON 형식으로만 답변해. 설명이나 주석 없이 JSON만 출력해.
- label: 긍정, 부정, 중립 중 하나
- positive, neutral, negative: 각 라벨에 대한 확신도 (0~1 사이 실수, 합이 1)

출력 형식:
{{"label": "긍정", "positive": 0.7, "neutral": 0.2, "negative": 0.1}}
"""

# Step 2: 근거 문장 추출
PROMPT_EXTRACT_RATIONALE = """
다음 기사를 읽고, 감성 판단의 핵심 근거가 되는 문장을 골라줘.

기사 (문장별 번호):
{numbered_article}

이 기사의 감성은 "{label}"로 판단되었어.
이 판단의 핵심 근거가 되는 문장 번호만 골라줘 (최대 5개).

아래 JSON 형식으로만 답변해. 설명이나 주석 없이 JSON만 출력해.
{{"rationale_sentence_ids": [1, 3, 5]}}
"""

# Step 3 & 4: 변형된 텍스트로 감성 확률 재예측
PROMPT_SENTIMENT_PROB_ONLY = """
다음 텍스트를 읽고 감성을 판단해줘.

텍스트:
{text}

아래 JSON 형식으로만 답변해. 설명이나 주석 없이 JSON만 출력해.
- positive, neutral, negative: 각 라벨에 대한 확신도 (0~1 사이 실수, 합이 1)

출력 형식:
{{"positive": 0.7, "neutral": 0.2, "negative": 0.1}}
"""


# =============================================================================
# LLM 호출 클래스
# =============================================================================

class CompSuffEvaluator:
    """Comprehensiveness / Sufficiency 평가기"""
    
    def __init__(self, model_name: str, logger):
        self.model_name = model_name
        self.logger = logger
        self.chat_ollama = ChatOllama(
            model=model_name,
            base_url=OLLAMA_URL,
            temperature=0.0,  # 일관된 결과를 위해 temperature=0
        )
    
    def _call_llm(self, prompt: str) -> str:
        """LLM 호출하여 응답 텍스트 반환"""
        try:
            response = self.chat_ollama.invoke(prompt)
            return response.content.strip()
        except Exception as e:
            self.logger.error(f"LLM 호출 실패: {e}")
            raise
    
    def _parse_json_response(self, response: str) -> dict:
        """JSON 응답 파싱 (코드 블록 제거 포함)"""
        # 코드 블록 제거
        cleaned = re.sub(r'```json\s*', '', response)
        cleaned = re.sub(r'```\s*', '', cleaned)
        cleaned = cleaned.strip()
        
        # JSON 파싱 시도
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # JSON 부분만 추출 시도
            match = re.search(r'\{[^{}]*\}', cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            self.logger.error(f"JSON 파싱 실패: {cleaned[:200]}")
            raise ValueError(f"Invalid JSON response: {cleaned[:200]}")
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """텍스트를 문장 단위로 분리"""
        # 한국어 문장 분리 (마침표, 물음표, 느낌표 기준)
        # 단, 숫자 뒤의 마침표는 제외 (예: 1.5%, 제2조 등)
        sentences = re.split(r'(?<=[.!?])\s+(?=[가-힣A-Z])', text)
        # 빈 문장 제거 및 정리
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences
    
    def _create_numbered_article(self, sentences: List[str]) -> str:
        """문장에 번호를 붙인 텍스트 생성"""
        numbered = []
        for i, sent in enumerate(sentences, 1):
            numbered.append(f"[{i}] {sent}")
        return "\n".join(numbered)
    
    def step1_get_base_prediction(self, article: str) -> Tuple[str, SentimentProbability]:
        """
        Step 1: 원문 전체에 대한 감성 라벨 + 확률 예측
        
        Returns:
            (base_label, p_full)
        """
        self.logger.info("  📊 Step 1: 기본 감성 예측 중...")
        
        prompt = PROMPT_SENTIMENT_WITH_PROB.format(article=article)
        response = self._call_llm(prompt)
        
        try:
            data = self._parse_json_response(response)
            label = data.get('label', '중립')
            prob = SentimentProbability(
                positive=float(data.get('positive', 0.33)),
                neutral=float(data.get('neutral', 0.34)),
                negative=float(data.get('negative', 0.33))
            )
            
            self.logger.info(f"    → 라벨: {label}")
            self.logger.info(f"    → 확률: 긍정={prob.positive:.2f}, 중립={prob.neutral:.2f}, 부정={prob.negative:.2f}")
            
            return label, prob
            
        except Exception as e:
            self.logger.error(f"  ❌ Step 1 파싱 실패: {e}")
            # 기본값 반환
            return "중립", SentimentProbability(0.33, 0.34, 0.33)
    
    def step2_extract_rationale(self, sentences: List[str], label: str) -> List[int]:
        """
        Step 2: 근거 문장 ID 추출
        
        Returns:
            rationale_sentence_ids (1-indexed)
        """
        self.logger.info("  📝 Step 2: 근거 문장 추출 중...")
        
        numbered_article = self._create_numbered_article(sentences)
        prompt = PROMPT_EXTRACT_RATIONALE.format(
            numbered_article=numbered_article,
            label=label
        )
        response = self._call_llm(prompt)
        
        try:
            data = self._parse_json_response(response)
            ids = data.get('rationale_sentence_ids', [])
            # 유효한 범위로 필터링
            valid_ids = [i for i in ids if 1 <= i <= len(sentences)]
            
            self.logger.info(f"    → 근거 문장 ID: {valid_ids}")
            
            return valid_ids
            
        except Exception as e:
            self.logger.error(f"  ❌ Step 2 파싱 실패: {e}")
            # 기본값: 첫 번째 문장
            return [1] if sentences else []
    
    def step3_comprehensiveness(
        self, 
        sentences: List[str], 
        rationale_ids: List[int],
        base_label: str,
        p_full: SentimentProbability
    ) -> Tuple[SentimentProbability, float]:
        """
        Step 3: Comprehensiveness 계산
        - 근거 문장을 제거한 버전으로 확률 재측정
        - Comp = p_full(y_base) - p_no_rationale(y_base)
        
        Returns:
            (p_no_rationale, comprehensiveness)
        """
        self.logger.info("  🔍 Step 3: Comprehensiveness 계산 중...")
        
        # 근거 삭제 버전 생성 (1-indexed → 0-indexed 변환)
        rationale_set = set(rationale_ids)
        no_rationale_sentences = [
            s for i, s in enumerate(sentences, 1) 
            if i not in rationale_set
        ]
        
        if not no_rationale_sentences:
            self.logger.warning("    ⚠️ 근거 삭제 후 텍스트가 비어있음")
            p_no_rationale = SentimentProbability(0.33, 0.34, 0.33)
        else:
            no_rationale_text = " ".join(no_rationale_sentences)
            prompt = PROMPT_SENTIMENT_PROB_ONLY.format(text=no_rationale_text)
            response = self._call_llm(prompt)
            
            try:
                data = self._parse_json_response(response)
                p_no_rationale = SentimentProbability(
                    positive=float(data.get('positive', 0.33)),
                    neutral=float(data.get('neutral', 0.34)),
                    negative=float(data.get('negative', 0.33))
                )
            except Exception as e:
                self.logger.error(f"    ❌ 파싱 실패: {e}")
                p_no_rationale = SentimentProbability(0.33, 0.34, 0.33)
        
        # Comprehensiveness 계산
        comp = p_full.get_prob(base_label) - p_no_rationale.get_prob(base_label)
        
        self.logger.info(f"    → p_no_rationale({base_label}): {p_no_rationale.get_prob(base_label):.2f}")
        self.logger.info(f"    → Comprehensiveness: {comp:.4f}")
        
        return p_no_rationale, comp
    
    def step4_sufficiency(
        self, 
        sentences: List[str], 
        rationale_ids: List[int],
        base_label: str,
        p_full: SentimentProbability
    ) -> Tuple[SentimentProbability, float]:
        """
        Step 4: Sufficiency 계산
        - 근거 문장만 남긴 버전으로 확률 재측정
        - Suff = p_full(y_base) - p_rationale_only(y_base)
        
        Returns:
            (p_rationale_only, sufficiency)
        """
        self.logger.info("  📐 Step 4: Sufficiency 계산 중...")
        
        # 근거만 남긴 버전 생성
        rationale_set = set(rationale_ids)
        rationale_sentences = [
            s for i, s in enumerate(sentences, 1) 
            if i in rationale_set
        ]
        
        if not rationale_sentences:
            self.logger.warning("    ⚠️ 근거 문장이 비어있음")
            p_rationale_only = SentimentProbability(0.33, 0.34, 0.33)
        else:
            rationale_text = " ".join(rationale_sentences)
            prompt = PROMPT_SENTIMENT_PROB_ONLY.format(text=rationale_text)
            response = self._call_llm(prompt)
            
            try:
                data = self._parse_json_response(response)
                p_rationale_only = SentimentProbability(
                    positive=float(data.get('positive', 0.33)),
                    neutral=float(data.get('neutral', 0.34)),
                    negative=float(data.get('negative', 0.33))
                )
            except Exception as e:
                self.logger.error(f"    ❌ 파싱 실패: {e}")
                p_rationale_only = SentimentProbability(0.33, 0.34, 0.33)
        
        # Sufficiency 계산
        suff = p_full.get_prob(base_label) - p_rationale_only.get_prob(base_label)
        
        self.logger.info(f"    → p_rationale_only({base_label}): {p_rationale_only.get_prob(base_label):.2f}")
        self.logger.info(f"    → Sufficiency: {suff:.4f}")
        
        return p_rationale_only, suff
    
    def interpret_result(self, comp: float, suff: float) -> str:
        """결과 해석"""
        interpretations = []
        
        # Comprehensiveness 해석
        if comp > 0.3:
            interpretations.append("근거가 매우 중요함 (Comp 높음)")
        elif comp > 0.1:
            interpretations.append("근거가 어느 정도 중요함 (Comp 보통)")
        else:
            interpretations.append("근거가 별로 중요하지 않음 (Comp 낮음)")
        
        # Sufficiency 해석
        if suff < 0.1:
            interpretations.append("근거만으로 충분함 (Suff 낮음=좋음)")
        elif suff < 0.3:
            interpretations.append("근거가 부분적으로 충분함 (Suff 보통)")
        else:
            interpretations.append("근거만으로는 불충분함 (Suff 높음=나쁨)")
        
        # 종합 해석
        if comp > 0.3 and suff < 0.1:
            interpretations.append("✅ 이상적: 근거가 핵심이며 충분함")
        elif comp < 0.1 and suff > 0.3:
            interpretations.append("⚠️ 문제: 근거가 중요하지도, 충분하지도 않음")
        
        return " | ".join(interpretations)
    
    def evaluate_article(self, article_id: str, title: str, url: str, article_text: str) -> EvaluationResult:
        """
        단일 기사에 대한 전체 평가 수행
        
        Returns:
            EvaluationResult
        """
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"📰 기사 평가: {title[:50]}...")
        self.logger.info(f"   ID: {article_id}")
        self.logger.info(f"{'='*60}")
        
        # 문장 분리
        sentences = self._split_into_sentences(article_text)
        self.logger.info(f"  총 {len(sentences)}개 문장")
        
        # Step 1: 기본 예측
        base_label, p_full = self.step1_get_base_prediction(article_text)
        
        # Step 2: 근거 추출
        rationale_ids = self.step2_extract_rationale(sentences, base_label)
        rationale_sentences = [sentences[i-1] for i in rationale_ids if i <= len(sentences)]
        
        # Step 3: Comprehensiveness
        p_no_rationale, comp = self.step3_comprehensiveness(
            sentences, rationale_ids, base_label, p_full
        )
        
        # Step 4: Sufficiency
        p_rationale_only, suff = self.step4_sufficiency(
            sentences, rationale_ids, base_label, p_full
        )
        
        # 해석
        interpretation = self.interpret_result(comp, suff)
        
        result = EvaluationResult(
            article_id=article_id,
            title=title,
            url=url,
            base_label=base_label,
            p_full=p_full,
            sentences=sentences,
            rationale_ids=rationale_ids,
            rationale_sentences=rationale_sentences,
            p_no_rationale=p_no_rationale,
            comprehensiveness=comp,
            p_rationale_only=p_rationale_only,
            sufficiency=suff,
            interpretation=interpretation
        )
        
        self.logger.info(f"\n  📊 결과 요약:")
        self.logger.info(f"     라벨: {base_label}")
        self.logger.info(f"     Comprehensiveness: {comp:.4f}")
        self.logger.info(f"     Sufficiency: {suff:.4f}")
        self.logger.info(f"     해석: {interpretation}")
        
        return result


# =============================================================================
# MongoDB 유틸리티
# =============================================================================

def fetch_article_text_from_contents(id_str: str, logger) -> Optional[Dict]:
    """
    contents 컬렉션에서 기사 텍스트 조회
    """
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://ksubscribe_mongodb:27017')
    mongo_db = os.getenv('MONGO_DB', 'mycontents')
    
    try:
        client = pymongo.MongoClient(mongo_uri)
        db = client.get_database(mongo_db)
        
        # contents에서 조회
        doc = db.get_collection('contents').find_one({"_id": ObjectId(id_str)})
        
        if doc:
            return {
                '_id': str(doc['_id']),
                'title': doc.get('title', 'N/A'),
                'url': doc.get('url', ''),
                'text': doc.get('rawContent', '') or doc.get('content', '') or ''
            }
        
        # contents_queue에서도 시도
        doc = db.get_collection('contents_queue').find_one({"_id": ObjectId(id_str)})
        if doc:
            return {
                '_id': str(doc['_id']),
                'title': doc.get('title', 'N/A'),
                'url': doc.get('url', ''),
                'text': ''  # Queue에는 본문이 없을 수 있음
            }
        
        client.close()
        return None
        
    except Exception as e:
        logger.error(f"MongoDB 조회 실패: {e}")
        return None


def fetch_article_from_url(url: str, logger) -> Optional[str]:
    """
    URL에서 기사 본문 스크래핑 (필요시)
    """
    try:
        from docker_scraping.trafilaura_scraper import TrafilaturaScraper
        scraper = TrafilaturaScraper()
        success, title, text = scraper.get_newbody(url)
        if success and text:
            return text
    except Exception as e:
        logger.warning(f"URL 스크래핑 실패: {e}")
    return None


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
# 결과 저장
# =============================================================================

def save_evaluation_results(results: List[EvaluationResult], model_name: str, output_dir: Path):
    """평가 결과를 JSON으로 저장"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_model = model_name.replace(':', '-').replace('/', '_')
    filename = f"comp_suff_{safe_model}_{timestamp}.json"
    filepath = output_dir / filename
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 직렬화 가능한 형태로 변환
    data = {
        'meta': {
            'model': model_name,
            'timestamp': timestamp,
            'count': len(results)
        },
        'results': []
    }
    
    for r in results:
        data['results'].append({
            'article_id': r.article_id,
            'title': r.title,
            'url': r.url,
            'base_label': r.base_label,
            'p_full': asdict(r.p_full),
            'rationale_ids': r.rationale_ids,
            'rationale_sentences': r.rationale_sentences,
            'p_no_rationale': asdict(r.p_no_rationale),
            'comprehensiveness': r.comprehensiveness,
            'p_rationale_only': asdict(r.p_rationale_only),
            'sufficiency': r.sufficiency,
            'interpretation': r.interpretation
        })
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return str(filepath)


def print_summary_table(results: List[EvaluationResult], logger):
    """결과 요약 테이블 출력"""
    logger.info("\n" + "=" * 100)
    logger.info("📊 Comprehensiveness / Sufficiency 평가 결과 요약")
    logger.info("=" * 100)
    
    # 헤더
    logger.info(f"{'Article':<30} | {'Label':<6} | {'Comp':>8} | {'Suff':>8} | {'해석'}")
    logger.info("-" * 100)
    
    total_comp = 0
    total_suff = 0
    
    for r in results:
        title_short = r.title[:28] + ".." if len(r.title) > 30 else r.title
        logger.info(
            f"{title_short:<30} | {r.base_label:<6} | "
            f"{r.comprehensiveness:>8.4f} | {r.sufficiency:>8.4f} | {r.interpretation}"
        )
        total_comp += r.comprehensiveness
        total_suff += r.sufficiency
    
    logger.info("-" * 100)
    
    # 평균
    n = len(results)
    if n > 0:
        avg_comp = total_comp / n
        avg_suff = total_suff / n
        logger.info(f"{'평균':<30} | {'':>6} | {avg_comp:>8.4f} | {avg_suff:>8.4f} |")
    
    logger.info("=" * 100)
    
    # 해석 가이드
    logger.info("\n📖 지표 해석 가이드:")
    logger.info("  • Comprehensiveness (클수록 좋음): 근거를 제거하면 예측 확신이 얼마나 떨어지는가")
    logger.info("    - > 0.3: 근거가 매우 중요 | 0.1~0.3: 보통 | < 0.1: 근거가 별로 중요하지 않음")
    logger.info("  • Sufficiency (작을수록 좋음): 근거만으로 원래 예측을 얼마나 유지하는가")
    logger.info("    - < 0.1: 근거만으로 충분 | 0.1~0.3: 부분적 | > 0.3: 근거만으로 불충분")


# =============================================================================
# 메인 함수
# =============================================================================

def main():
    """메인 함수"""
    
    parser = argparse.ArgumentParser(
        description='LLM 감성 분석의 Comprehensiveness / Sufficiency 평가',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 기본 3개 문서 평가
  python3 test_llm_evaluation2.py --ollama-model gpt-oss:20b
  
  # 파일에서 ID 읽기
  python3 test_llm_evaluation2.py --test-ids test_ids.txt --ollama-model gpt-oss:20b
        """
    )
    
    parser.add_argument(
        '--test-ids',
        type=str,
        default=None,
        help='테스트할 문서 ID (파일 경로 또는 쉼표 구분 ID). 미지정 시 기본 3개 문서 사용'
    )
    
    parser.add_argument(
        '--ollama-model',
        type=str,
        required=True,
        help='(필수) 평가할 Ollama 모델. 예: gpt-oss:20b'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='상세 로그 출력'
    )
    
    args = parser.parse_args()
    
    # Logger 설정
    logger = Logger().setup_logger("comp_suff_evaluation")
    
    logger.info("=" * 80)
    logger.info("🚀 Comprehensiveness / Sufficiency 평가 시작")
    logger.info("=" * 80)
    logger.info(f"모델: {args.ollama_model}")
    logger.info(f"시작 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 모델 설정
    os.environ['OLLAMA_MODEL'] = args.ollama_model
    
    # 테스트 ID 로드
    test_ids = load_test_ids(args.test_ids)
    logger.info(f"테스트 대상: {len(test_ids)}개 문서")
    
    # 평가기 생성
    evaluator = CompSuffEvaluator(args.ollama_model, logger)
    
    results: List[EvaluationResult] = []
    
    for idx, id_str in enumerate(test_ids, 1):
        logger.info(f"\n[{idx}/{len(test_ids)}] 문서 ID: {id_str}")
        
        # 기사 정보 조회
        article_info = fetch_article_text_from_contents(id_str, logger)
        
        if not article_info:
            logger.warning(f"  ⚠️ 문서를 찾을 수 없음: {id_str}")
            continue
        
        # 본문이 없으면 URL에서 스크래핑 시도
        article_text = article_info['text']
        if not article_text and article_info['url']:
            logger.info(f"  📥 URL에서 본문 스크래핑 중...")
            article_text = fetch_article_from_url(article_info['url'], logger)
        
        if not article_text:
            logger.warning(f"  ⚠️ 기사 본문을 가져올 수 없음: {id_str}")
            continue
        
        # 평가 수행
        try:
            result = evaluator.evaluate_article(
                article_id=id_str,
                title=article_info['title'],
                url=article_info['url'],
                article_text=article_text
            )
            results.append(result)
            
        except Exception as e:
            logger.error(f"  ❌ 평가 실패: {e}")
            if args.verbose:
                logger.error(traceback.format_exc())
    
    # 결과 요약
    if results:
        print_summary_table(results, logger)
        
        # 결과 저장
        output_dir = SCRIPT_DIR / 'result'
        filepath = save_evaluation_results(results, args.ollama_model, output_dir)
        logger.info(f"\n💾 결과 저장됨: {filepath}")
    else:
        logger.warning("평가된 문서가 없습니다.")
    
    logger.info("\n✅ 평가 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
