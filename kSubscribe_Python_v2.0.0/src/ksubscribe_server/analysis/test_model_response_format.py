"""
gpt-oss:20b와 llama 모델 출력 형식 비교 테스트

사용법:
    docker exec ksubscribe_python_unified python3 /app/ksubscribe_server/analysis/test_model_response_format.py
"""

from langchain_ollama import ChatOllama
import ksubscribe_share.config as CONF
from ksubscribe_server.analysis.analysis_ollama_base import AnalysisOllamaBase


class ModelTester(AnalysisOllamaBase):
    """모델 출력 형식 테스트"""
    
    def __init__(self):
        self.test_content = "김천시와 한국전력공사 대구본부가 1인 가구 안부살핌 서비스를 위한 업무협약을 체결했다."
        self.test_keywords = "에너지, 전력, 재생에너지, 디지털, AI"
        self.models = ["gpt-oss:20b", "llama-3-Korean-Bllossom-8B-Q4_K_M:latest"]
    
    def test_model(self, model_name):
        """모델 테스트"""
        print(f"\n{'='*60}")
        print(f"모델: {model_name}")
        print(f"{'='*60}")
        
        try:
            chat_ollama = ChatOllama(model=model_name, base_url=CONF.OLLAMA_URL)
            chat_ollama.client_kwargs["timeout"] = 180
            chat_ollama._set_clients()
            
            prompt = self.question_verify.replace("pred_keywords_from_db", self.test_keywords).replace("[contents]", self.test_content)
            
            print("API 호출 중...")
            result = chat_ollama._client.generate(model=model_name, prompt=prompt)
            
            print(f"\n원본 응답:")
            print(f"{'-'*60}")
            print(result.response)
            print(f"{'-'*60}")
            
            return result.response
        except Exception as e:
            print(f"\n❌ 오류: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def compare(self):
        """두 모델 비교"""
        print(f"\n{'#'*60}")
        print(f"모델 응답 형식 비교 테스트")
        print(f"{'#'*60}")
        
        results = {}
        for model in self.models:
            results[model] = self.test_model(model)
        
        print(f"\n{'#'*60}")
        print(f"비교 완료")
        print(f"{'#'*60}")


if __name__ == "__main__":
    tester = ModelTester()
    tester.compare()