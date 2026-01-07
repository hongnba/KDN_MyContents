#!/usr/bin/env python3
"""
test_llm_evaluation.py

목적: 특정 문서들로 LLM 모델 평가 및 비교
작성일: 2025-11-18

기능:
  - 특정 ObjectId 목록으로 LLM 평가 실행
  - 텍스트 파일 또는 커맨드 라인에서 ID 입력 지원
  - 결과 비교 및 통계 출력
  - 재시도/통계 계산 건너뛰기 (테스트 전용)

사용법:
  # 파일에서 ID 목록 읽기
  python3 test_llm_evaluation.py --test-ids test_ids.txt
  
  # 커맨드 라인에서 직접 입력
  python3 test_llm_evaluation.py --test-ids "68edc849ae3da00bfe2d0cef,68edc849ae3da00bfe2d0cf3"
  
  # 기본 3개 문서 (하드코딩)
  python3 test_llm_evaluation.py
  
  # 상세 로그 모드
  python3 test_llm_evaluation.py --test-ids test_ids.txt --verbose
  
  # Queue에서 삭제하지 않기 (재실행 가능)
  python3 test_llm_evaluation.py --test-ids test_ids.txt --keep-queue
"""

import sys
import os
import argparse
from pathlib import Path
from bson import ObjectId
from datetime import datetime
from typing import List, Dict, Optional
import json
import glob
import subprocess
import time

# 프로젝트 루트를 Python path에 추가
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from docker_collect.driver_utils import get_driver
from docker_scraping.web_loader import WebLoaderV3
from docker_scraping.contents_scraping_ollama_trafilaura import ContentsScrapingOllamaTrafilaura
from ksubscribe_server.analysis.ollama_alive import OllamaAlive
from ksubscribe_server.analysis.analysis_ollama_generate import AnalysisOllamaGenerateCall
from ksubscribe_share.db.service.contentsService import ContentsService
from ksubscribe_share.db.service.baseQueryService import BaseQueryService
import pymongo
from ksubscribe_share.logger import Logger
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO
import ksubscribe_share.config as CONF

DUMP_RAW_SENTINEL = "__DUMP_RAW_DEFAULT__"
GPU_USAGE_BUSY_THRESHOLD_MB = 200

# 기본 테스트 문서 ID (하드코딩)
# 사용법: python3 test_llm_evaluation.py (--test-ids 옵션 없이 실행하면 아래 ID 사용)
DEFAULT_TEST_IDS = [
    "68edc849ae3da00bfe2d0cef",  # "이게 8천 원이라고요? 심했다"…한국전력 '부실 급식' 논란
    "68edc849ae3da00bfe2d0cf3",  # 한국전력, 5년간 안전·환경 법령 110건 위반
    "68edc84aae3da00bfe2d0cf7"   # 한국전력-한수원, 368억원 소송전
]


def get_recent_queue_ids(limit: int = 3) -> List[str]:
    """contents_queue에서 최근 문서 ID 조회"""
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://ksubscribe_mongodb:27017')
    mongo_db = os.getenv('MONGO_DB', 'mycontents')
    client = None
    ids: List[str] = []
    try:
        client = pymongo.MongoClient(mongo_uri)
        db = client.get_database(mongo_db)
        coll = db.get_collection('contents_queue')

        cursor = coll.find({}, {"_id": 1, "collectDt": 1}).sort(
            [("collectDt", -1), ("_id", -1)]
        ).limit(limit)

        for doc in cursor:
            ids.append(str(doc.get('_id')))
    except Exception as e:
        print(f"❌ Queue ID 조회 실패: {e}")
    finally:
        if client:
            client.close()

    return ids


def _collect_gpu_memory_usage() -> List[tuple]:
    """nvidia-smi에서 GPU별 사용 메모리를 수집."""
    cmd = [
        "nvidia-smi",
        "--query-gpu=index,memory.used",
        "--format=csv,noheader,nounits",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    usages: List[tuple] = []
    for line in proc.stdout.strip().splitlines():
        parts = [p.strip() for p in line.split(',') if p.strip()]
        if len(parts) < 2:
            continue
        try:
            gpu_idx = int(parts[0])
            mem_mb = int(parts[1])
            usages.append((gpu_idx, mem_mb))
        except ValueError:
            continue
    return usages


def _fallback_nvidia_smi_plain() -> str:
    try:
        proc = subprocess.run(["nvidia-smi"], capture_output=True, text=True, check=True)
        return proc.stdout.strip()
    except Exception:
        return ""


def log_gpu_status(label: str, logger) -> Optional[bool]:
    """GPU 상태를 로그로 남기고, 점유 여부를 반환."""
    try:
        usages = _collect_gpu_memory_usage()
        if not usages:
            logger.info(f"[GPU] {label}: 사용 정보 없음")
            return None
        usage_text = ', '.join(f"GPU{idx}:{mem}MB" for idx, mem in usages)
        busy = any(mem > GPU_USAGE_BUSY_THRESHOLD_MB for _, mem in usages)
        state = "모델이 올라간 것으로 감지" if busy else "GPU 점유 없음"
        logger.info(f"[GPU] {label}: {state} ({usage_text})")
        return busy
    except FileNotFoundError:
        logger.warning(f"[GPU] {label}: nvidia-smi 명령을 찾을 수 없습니다.")
        return None
    except subprocess.CalledProcessError as exc:
        logger.warning(f"[GPU] {label}: nvidia-smi 조회 실패 - {exc}")
        fallback = _fallback_nvidia_smi_plain()
        if fallback:
            logger.info(f"[GPU] {label} 출력:\n{fallback}")
        return None


def report_gpu_transition(before: Optional[bool], after: Optional[bool], logger):
    """테스트 전후 GPU 점유 변화를 요약."""
    if before is None or after is None:
        logger.info("[GPU] 테스트 전후 비교 불가 (GPU 상태 정보를 일부 수집하지 못했습니다).")
        return

    if before and not after:
        logger.info("[GPU] 모델이 테스트 중 GPU에 올라갔다가 종료 후 내려갔습니다.")
    elif before and after:
        logger.info("[GPU] 모델이 GPU에 계속 올라간 상태로 유지되고 있습니다.")
    elif not before and after:
        logger.info("[GPU] 테스트 이후 GPU에 새 작업이 올라간 것으로 보입니다.")
    else:
        logger.info("[GPU] 테스트 전후 모두 GPU 점유가 감지되지 않았습니다.")


def _resolve_test_ids_path(path_str: str) -> Optional[Path]:
    """--test-ids 파일 경로를 절대/상대 모두 지원하도록 해석."""
    candidate = Path(path_str).expanduser()
    if candidate.is_file():
        return candidate

    if not candidate.is_absolute():
        script_relative = (SCRIPT_DIR / candidate).resolve()
        if script_relative.is_file():
            return script_relative

    return None


def load_test_ids_from_file(filepath: str) -> List[str]:
    """
    텍스트 파일에서 ObjectId 목록 로드
    
    파일 형식:
      - 한 줄에 하나의 ObjectId
      - # 으로 시작하는 줄은 주석 (무시)
      - 빈 줄은 무시
    
    Args:
        filepath: 텍스트 파일 경로
        
    Returns:
        ObjectId 문자열 리스트
        
    Raises:
        FileNotFoundError: 파일이 없는 경우
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {filepath}")
    
    ids = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            # 빈 줄 또는 주석 무시
            if not line or line.startswith('#'):
                continue
            
            # ObjectId 유효성 검증
            try:
                ObjectId(line)  # 유효성만 확인
                ids.append(line)
            except Exception as e:
                print(f"⚠️  라인 {line_num}: 유효하지 않은 ObjectId - {line}")
                print(f"    오류: {e}")
    
    return ids


def parse_test_ids_argument(test_ids_arg: str) -> List[str]:
    """
    --test-ids 인자 파싱 (파일 또는 쉼표 구분 ID)
    
    Args:
        test_ids_arg: 파일 경로 또는 쉼표로 구분된 ID 목록
        
    Returns:
        ObjectId 문자열 리스트
    """
    # 파일인지 확인
    resolved_file = _resolve_test_ids_path(test_ids_arg)
    if resolved_file:
        print(f"📄 파일에서 ID 목록 로드: {resolved_file}")
        return load_test_ids_from_file(str(resolved_file))
    
    # 쉼표로 구분된 ID 목록
    print(f"📝 커맨드 라인에서 ID 파싱")
    ids = [id.strip() for id in test_ids_arg.split(',') if id.strip()]
    
    # 유효성 검증
    valid_ids = []
    for id_str in ids:
        try:
            ObjectId(id_str)
            valid_ids.append(id_str)
        except Exception as e:
            print(f"⚠️  유효하지 않은 ObjectId: {id_str} - {e}")
    
    return valid_ids


def fetch_documents_from_queue(id_list: List[str], logger) -> List[Dict]:
    """
    contents_queue에서 문서 조회
    
    Args:
        id_list: ObjectId 문자열 리스트
        logger: Logger 인스턴스
        
    Returns:
        문서 딕셔너리 리스트
    """
    # 직접 pymongo로 mycontents.contents_queue에서 문서를 조회합니다.
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://ksubscribe_mongodb:27017')
    mongo_db = os.getenv('MONGO_DB', 'mycontents')
    client = None
    docs = []
    logger.info("\n📋 mycontents.contents_queue에서 문서 조회 중...")
    try:
        client = pymongo.MongoClient(mongo_uri)
        db = client.get_database(mongo_db)
        coll = db.get_collection('contents_queue')
    except Exception as e:
        logger.error(f"MongoDB에 연결 실패: {e}")
        return docs

    for id_str in id_list:
        try:
            doc = coll.find_one({"_id": ObjectId(id_str)})
            if doc:
                docs.append(doc)
                title = doc.get('title', 'N/A')
                logger.info(f"  ✅ {id_str[:8]}... - {title[:60]}")
            else:
                logger.warning(f"  ⚠️  {id_str} - contents_queue에 문서가 없음")
        except Exception as e:
            logger.error(f"  ❌ {id_str} - 조회 오류: {e}")
    
    if client:
        try:
            client.close()
        except Exception:
            pass
    
    return docs


def resolve_dump_config(dump_option: str):
    """--dump-raw 인자 해석."""
    if not dump_option:
        return None

    config = {
        "print": True,
        "dir": None,
    }

    stdout_markers = {"stdout", "console", "-", "print"}

    if dump_option == DUMP_RAW_SENTINEL:
        config["dir"] = (SCRIPT_DIR / "outputs").resolve()
    elif dump_option.lower() in stdout_markers:
        config["dir"] = None
    else:
        config["dir"] = Path(dump_option).expanduser().resolve()

    return config


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


def collect_raw_content(queue_vo: ContentsQueueVO, scraper, webLoader, driver, logger):
    """원문 텍스트만 별도로 수집."""
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
                isSuccess, text = webLoader.loadContents(contentsVO, contentsOrgVO, contentsOrgCategory, driver)
            elif method == "textintag":
                isSuccess, fetched_title, text = scraper.trafilauraScraper.get_newbody(contentsVO.url)
                if fetched_title:
                    title = fetched_title
            else:  # textInBody 또는 기타 기본 로더
                isSuccess, text = webLoader.loadContents(contentsVO, contentsOrgVO, contentsOrgCategory, driver)
    except Exception as e:
        logger.error(f"원문 수집 중 예외 발생: {e}")
        return False, None, title

    if not isSuccess or not text:
        return False, text, title

    return True, text, title


def dump_raw_content(queue_vo: ContentsQueueVO, scraper, webLoader, driver, dump_config, logger):
    """요청 시 원문 텍스트 출력/저장."""
    success, text, title = collect_raw_content(queue_vo, scraper, webLoader, driver, logger)
    if not success or not text:
        logger.warning(f"⚠️  원문 덤프 실패: {queue_vo._id}")
        return

    header = f"RAW CONTENT [{queue_vo._id}] - {title[:80]}"
    separator = "=" * len(header)

    if dump_config.get("print"):
        print(f"\n{separator}\n{header}\n{separator}\n{text}\n")

    output_dir = dump_config.get("dir")
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / f"{queue_vo._id}.txt"
        file_path.write_text(text, encoding="utf-8")
        logger.info(f"📝 원문 저장: {file_path}")


def process_documents(
    docs: List[Dict],
    logger,
    keep_queue: bool = False,
    verbose: bool = False,
    dump_config=None,
    prompt_overrides: Optional[Dict[str, str]] = None,
    yaml_path: Optional[str] = None,
):
    """
    문서 스크래핑 및 LLM 분석 실행
    
    Args:
        docs: 문서 딕셔너리 리스트
        logger: Logger 인스턴스
        keep_queue: True면 Queue에서 삭제하지 않음
        verbose: 상세 로그 출력 여부
    """
    if len(docs) == 0:
        logger.error("❌ 처리할 문서가 없습니다.")
        return
    
    logger.info(f"\n총 {len(docs)}개 문서 처리 시작\n")
    
    # 스크래핑 준비
    scraper = ContentsScrapingOllamaTrafilaura()
    
    # keep_queue 옵션 적용
    if keep_queue:
        scraper.delete_queue_after_processing = False
        logger.info("🔒 Queue 유지 모드: 처리 후에도 Queue에서 삭제하지 않습니다.")
    
    webLoader = WebLoaderV3()
    driver = get_driver()
    
    # YAML 프롬프트 파일 경로 처리
    if yaml_path:
        # 컨테이너 내부 경로로 변환 (필요한 경우)
        if not os.path.exists(yaml_path):
            # 상대 경로인 경우 컨테이너 내부 경로로 변환 시도
            container_path = f"/app/ksubscribe_share/test/{os.path.basename(yaml_path)}"
            if os.path.exists(container_path):
                yaml_path = container_path
        logger.info(f"📝 YAML 프롬프트 파일 사용: {yaml_path}")
    
    ollamaAnalysis = AnalysisOllamaGenerateCall(yaml_path=yaml_path)
    if prompt_overrides:
        applied = apply_prompt_overrides(ollamaAnalysis, prompt_overrides, logger)
        if applied:
            logger.info(f"🧪 프롬프트 오버라이드 적용: {', '.join(applied)}")
    # GPT 모델일 경우 format 제거 (JSON 포맷이 답변을 방해할 수 있음)
    if 'gpt' in os.environ.get('OLLAMA_MODEL', '').lower():
        ollamaAnalysis.chat_ollama.format = None
        logger.info("⚠️ GPT 모델 감지: format='json' 제거하여 텍스트 응답 허용")
    contents_service = ContentsService() if verbose else None
    
    results = []
    
    for idx, doc in enumerate(docs, 1):
        logger.info("=" * 80)
        logger.info(f"[{idx}/{len(docs)}] 처리 중")
        logger.info(f"ID: {doc['_id']}")
        logger.info(f"URL: {doc['url']}")
        logger.info(f"제목: {doc.get('title', 'N/A')}")
        logger.info("=" * 80)
        
        # MongoDB 문서 필드명을 ContentsQueueVO 파라미터명에 맞게 매핑
        # 다양한 필드 네이밍(legacy/variation)에 대응하도록 안전한 추출(fallback)을 사용합니다.
        def _get_field(d, *keys):
            for k in keys:
                if k in d and d.get(k) is not None:
                    return d.get(k)
            return None

        queue_doc = {
            'contentOrgId': _get_field(doc, 'contentOrgId', 'contentsOrgId', 'orgId', 'contents_org_id'),
            'cateId': _get_field(doc, 'cateId', 'categoryId', 'category_id', 'cate_id'),
            'title': _get_field(doc, 'title', 'newsTitle', 'headline'),
            'url': _get_field(doc, 'url', 'link', 'originalUrl'),
            'pubDt': _get_field(doc, 'pubDt', 'publishDate', 'pub_dt'),
            'collectDt': _get_field(doc, 'collectDt', 'collectedAt', 'collect_dt'),
            'collectKeyword': _get_field(doc, 'collectKeyword', 'keyword', 'collectKeywordList'),
            '_id': doc.get('_id'),
        }

        # 대신 가능하면 원본 문서 전체를 전달하는 것도 안전하지만,
        # ContentsQueueVO가 기대하는 필드만 채워서 생성합니다.
        queue_vo = ContentsQueueVO(**queue_doc)
        
        start_time = datetime.now()
        
        try:
            if dump_config:
                dump_raw_content(queue_vo, scraper, webLoader, driver, dump_config, logger)

            # 스크래핑 및 LLM 분석
            # scraper.crawl_and_analyze_one_ollama(queue_vo, webLoader, driver, ollamaAnalysis)
            
            # [Base2 실험용 수정] 직접 크롤링 후 analysis_with_pipeline 호출
            # logger.info(f"🚀 [Base2 실험] 직접 크롤링 및 파이프라인 분석 시작: {queue_vo.url}")
            
            # 1. 크롤링 (Encapsulated method 사용)
            isSuccess, text, title, contentsVO = scraper.scrape_content(queue_vo, webLoader, driver)

            if not isSuccess or not text:
                logger.error(f"크롤링 실패: {queue_vo.url}")
            else:
                # 3. 파이프라인 분석 실행 (Base - analysis_main)
                logger.info(f"🚀 Base 파이프라인 실행 (analysis_main): {queue_vo.url}")
                
                try:
                    # analysis_main returns tuple: (bool, ContentsMetaResult, ...)
                    result_tuple = ollamaAnalysis.analysis_main(
                        content=text,
                        pred_keyword_list=scraper.keyword_name_list,
                        org_name_list=scraper.org_name_list,
                        mycontents_logger=logger,
                        queueContent=queue_vo
                    )
                    
                    if isinstance(result_tuple, tuple):
                        isSuccess = result_tuple[0]
                        contentsMetaResult = result_tuple[1]
                    else:
                        isSuccess = result_tuple
                        contentsMetaResult = None

                except Exception as e:
                    logger.error(f"Base 파이프라인 실행 실패: {e}")
                    isSuccess = False
                    contentsMetaResult = None

                # 4. 결과 처리 및 DB 저장
                if isSuccess and contentsMetaResult:
                    contentsVO = scraper.generateContentsMeta_ollama(contentsVO, contentsMetaResult)
                    contentsVO = scraper.generate_imageId(contentsVO)
                    
                    # Calculate and set totalProcessingDuration
                    end_time_processing = datetime.now()
                    duration_seconds = (end_time_processing - start_time).total_seconds()
                    if contentsVO.contentsMeta:
                        contentsVO.contentsMeta.totalProcessingDuration = round(duration_seconds, 3)
                        
                    try:
                        BaseQueryService.insert_one(contentsVO)
                        logger.info(f"✅ 분석 및 저장 성공 (Base): {contentsVO.title}")
                    except Exception as e:
                        logger.error(f"DB 저장 실패: {e}")
                else:
                    logger.error("분석 실패 (Base)")
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ 처리 완료 (소요 시간: {elapsed:.1f}초)")
            
            # 결과 기록
            results.append({
                'id': str(doc['_id']),
                'url': doc['url'],
                'success': True,
                'elapsed': elapsed
            })
            
            # MongoDB에서 결과 확인 (선택적)
            if verbose and contents_service:
                # saved_content = contents_service.find_by_url(doc['url'])
                # 최신 결과 조회를 위해 직접 쿼리 (URL로 조회하되 최신순 정렬)
                try:
                    coll = contents_service.mongoManager.getCollection("contents")
                    latest_doc = coll.find_one(
                        {"url": doc['url']}, 
                        sort=[("metaAnalyzeDt", -1), ("rawCollectDt", -1), ("_id", -1)]
                    )
                    saved_content = ContentsVO.from_mongo(latest_doc) if latest_doc else None
                except Exception as e:
                    logger.warning(f"최신 결과 조회 실패: {e}")
                    saved_content = None

                if saved_content and getattr(saved_content, "contentsMeta", None):
                    summary_text = (
                        getattr(saved_content.contentsMeta, "shortSummary", None)
                        or getattr(saved_content.contentsMeta, "longSummary", None)
                    )
                    if summary_text:
                        preview = summary_text.replace("\n", " ")[:100]
                        logger.info(f"📊 요약: {preview}{'...' if len(summary_text) > 100 else ''}")
                    else:
                        logger.info("� 요약 정보 없음")

                    sentiments = getattr(saved_content.contentsMeta, "sentiments", None) or []
                    if sentiments:
                        top_sentiment = sentiments[0]
                        pos = getattr(top_sentiment, "positiveRatio", 0.0)
                        neg = getattr(top_sentiment, "negativeRatio", 0.0)
                        neu = getattr(top_sentiment, "neutralRatio", 0.0)
                        org_name = getattr(top_sentiment, "orgName", None) or "전체"
                        
                        if pos is not None and neg is not None:
                            logger.info(
                                f"📈 감성 비율({org_name}): 긍정 {pos:.1f}% / 부정 {neg:.1f}% / 중립 {neu:.1f}%"
                            )
                        else:
                            logger.info(f"📈 감성 비율({org_name}): 데이터 없음")
                    else:
                        logger.info("📈 감성 데이터 없음")

            # 저장 위치 확인 및 출력
            try:
                storage = check_storage_status(str(doc['_id']), dump_config, logger)
                logger.info("📂 저장 상태:")
                logger.info(f"  - DB(contents): {'있음' if storage['in_contents'] else '없음'}")
                logger.info(f"  - Queue(contents_queue): {'있음' if storage['in_queue'] else '없음'}")
                if storage['export_files']:
                    for ef in storage['export_files']:
                        logger.info(f"  - Export 파일: {ef}")
                else:
                    logger.info("  - Export 파일: 없음(또는 exports 폴더에 해당 파일 없음)")
                if storage['raw_dump']:
                    logger.info(f"  - Raw dump: {storage['raw_dump']}")
            except Exception:
                pass
        
        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ 처리 실패 (소요 시간: {elapsed:.1f}초)")
            logger.error(f"   오류: {e}")
            
            results.append({
                'id': str(doc['_id']),
                'url': doc['url'],
                'success': False,
                'elapsed': elapsed,
                'error': str(e)
            })
            # 실패 시에도 저장 상태를 확인해서 출력
            try:
                storage = check_storage_status(str(doc['_id']), dump_config, logger)
                logger.info("📂 (실패한 문서) 저장 상태:")
                logger.info(f"  - DB(contents): {'있음' if storage['in_contents'] else '없음'}")
                logger.info(f"  - Queue(contents_queue): {'있음' if storage['in_queue'] else '없음'}")
                if storage['export_files']:
                    for ef in storage['export_files']:
                        logger.info(f"  - Export 파일: {ef}")
                if storage['raw_dump']:
                    logger.info(f"  - Raw dump: {storage['raw_dump']}")
            except Exception:
                pass
        
        logger.info("")
    
    driver.quit()
    
    return results, scraper


def print_summary(results: List[Dict], scraper, logger):
    """
    평가 결과 요약 출력
    
    Args:
        results: 처리 결과 리스트
        scraper: ContentsScrapingOllamaTrafilaura 인스턴스
        logger: Logger 인스턴스
    """
    logger.info("=" * 80)
    logger.info("📊 LLM 평가 결과 요약")
    logger.info("=" * 80)
    
    total = len(results)
    success = sum(1 for r in results if r['success'])
    failed = total - success
    
    total_time = sum(r['elapsed'] for r in results)
    avg_time = total_time / total if total > 0 else 0
    
    logger.info(f"총 문서 수: {total}개")
    logger.info(f"  ✅ 성공: {success}개")
    logger.info(f"  ❌ 실패: {failed}개")
    logger.info(f"\n처리 시간:")
    logger.info(f"  총 시간: {total_time:.1f}초")
    logger.info(f"  평균 시간: {avg_time:.1f}초/문서")
    logger.info(f"\nScraper 통계:")
    logger.info(f"  스크래핑 성공: {scraper.scrapping_cnt_for_once}개")
    logger.info(f"  LLM 분석 성공: {scraper.analysis_cnt_for_once}개")
    logger.info("=" * 80)
    
    # 실패한 문서 상세 출력
    if failed > 0:
        logger.info("\n⚠️  실패한 문서:")
        for r in results:
            if not r['success']:
                logger.info(f"  - {r['id'][:8]}... : {r.get('error', 'Unknown error')}")


def print_mongodb_commands(docs: List[Dict], logger):
    """
    MongoDB에서 결과 확인하는 명령어 출력
    
    Args:
        docs: 문서 리스트
        logger: Logger 인스턴스
    """
    logger.info("\n" + "=" * 80)
    logger.info("📌 MongoDB에서 결과 확인 방법")
    logger.info("=" * 80)
    
    logger.info("\n1. MongoDB 컨테이너 접속:")
    logger.info("   docker exec -it ksubscribe_mongodb mongosh mycontents")
    
    logger.info("\n2. 처리된 문서 조회:")
    logger.info("   db.contents.find({")
    logger.info("     _id: { $in: [")
    for doc in docs:
        logger.info(f'       ObjectId("{doc["_id"]}"),')
    logger.info("     ]}")
    logger.info("   }).pretty()")


def check_storage_status(id_str: str, dump_config, logger):
    """
    문서의 저장 위치를 확인합니다: contents, contents_queue, exports 파일

    Returns a dict with keys: in_contents (bool), in_queue (bool), export_files (list of paths), raw_dump (path or None)
    """
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://ksubscribe_mongodb:27017')
    mongo_db = os.getenv('MONGO_DB', 'mycontents')
    in_contents = False
    in_queue = False
    export_files = []
    raw_dump = None

    # check raw dump path if dump_config provided
    try:
        if dump_config and dump_config.get('dir'):
            candidate = Path(dump_config.get('dir')) / f"{id_str}.txt"
            if candidate.exists():
                raw_dump = str(candidate.resolve())
    except Exception:
        raw_dump = None

    # check exports directory for JSON files containing this id
    try:
        exports_dir = Path(os.getenv('EXPORTS_DIR', '/app/exports'))
        if exports_dir.exists() and exports_dir.is_dir():
            for p in exports_dir.glob('*.json'):
                try:
                    txt = p.read_text(encoding='utf-8')
                    if id_str in txt:
                        export_files.append(str(p.resolve()))
                except Exception:
                    continue
    except Exception:
        pass

    # check MongoDB collections
    try:
        client = pymongo.MongoClient(mongo_uri)
        db = client.get_database(mongo_db)
        if db.get_collection('contents').find_one({'_id': ObjectId(id_str)}):
            in_contents = True
        if db.get_collection('contents_queue').find_one({'_id': ObjectId(id_str)}):
            in_queue = True
        try:
            client.close()
        except Exception:
            pass
    except Exception as e:
        logger.warning(f"MongoDB 접근 불가(저장 상태 확인 실패): {e}")

    return {
        'in_contents': in_contents,
        'in_queue': in_queue,
        'export_files': export_files,
        'raw_dump': raw_dump
    }
    
    logger.info("\n3. 요약 결과만 보기:")
    logger.info("   db.contents.find({")
    logger.info("     _id: { $in: [")
    for doc in docs:
        logger.info(f'       ObjectId("{doc["_id"]}"),')
    logger.info("     ]}")
    logger.info("   }, {")
    logger.info("     title: 1,")
    logger.info("     'contentsMeta.summary': 1,")
    logger.info("     'contentsMeta.sentiment.positive': 1")
    logger.info("   }).pretty()")


def save_results_to_json(results: List[Dict], output_file: str = None):
    """
    결과를 JSON 파일로 저장
    
    Args:
        results: 처리 결과 리스트
        output_file: 출력 파일명 (None이면 자동 생성)
    """
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 모델 이름을 파일명에 추가
        try:
            model_name = CONF.OLLAMA_MODEL.replace(':', '-').replace('/', '-')  # 특수문자 치환
            output_file = f"{model_name}_llm_evaluation_results_{timestamp}.json"
        except Exception:
            output_file = f"llm_evaluation_results_{timestamp}.json"
    path = Path(output_file).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    abs_path = str(path.resolve())
    print(f"\n💾 결과 저장됨: {abs_path}")
    return abs_path


def _serialize_datetime(obj):
    """재귀적으로 datetime 객체를 문자열로 변환"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: _serialize_datetime(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_serialize_datetime(item) for item in obj]
    else:
        return obj


def save_recent_contents_snapshot(limit: int = 3, logger=None, model_name: str = None):
    """
    MongoDB `contents` 컬렉션에서 최신 `limit`건을 조회하여
    스냅샷 JSON 파일로 저장합니다. 반환값은 저장된 파일 경로 문자열입니다.

    Uses environment variables `MONGO_URI` and `MONGO_DB`.
    
    Args:
        limit: 조회할 문서 개수
        logger: Logger 인스턴스
        model_name: LLM 모델 이름 (파일명에 포함)
    """
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://ksubscribe_mongodb:27017')
    mongo_db = os.getenv('MONGO_DB', 'mycontents')
    client = None
    try:
        client = pymongo.MongoClient(mongo_uri)
        db = client.get_database(mongo_db)
        coll = db.get_collection('contents')

        cursor = coll.find({}, projection=None).sort([
            ("metaAnalyzeDt", -1),
            ("rawCollectDt", -1)
        ]).limit(limit)

        docs = []
        for d in cursor:
            # 재귀적으로 datetime/ObjectId 직렬화
            serialized_doc = _serialize_datetime(d)
            docs.append(serialized_doc)

        # 모델 이름 정리 (파일명에 사용하기 적합하게)
        if model_name:
            safe_model_name = model_name.replace(':', '-').replace('/', '_')
        else:
            safe_model_name = 'unknown'

        payload = {
            'meta': {
                'created_at': datetime.utcnow().isoformat(),
                'model': model_name or 'unknown',
                'count': len(docs),
            },
            'docs': docs
        }

        # 저장 경로: 모델명_날짜_시간.json
        result_dir = SCRIPT_DIR / 'result'
        result_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{safe_model_name}_{timestamp}.json"
        filepath = result_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        return str(filepath.resolve())

    except Exception as e:
        if logger:
            logger.error(f"최근 contents 스냅샷 생성 실패: {e}")
        raise
    finally:
        if client:
            try:
                client.close()
            except Exception:
                pass


def main():
    """메인 함수"""
    
    # argparse 설정
    parser = argparse.ArgumentParser(
        description='LLM 모델 평가 테스트 스크립트',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 기본 3개 문서 평가
  python3 test_llm_evaluation.py
  
  # 파일에서 ID 목록 읽기
  python3 test_llm_evaluation.py --test-ids test_ids.txt
  
  # 직접 ID 입력 (쉼표로 구분)
  python3 test_llm_evaluation.py --test-ids "68edc849ae3da00bfe2d0cef,68edc849ae3da00bfe2d0cf3"
  
  # Queue 유지 모드 (재실행 가능)
  python3 test_llm_evaluation.py --test-ids test_ids.txt --keep-queue
  
  # 상세 로그 + JSON 결과 저장
  python3 test_llm_evaluation.py --test-ids test_ids.txt --verbose --save-json results.json
        """
    )
    
    parser.add_argument(
        '--test-ids',
        type=str,
        required=True,
        help='(필수) 테스트할 문서 ID (파일 경로나 쉼표 구분 ID 목록)'
    )
    
    parser.add_argument(
        '--keep-queue',
        action='store_true',
        help='처리 후에도 contents_queue에서 문서를 삭제하지 않음 (재실행 가능)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='상세 로그 출력 (MongoDB 결과 포함)'
    )
    
    parser.add_argument(
        '--save-json',
        type=str,
        metavar='FILE',
        help='결과를 JSON 파일로 저장 (예: results.json)'
    )

    parser.add_argument(
        '--dump-raw',
        nargs='?',
        const=DUMP_RAW_SENTINEL,
        metavar='DIR',
        help='원문 텍스트 덤프. 인자를 생략하면 콘솔 출력 + 기본 outputs 폴더(/app/.../test/outputs)에 저장하며, DIR을 지정하면 해당 경로에 저장합니다. "stdout"을 주면 출력만 수행합니다.'
    )

    parser.add_argument(
        '--ollama-model',
        type=str,
        metavar='MODEL',
        required=True,
        help='(필수) 실행할 Ollama 모델을 지정합니다. 예: "gpt-oss:20b" 또는 "llama-3-Korean-Bllossom-8B-Q4_K_M:latest".'
    )

    parser.add_argument(
        '--prompt-overrides',
        type=str,
        metavar='FILE',
        help='JSON 파일에서 특정 프롬프트 문자열을 덮어씁니다. 예시: {"question_summary": "..."}'
    )
    
    parser.add_argument(
        '--yaml-prompt',
        type=str,
        metavar='FILE',
        help='YAML 프롬프트 파일 경로. 지정하면 해당 YAML 파일의 프롬프트를 사용합니다.'
    )
    
    args = parser.parse_args()
    
    # Logger 설정
    logger = Logger().setup_logger(Logger.docker_scraping_result_logger_name)
    
    # 시작 메시지
    logger.info("=" * 80)
    logger.info("🚀 LLM 모델 평가 테스트 시작")
    logger.info("=" * 80)
    logger.info(f"실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"옵션:")
    logger.info(f"  - Queue 유지: {args.keep_queue}")
    logger.info(f"  - 상세 로그: {args.verbose}")
    logger.info(f"  - JSON 저장: {args.save_json or 'No'}")
    logger.info(f"  - YAML 프롬프트: {getattr(args, 'yaml_prompt', 'No') or 'No'}")
    dump_mode_desc = "No"
    dump_config = resolve_dump_config(args.dump_raw)
    if dump_config:
        if dump_config.get("dir"):
            dump_mode_desc = f"stdout + {dump_config['dir']}"
        else:
            dump_mode_desc = "stdout"
    logger.info(f"  - 원문 덤프: {dump_mode_desc}")
    logger.info(f"  - 프롬프트 오버라이드: {args.prompt_overrides or 'No'}")

    prompt_overrides: Optional[Dict[str, str]] = None
    if args.prompt_overrides:
        try:
            prompt_overrides = load_prompt_overrides_file(args.prompt_overrides)
            logger.info(f"🧪 프롬프트 오버라이드 로드 완료 ({len(prompt_overrides)}개) : {Path(args.prompt_overrides).expanduser()}")
        except Exception as e:
            logger.error(f"❌ 프롬프트 오버라이드 로드 실패: {e}")
            return 1

    initial_gpu_status: Optional[bool] = None
    final_gpu_status: Optional[bool] = None
    
    # 1. 테스트 ID 목록 결정 (--test-ids 필수)
    try:
        test_ids = parse_test_ids_argument(args.test_ids)
    except Exception as e:
        logger.error(f"❌ ID 파싱 오류: {e}")
        return 1
    
    if len(test_ids) == 0:
        logger.error("❌ 테스트할 문서 ID가 없습니다.")
        return 1
    
    logger.info(f"✅ 테스트 대상: {len(test_ids)}개 문서\n")
    
    # 2. Ollama 서버 시작
    # If the user passed an explicit model, override environment/config for this run
    if getattr(args, 'ollama_model', None):
        sel = args.ollama_model.strip()
        logger.info(f"🔁 테스트용 Ollama 모델 오버라이드: {sel}")
        # set environment variable used by some modules
        os.environ['OLLAMA_MODEL'] = sel
        # try to update local config module if present
        try:
            CONF.OLLAMA_MODEL = sel
            logger.info("✅ ksubscribe_share.config.OLLAMA_MODEL 업데이트 완료")
        except Exception:
            logger.info("⚠️ ksubscribe_share.config 모듈을 업데이트할 수 없음(존재하지 않거나 오류)")

    logger.info("ℹ️ 모델 상태 확인은 생략합니다 (처리 후 자동 초기화 가정).")

    checker = OllamaAlive(op_mode="docker_server", keep_alive=False)
    checker.start_thread()
    logger.info("✅ Ollama 서버 연결 완료\n")
    initial_gpu_status = log_gpu_status("테스트 시작 직전 GPU 상태", logger)
    
    try:
        # 3. MongoDB에서 문서 조회
        docs = fetch_documents_from_queue(test_ids, logger)
        
        if len(docs) == 0:
            logger.error("❌ Queue에서 문서를 찾을 수 없습니다.")
            logger.info("\n💡 Tip: Queue에 문서가 없다면 먼저 수집을 실행하세요:")
            logger.info("   python3 docker_shell/main_collect_and_scrapping.py")
            return 1
        
        # 4. 스크래핑 및 LLM 분석
        results, scraper = process_documents(
            docs, 
            logger, 
            keep_queue=args.keep_queue,
            verbose=args.verbose,
            dump_config=dump_config,
            prompt_overrides=prompt_overrides,
            yaml_path=getattr(args, 'yaml_prompt', None),
        )
        
        # 5. 결과 요약 출력
        print_summary(results, scraper, logger)
        
        # 6. MongoDB 확인 명령어 출력
        print_mongodb_commands(docs, logger)
        
        # 7. JSON 저장 (선택적)
        if args.save_json:
            results_json_path = save_results_to_json(results, args.save_json)
            logger.info(f"📍 결과 JSON 저장 경로: {results_json_path}")
        else:
            logger.info("📝 --save-json 옵션이 없어 결과 JSON은 별도 저장하지 않았습니다.")

        logger.info("\n" + "=" * 80)
        logger.info("✅ LLM 평가 완료")
        logger.info("=" * 80)
        # 8. 처리 완료 후 contents 컬렉션에서 최신 문서 N건을 스냅샷으로 저장
        try:
            # 사용된 모델 이름 가져오기
            current_model = os.getenv('OLLAMA_MODEL', CONF.OLLAMA_MODEL if hasattr(CONF, 'OLLAMA_MODEL') else 'unknown')
            snapshot_path = save_recent_contents_snapshot(len(docs), logger, model_name=current_model)
            if snapshot_path:
                logger.info(f"💾 contents 최신 {len(docs)}건 스냅샷 저장: {snapshot_path}")
                logger.info(f"📍 스냅샷 JSON 절대경로: {snapshot_path}")
        except Exception as e:
            logger.warning(f"최근 contents 스냅샷 저장 실패: {e}")

        final_gpu_status = log_gpu_status("테스트 완료 후 GPU 상태", logger)

        return 0

    except Exception as e:
        logger.error(f"❌ 실행 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        final_gpu_status = log_gpu_status("오류 발생 직후 GPU 상태", logger)
        return 1
    
    finally:
        report_gpu_transition(initial_gpu_status, final_gpu_status, logger)
        checker.stop_thread()


if __name__ == "__main__":
    sys.exit(main())
