import yaml
import logging
from typing import Dict, Any, List
from langchain_ollama import ChatOllama
from ksubscribe_share.logger import Logger
import ksubscribe_share.config as CONF

class AnalysisOllamaBase2:
    """
    Pure YAML Pipeline Engine
    YAML 파일에 정의된 순서대로 프롬프트를 실행하고 결과를 전달하는 엔진 클래스
    """
    def __init__(self, config_path: str):
        self.logger = logging.getLogger("AnalysisOllamaBase2")
        self.config = self._load_config(config_path)
        
        # 모델에 따른 포맷 설정 (gpt-oss는 json 포맷 미지원)
        ollama_format = None if "gpt-oss" in CONF.OLLAMA_MODEL else "json"
        
        self.llm = ChatOllama(
            model=CONF.OLLAMA_MODEL,
            base_url=CONF.OLLAMA_URL,
            format=ollama_format
        )
        # 타임아웃 설정 (기본값보다 길게)
        if not self.llm.client_kwargs:
            self.llm.client_kwargs = {}
        self.llm.client_kwargs["timeout"] = 180

    def _load_config(self, path: str) -> Dict:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def run_pipeline(self, initial_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        YAML 파이프라인 실행
        :param initial_context: 초기 입력 데이터 (content, org_name 등)
        :return: 최종 실행 결과가 포함된 컨텍스트
        """
        print(f"DEBUG: Starting pipeline with context keys: {list(initial_context.keys())}")
        context = initial_context.copy()
        pipeline_steps = self.config.get('pipeline', [])
        prompts = self.config.get('prompts', {})

        for step in pipeline_steps:
            step_id = step['step_id']
            template_key = step['prompt_template']
            output_key = step['output_key']
            
            self.logger.info(f"Running step: {step_id}")
            print(f"DEBUG: Running step: {step_id}")

            # 1. 프롬프트 템플릿 가져오기
            if template_key not in prompts:
                raise ValueError(f"Prompt template '{template_key}' not found in config")
            template_str = prompts[template_key]

            # 2. 입력 변수 매핑 (input_mapping 처리)
            # 기본적으로 현재 context를 사용하되, mapping이 있으면 추가/덮어쓰기
            input_vars = context.copy()
            if 'input_mapping' in step and step['input_mapping']:
                for target_var, source_key in step['input_mapping'].items():
                    # 점(.) 표기법 지원 (예: sentiment_ratio_result.positiveRatio)
                    if "." in source_key:
                        parts = source_key.split(".")
                        value = context
                        found = True
                        for part in parts:
                            if isinstance(value, dict) and part in value:
                                value = value[part]
                            else:
                                found = False
                                break
                        
                        if found:
                            input_vars[target_var] = value
                        else:
                            self.logger.warning(f"Input mapping source '{source_key}' not found in context for step {step_id}")
                    
                    # 일반 키 접근
                    elif source_key in context:
                        input_vars[target_var] = context[source_key]
                    else:
                        self.logger.warning(f"Input mapping source '{source_key}' not found in context for step {step_id}")

            # 3. 프롬프트 포맷팅
            try:
                formatted_prompt = template_str.format(**input_vars)
            except KeyError as e:
                self.logger.error(f"Missing key for prompt formatting in step {step_id}: {e}")
                raise

            # 4. LLM 실행
            try:
                response = self.llm.invoke(formatted_prompt)
                result_content = response.content
            except Exception as e:
                self.logger.error(f"LLM execution failed at step {step_id}: {e}")
                raise

            # 5. 결과 파싱 및 저장
            import json
            import re
            import ast
            
            # JSON 파싱 시도 (format 설정과 무관하게 시도하여 구조화된 데이터 확보)
            try:
                # 1. 순수 JSON 파싱 시도
                parsed_result = json.loads(result_content)
                context[output_key] = parsed_result
            except json.JSONDecodeError:
                # 2. Markdown 코드 블록 또는 텍스트 내 JSON 추출 시도
                try:
                    cleaned_content = result_content.strip()
                    # ```json ... ``` 또는 ``` ... ``` 패턴 찾기
                    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned_content, re.DOTALL)
                    if match:
                        cleaned_content = match.group(1)
                    else:
                        # 그냥 { ... } 패턴 찾기 (가장 바깥쪽 중괄호)
                        match = re.search(r"(\{.*\})", cleaned_content, re.DOTALL)
                        if match:
                            cleaned_content = match.group(1)
                    
                    # 정리된 문자열로 다시 파싱 시도
                    parsed_result = json.loads(cleaned_content)
                    context[output_key] = parsed_result
                    self.logger.info(f"Step {step_id}: JSON parsed from text/markdown.")
                    
                except (json.JSONDecodeError, AttributeError):
                    # 3. ast.literal_eval 시도 (Single quotes 등 Python dict 형태인 경우)
                    try:
                        # 위에서 추출한 cleaned_content 재사용
                        parsed_result = ast.literal_eval(cleaned_content)
                        if isinstance(parsed_result, dict):
                            context[output_key] = parsed_result
                            self.logger.info(f"Step {step_id}: JSON parsed using ast.literal_eval.")
                        else:
                            raise ValueError("Not a dict")
                    except (ValueError, SyntaxError):
                        # 파싱 실패 시
                        self.logger.warning(f"Step {step_id}: Failed to parse JSON. Raw content preview: {result_content[:500]}")
                        context[output_key] = result_content
            
            self.logger.info(f"Step {step_id} completed. Output stored in '{output_key}'")

        return context
