import fitz  # PyMuPDF
from ksubscribe_server.summarize.gpt_summarize import GPTSummarize
from ksubscribe_server.summarize.ollama_summarize import OllamaSummarize
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from langchain_community.llms.ollama import Ollama
import ksubscribe_share.config as CONF
from langchain_community.embeddings import HuggingFaceEmbeddings

class PdfRAGSummarize:
    
    def __init__(self):
        self.gptSummarize = GPTSummarize()
        self.ollamaSummarize = OllamaSummarize()
        pass    

    def summarize_rag_pdf(self):

        # 1. 문서 로드
        loader = PyMuPDFLoader("data/20240902_로봇산업기술개발(로봇산업핵심기술개발)_V4.pdf")
        docs = loader.load()

        # 2. 문서 분할
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=50)
        split_documents = text_splitter.split_documents(docs)

        # 3. 문서 임베딩 및 벡터 DB 저장
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")  # 경량 & 속도 빠름
        vectorstore = FAISS.from_documents(documents=split_documents, embedding=embeddings)

        # 4. 검색기 생성
        retriever = vectorstore.as_retriever()

        # 5. 프롬프트 템플릿 정의
        prompt = PromptTemplate.from_template(
            """당신은 질문에 답변하는 AI 어시스턴트입니다. 
        다음 제공된 문맥을 활용하여 질문에 답하세요. 
        만약 답을 모른다면, 모른다고 답하세요. 
        답변은 한국어로 작성하세요.

        # 문맥:
        {context}

        # 질문:
        {question}

        # 답변:"""
        )

        # 6. Ollama LLM 및 체인 생성
        # 하드코딩된 기존 설정 (보관용 주석):
        # llm = Ollama(model="EEVE-Korean-10.8B")

        # 설정 파일의 값을 사용하도록 변경
        llm = Ollama(model=CONF.OLLAMA_MODEL, base_url=CONF.OLLAMA_URL)
        chain = (
            {"context": retriever, "question": lambda x: x}
            | prompt
            | llm
        )

        # 7. 질문 실행
        question = "문서의 내용을 요약해줘"
        response = chain.invoke(question)
        print(response)
    
     
if __name__ == "__main__":
    
    pdfRAGSummarize = PdfRAGSummarize()
    pdfRAGSummarize.summarize_rag_pdf()
    
         