# pip install -q langchain-openai langchain playwright beautifulsoup4
# playwright install
# pip install langchain_community

from langchain_community.chat_models import ChatOllama

# LLM에게 전달해서 쉽게 정보 추출하기
import tracemalloc


tracemalloc.start()

class Emotion:
    def __init__ (self):    
        pass
    
    async def Emotion (self, content, org):
        # TimeStart = time.time()
        chat_ollama =  ChatOllama(model="llama3")#"llama3") #hf.co/MLP-KTLim/llama-3-Korean-Bllossom-8B-gguf-Q4_K_M:latest
        
        # emotion_analysis_ko = chat_ollama.predict(f"다음 내용이 삼성이라는 기관에 긍정적인지 부정적인지 감정을 분석하고 퍼센트와 같이 한글로 대답해줘 답변은 꼭 한글로만 해줘: {content}")
        emotion_analysis_ko = chat_ollama.predict(f"다음 내용에서 {org}에 대한 감정을 분석하고 답변은 다음 예시 '긍정적: 80%, 부정적: 10%, 중립적: 05% , 이유...'와 동일한 형식으로 해줘, 답변은 한글로만 해줘 : '{content}'")
        # emotion_analysis_ko = chat_ollama.predict(f"다음 내용이 긍정적인지 부정적인지 감정을 분석해줘 형식은 '긍정: 비율, 부정 : 비울, 중립: 비율, 이유'로 해줘 답변은 한글로만 해줘: {content}")
        
        # TimeEnd = time.time()
                
        # print("EmotionPredicTime : " +  str(TimeEnd -   TimeStart)+ '\n')


        return emotion_analysis_ko

    


