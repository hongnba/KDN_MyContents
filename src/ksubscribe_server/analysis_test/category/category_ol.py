# pip install -q langchain-openai langchain playwright beautifulsoup4
# playwright install
# pip install langchain_community

from langchain_community.chat_models import ChatOllama

# LLM에게 전달해서 쉽게 정보 추출하기
import tracemalloc


tracemalloc.start()

class Category:
    def __init__ (self):    
        pass
    
    async def Category (self, content):
        # TimeStart = time.time()
        chat_ollama =  ChatOllama(model="llama3")#"llama3") # hf.co/MLP-KTLim/llama-3-Korean-Bllossom-8B-gguf-Q4_K_M:latest
        
        #category_ko = chat_ollama.predict(f"다음 내용을 정치, 경제, 과학, 교육 의 카테고리 중 어떤 것과 가장 연관성이 놓은 카테고리를 한 단어로 대답해줘 답변은 한글로만 해줘: {content}")
        category_ko = chat_ollama.predict(f"다음 내용을 정치, 경제, 과학, 교육 의 카테고리 중 어떤 것과 가장 연관성이 높은지 분석하고 답변은 다음 예시 '정치 : 80%, 경제 : 20%'와 동일한 형식으로 해줘, 답변은 한글로만 해줘  : '{content}' ")

        # TimeEnd = time.time()               
        # print("CategoryPredicTime : " +  str(TimeEnd -   TimeStart)+ '\n')
        
        return category_ko
    


    


