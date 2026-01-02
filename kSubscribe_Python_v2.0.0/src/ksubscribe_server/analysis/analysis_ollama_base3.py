import yaml
import logging
from typing import Dict, Any, List
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableSerializable
from operator import itemgetter
import ksubscribe_share.config as CONF

class AnalysisOllamaBase3:
    """
    Hybrid LangChain Pipeline Engine
    YAML에서 순서를 읽어와 LangChain(LCEL) 체인을 동적으로 구성하여 실행
    """
    def __init__(self, config_path: str):
        self.logger = logging.getLogger("AnalysisOllamaBase3")
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

    def create_dynamic_chain(self) -> RunnableSerializable:
        """
        YAML 설정을 기반으로 LangChain Runnable 체인 생성
        """
        pipeline_steps = self.config.get('pipeline', [])
        prompts = self.config.get('prompts', {})
        
        # 초기 체인: 입력을 그대로 통과시킴
        chain = RunnablePassthrough()

        for step in pipeline_steps:
            step_id = step['step_id']
            template_key = step['prompt_template']
            output_key = step['output_key']
            
            if template_key not in prompts:
                raise ValueError(f"Prompt template '{template_key}' not found")
            
            template_str = prompts[template_key]
            prompt_template = ChatPromptTemplate.from_template(template_str)
            
            # 파서 선택
            if self.llm.format == "json":
                parser = JsonOutputParser()
            else:
                parser = StrOutputParser()

            # 입력 매핑 처리 (input_mapping)
            # 예: input_mapping: { "context": "verification_result" }
            # -> assign(context=itemgetter("verification_result"))
            input_mapper = RunnablePassthrough()
            if 'input_mapping' in step and step['input_mapping']:
                mapping_dict = {
                    target: itemgetter(source) 
                    for target, source in step['input_mapping'].items()
                }
                input_mapper = RunnablePassthrough.assign(**mapping_dict)

            # 개별 단계 체인 구성: (입력 State) -> Mapper -> Prompt -> LLM -> Parser -> (결과)
            step_chain = input_mapper | prompt_template | self.llm | parser
            
            # 전체 체인에 단계 추가 (assign을 사용하여 결과를 state에 누적)
            # output_key에 결과를 저장
            chain = chain | RunnablePassthrough.assign(**{output_key: step_chain})
            
            self.logger.info(f"Added step {step_id} to chain, output to '{output_key}'")

        return chain

    def run_pipeline(self, initial_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        구성된 LangChain 파이프라인 실행
        """
        chain = self.create_dynamic_chain()
        try:
            result = chain.invoke(initial_context)
            return result
        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {e}")
            raise
            
            # 1. 프롬프트 템플릿 생성
            prompt_template = ChatPromptTemplate.from_template(prompts[template_key])
            
            # 2. 개별 단계의 체인 구성 (Prompt -> LLM -> Parser)
            step_chain = (
                prompt_template 
                | self.llm 
                | JsonOutputParser()
            )
            
            # 3. 전체 체인에 단계 추가 (RunnablePassthrough.assign 사용)
            # assign을 사용하면 이전 단계의 결과(context)를 유지하면서 새로운 결과를 output_key에 추가함
            chain = chain | RunnablePassthrough.assign(**{output_key: step_chain})
            
        return chain

    def run_pipeline(self, initial_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        생성된 체인 실행
        """
        chain = self.create_dynamic_chain()
        try:
            result = chain.invoke(initial_context)
            return result
        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {e}")
            raise
