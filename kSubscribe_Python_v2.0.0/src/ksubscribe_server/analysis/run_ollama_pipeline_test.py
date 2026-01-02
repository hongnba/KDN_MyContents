import sys
import os
import logging
import json

# Add src to path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from ksubscribe_server.analysis.analysis_ollama_base2 import AnalysisOllamaBase2
from ksubscribe_server.analysis.analysis_ollama_base3 import AnalysisOllamaBase3

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PipelineTest")

def test_pipeline():
    # Sample Input
    sample_context = {
        "content": """
        (서울=연합뉴스) 인공지능(AI) 기술이 급격히 발전하면서 전력 소비량이 급증하고 있다. 
        이에 따라 에너지 효율화 기술에 대한 관심이 높아지고 있으며, 한전KDN은 이러한 흐름에 맞춰 
        AI 기반의 전력 관리 시스템을 고도화하고 있다. 
        특히 스마트 그리드와 연계한 지능형 전력망 구축에 박차를 가하고 있다.
        """,
        "pred_keyword_list": ["AI", "에너지", "전력", "효율화"],
        "org_name": "한전KDN"
    }

    base_dir = os.path.dirname(__file__)
    
    # 1. Test Custom YAML Pipeline (Base2)
    logger.info("=== Testing Custom YAML Pipeline (Base2) ===")
    config_path_2 = os.path.join(base_dir, "prompts/pipeline_custom.yaml")
    try:
        engine2 = AnalysisOllamaBase2(config_path_2)
        result2 = engine2.run_pipeline(sample_context)
        logger.info("Base2 Execution Completed Successfully")
        logger.info(f"Result Keys: {list(result2.keys())}")
        if "summary_result" in result2:
            logger.info(f"Summary Result: {json.dumps(result2['summary_result'], ensure_ascii=False, indent=2)}")
    except Exception as e:
        logger.error(f"Base2 Failed: {e}", exc_info=True)

    # 2. Test Hybrid LangChain Pipeline (Base3)
    logger.info("\n=== Testing Hybrid LangChain Pipeline (Base3) ===")
    config_path_3 = os.path.join(base_dir, "prompts/pipeline_hybrid.yaml")
    try:
        engine3 = AnalysisOllamaBase3(config_path_3)
        result3 = engine3.run_pipeline(sample_context)
        logger.info("Base3 Execution Completed Successfully")
        logger.info(f"Result Keys: {list(result3.keys())}")
        if "summary_result" in result3:
            logger.info(f"Summary Result: {json.dumps(result3['summary_result'], ensure_ascii=False, indent=2)}")
    except Exception as e:
        logger.error(f"Base3 Failed: {e}", exc_info=True)

if __name__ == "__main__":
    test_pipeline()
