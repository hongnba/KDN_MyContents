# pip install -q langchain-openai langchain playwright beautifulsoup4
# playwright install
# pip install langchain_community

from langchain_community.chat_models import ChatOllama

# LLM에게 전달해서 쉽게 정보 추출하기
import tracemalloc


tracemalloc.start()

class Keyword:
    def __init__ (self):    
        pass
    
    async def Keyword (self, content):
        # TimeStart = time.time()
        chat_ollama =  ChatOllama(model="llama3")#"llama3") #hf.co/MLP-KTLim/llama-3-Korean-Bllossom-8B-gguf-Q4_K_M:latest
        
        #keyword_ko = chat_ollama.predict(f"다음 내용을 대표하는 키워드 세가지 단어를 선택해줘 답변은 한글로만 해줘: {content}")
        keyword_ko = chat_ollama.predict(f"다음 내용을 대표하는 키워드 세가지 단어를 선택해줘 답변은 다음 예시 '구름', '하늘', '바다'와 동일한 형식으로 해줘, 답변은 한글로만 해줘 : '{content}' ")

        # TimeEnd = time.time()
                
        # print("KeywordPredicTime : " +  str(TimeEnd -   TimeStart)+ '\n')


        return keyword_ko

    


