from langchain_community.chat_models import ChatOllama
import ksubscribe_share.config as CONF

class OllamaSummarize:
    
    def __init__(self):
        # 하드코딩된 기존 설정 (보관용 주석):
        # self.chat_ollama =  ChatOllama(model="EEVE-Korean-10.8B")  #/llama-3-Korean-Bllossom-8B-gguf-Q4_K_M:latest

        # 설정 파일의 값을 사용하도록 변경
        self.chat_ollama = ChatOllama(model=CONF.OLLAMA_MODEL, base_url=CONF.OLLAMA_URL)

    def messages_to_prompt(self, messages):
        prompt = []
        for msg in messages:
            if msg["role"] == "system":
                prompt.append(f"System: {msg['content']}")
            elif msg["role"] == "user":
                prompt.append(f"User: {msg['content']}")
        return "\n".join(prompt)
        
    def summarize_chunk(self, chunk):
        """
        각 청크를 GPT-4o API에 보내 요약
        """
        try:
            messages=[
                {"role": "system", "content": "주어진 텍스트를 간결하고 핵심적으로 요약해주세요."},
                {"role": "user", "content": chunk},
            ]
            llm_question = self.messages_to_prompt(messages)
                            
            invoke_result = self.chat_ollama.invoke(llm_question)
            return invoke_result.content.strip()
        except Exception as e:
            print(f"Error during summarization: {e}")
            return None
        
     