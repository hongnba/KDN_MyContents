이 코드가 단순히 **문서를 읽고 질문을 던지는 방식**과 차이가 있는 이유는 **문서 임베딩 및 검색 기반 질의응답 시스템(RAG, Retrieval-Augmented Generation)**을 사용하기 때문입니다.  

---

## **📌 주요 차이점**
| 방식 | 차이점 |
|------|----------------|
| **그냥 문서 내용을 읽고 질문** | - 문서를 전부 LLM에 입력한 후 요약 또는 답변 요청<br>- 대용량 문서일 경우, LLM의 토큰 제한 문제 발생<br>- 문서의 중요한 부분이 빠질 가능성 있음 |
| **RAG (Retrieval-Augmented Generation) 방식** | - 문서를 임베딩하여 **유사도 검색** 가능<br>- 질문과 연관된 부분만 검색해 LLM에 전달<br>- 메모리 및 성능 최적화 가능 |

---

## **🔍 차이점 상세 분석**
### **1. 그냥 문서를 읽어서 질문하는 방식**
- PDF 문서를 **그대로** LLM에게 전달하여 질문을 수행
- 한 번에 전체 문서를 모델에게 보내야 함
- 문서가 길면 **토큰 제한 문제** 발생 (예: GPT-4o의 입력 최대 토큰 수 초과)
- 중요한 내용이 중간에 있으면, 모델이 해당 내용을 인식하지 못할 가능성 있음
- LLM의 **비용 및 속도** 측면에서 비효율적

📌 **단점**
- 문서가 길면 **LLM이 처리하지 못할 가능성이 큼**
- 모델이 문서를 압축해 요약하는 과정에서 중요한 내용을 놓칠 가능성이 있음
- 전체 문서를 한번에 처리해야 하므로 **비용이 증가**함

---

### **2. RAG 방식 (이 코드의 방식)**
#### ✅ **문서를 잘게 나누고 검색 후 질의응답**
- 문서를 **작은 조각(chunk)으로 나눈 후, 벡터 임베딩을 생성**  
- 유사도를 기반으로 **질문과 관련된 부분만 검색**  
- **검색된 부분만 LLM에게 전달**하여 답변을 생성  
- 즉, **필요한 정보만** 모델에 입력하므로 토큰 낭비가 없음

📌 **장점**
- **토큰 절약**: 문서 전체를 한 번에 보내지 않고, 질문과 관련된 부분만 전달  
- **검색 최적화**: 문서가 길어도 빠르게 원하는 정보 검색 가능  
- **확장 가능**: 여러 개의 문서를 처리할 때도 효율적  

---

## **🛠 예제 비교**
### **❌ 문서 전체를 읽고 요약하는 방식 (비효율적)**
```python
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_openai import ChatOpenAI

# 문서 로드
loader = PyMuPDFLoader("data/SPRI_AI_Brief_2023년12월호_F.pdf")
docs = loader.load()

# 전체 문서 내용을 하나의 문자열로 결합
full_text = "\n".join([doc.page_content for doc in docs])

# LLM을 사용하여 요약 요청
llm = ChatOpenAI(model_name="gpt-4o", temperature=0)

summary = llm.invoke(f"이 문서를 요약해 주세요: {full_text}")
print(summary)
```
✅ **문제점**:  
- 문서가 길면 **GPT 모델의 최대 토큰 수를 초과할 가능성**이 큼  
- 모든 텍스트를 한꺼번에 넣기 때문에 **비용이 비쌈**  
- 문서의 특정 부분만 필요해도, 전체 문서를 모델이 읽어야 함  

---

### **✅ RAG 방식을 활용한 검색 + 질의응답 (효율적)**
```python
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# 1. 문서 로드
loader = PyMuPDFLoader("data/SPRI_AI_Brief_2023년12월호_F.pdf")
docs = loader.load()

# 2. 문서 분할
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=50)
split_documents = text_splitter.split_documents(docs)

# 3. 문서 임베딩 및 벡터 DB 저장
embeddings = OpenAIEmbeddings()
vectorstore = FAISS.from_documents(documents=split_documents, embedding=embeddings)

# 4. 검색기 생성
retriever = vectorstore.as_retriever()

# 5. 프롬프트 템플릿 정의
prompt = PromptTemplate.from_template(
    """You are an assistant for question-answering tasks. 
Use the following pieces of retrieved context to answer the question. 
If you don't know the answer, just say that you don't know. 
Answer in Korean.

#Context: 
{context}

#Question:
{question}

#Answer:"""
)

# 6. LLM 및 체인 생성
llm = ChatOpenAI(model_name="gpt-4o", temperature=0)
chain = (
    {"context": retriever, "question": lambda x: x}
    | prompt
    | llm
)

# 7. 질문 실행
question = "삼성전자가 자체 개발한 AI의 이름은?"
response = chain.invoke(question)
print(response)
```
✅ **이 방식의 장점**:  
- **LLM이 직접 모든 문서를 읽지 않고, 필요한 부분만 검색해서 처리**  
- **토큰 사용량 절감 → 비용 절감**  
- **속도가 빠름 → 불필요한 정보를 처리하지 않음**  

---

## **🧐 결론**
- 그냥 문서를 읽고 질문하는 방식은 **비효율적** (전체 문서를 한 번에 LLM에 입력해야 하므로 비용과 처리량 문제 발생)  
- **RAG 방식 (이 코드의 방식)이 훨씬 효율적**  
  - 문서를 임베딩하고 필요한 부분만 검색  
  - 검색된 텍스트만 LLM에 전달 → 토큰 절약 및 성능 향상  
  - 대량의 문서에도 확장 가능  

### **📌 추천 방식**
✔ **질의응답(Q&A) → RAG 방식 사용**  
✔ **요약(Summary) → 문서 분할 후 요약**  
✔ **대량 문서 처리 → 벡터 검색 활용**  

**즉, 이 코드가 단순히 문서를 읽고 질문하는 방식과 다른 점은, 문서를 효율적으로 나누고, 질문에 맞는 정보를 검색해서 답변을 생성하는 최적화된 방식이기 때문입니다.** 🚀


---
---
RAG(Retrieval-Augmented Generation) 방식으로 문서를 처리하면 **LLM에 전달하는 입력 토큰 수가 제한을 초과할 가능성이 크게 줄어듭니다.** 하지만 **완전히 방지되는 것은 아닙니다.**  
RAG 방식에서도 토큰 제한을 초과할 수 있는 경우가 있으므로 **적절한 설계와 추가적인 최적화가 필요합니다.**  

---

## **1️⃣ RAG 방식이 토큰 초과 문제를 해결하는 이유**
일반적으로 **LLM에 직접 문서 전체를 입력하는 방식**은 다음과 같은 문제를 가집니다:
- 문서가 길 경우 **토큰 제한(예: GPT-4o는 최대 약 128K 토큰)**을 초과할 수 있음
- 모델이 불필요한 내용을 읽게 되어 **비용이 증가**하고 **응답 속도가 느려짐**

**RAG 방식은 이러한 문제를 해결하기 위해 다음과 같은 과정으로 작동합니다:**
1. **문서를 작은 조각(Chunk)으로 나눔** → (`chunk_size=1000` 등 설정 가능)
2. **사용자의 질문과 관련된 부분만 검색(Retrieval)**
3. **검색된 내용만 LLM에 입력** → **불필요한 정보 배제 → 토큰 사용량 절감**

✅ **이 과정 덕분에 전체 문서를 한 번에 넣지 않아도 되므로 토큰 초과 가능성이 낮아짐**  

---

## **2️⃣ RAG에서도 토큰 초과가 발생할 수 있는 경우**
하지만 **RAG 방식이라고 해서 절대적으로 토큰 초과가 발생하지 않는 것은 아닙니다.**  
다음과 같은 경우에는 여전히 토큰 제한 문제가 발생할 수 있습니다:

### **1) 검색된 문서 조각이 너무 많을 경우**
- RAG는 질문과 관련된 `N`개의 문서 조각(Chunk)을 검색하여 LLM에 전달
- 하지만 검색된 문서가 많으면 이 텍스트를 모두 합쳐도 **LLM의 입력 토큰 한도를 초과할 가능성이 있음**  
  (예: GPT-4o의 최대 입력 128K 토큰 초과)

✅ **해결 방법**
- **검색된 Chunk 개수 제한** (`retriever = vectorstore.as_retriever(search_kwargs={"k": 5})`)
- 너무 많은 정보가 검색되지 않도록 **임베딩 품질 조정**
- 필요하다면 검색된 조각들을 다시 요약하여 크기를 줄이는 추가적인 과정 추가  

---

### **2) 개별 Chunk 크기가 너무 클 경우**
- Chunk 크기를 너무 크게 설정하면 검색된 문서 조각 하나만으로도 **토큰 제한을 초과할 수 있음**
- 특히, `chunk_size=5000` 같은 큰 값으로 설정하면 검색된 단일 Chunk만으로도 문제가 발생할 가능성이 있음

✅ **해결 방법**
- **적절한 `chunk_size` 값 설정** (`chunk_size=1000` 권장, 필요하면 더 작게 설정)
- `chunk_overlap`을 적절히 설정하여 내용 연결성을 유지 (`chunk_overlap=50` 정도)

---

### **3) 프롬프트에 포함된 텍스트가 많을 경우**
- RAG의 프롬프트에 **검색된 문서 조각 + 사용자 질문**이 포함됨  
- 이 프롬프트가 너무 길면 **토큰 초과 가능성 존재**

✅ **해결 방법**
- 검색된 문서 조각 개수를 조절 (`k=3~5`)
- 검색된 문서를 추가적으로 요약 (`summarize()` 기능 추가 가능)
- 프롬프트 자체를 최적화하여 불필요한 문구 제거

---

## **3️⃣ RAG의 토큰 초과 방지를 위한 최적화 방법**
RAG를 사용할 때 토큰 초과를 완벽히 방지하려면 **다음과 같은 전략을 활용**해야 합니다.

### ✅ **1) Chunk 크기 최적화**
```python
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=50)
split_documents = text_splitter.split_documents(docs)
```
- 너무 큰 `chunk_size`는 피해야 함 (`5000` 이상은 위험)
- `chunk_overlap`을 설정하여 문맥 연결성 유지  

---

### ✅ **2) 검색된 Chunk 개수 제한**
```python
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})  # 최대 5개의 Chunk만 검색
```
- 너무 많은 검색 결과가 나오지 않도록 제한  
- 필요하면 `k=3~5`로 설정하여 최적화  

---

### ✅ **3) 검색된 문서를 LLM에 전달하기 전에 추가 요약**
```python
from langchain_core.runnables import RunnableMap

# 검색된 문서 조각을 추가로 요약하는 체인 생성
summarize_chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

# 질문 실행
question = "삼성전자가 자체 개발한 AI의 이름은?"
response = summarize_chain.invoke(question)
print(response)
```
- 검색된 문서가 너무 길 경우, **한 번 더 요약하여 토큰 수를 줄임**
- LLM이 핵심 내용을 빠르게 이해할 수 있도록 최적화

---

### ✅ **4) 프롬프트 최적화 (불필요한 문구 제거)**
```python
prompt = PromptTemplate.from_template(
    """You are an assistant for question-answering tasks. 
Use the retrieved context below to answer concisely. 
If unsure, say 'I don't know'. Answer in Korean.

# Context: 
{context}

# Question:
{question}

# Answer:"""
)
```
- 프롬프트를 최소한의 문구로 최적화  
- `context` 크기를 줄이고 질문을 짧게 유지  

---

## **4️⃣ 결론**
🚀 **RAG 방식을 사용하면 문서 전체를 LLM에 넣지 않아도 되므로 토큰 초과 가능성이 줄어듭니다.**  
하지만 **완전히 방지되는 것은 아니며**, 아래의 최적화 기법을 적용해야 합니다:

✔ **Chunk 크기 최적화 (`chunk_size=1000` 추천)**  
✔ **검색된 Chunk 개수 제한 (`retriever.as_retriever(search_kwargs={"k": 5})`)**  
✔ **검색된 문서를 요약하여 전달 (LLM이 처리할 수 있도록 압축)**  
✔ **프롬프트를 최적화하여 불필요한 정보 제거**  

💡 **이러한 전략을 적용하면 토큰 초과를 방지하면서도 RAG의 장점을 최대한 활용할 수 있습니다!** 🚀