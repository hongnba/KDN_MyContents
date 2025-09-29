### **LangChain을 사용하여 HTML을 텍스트로 변환하는 방법**

https://medium.com/@garysvenson09/how-to-convert-html-to-text-with-langchain-tutorial-95a79812f66a

HTML 문서를 **일반 텍스트로 변환하는 과정**은 데이터 스크래핑부터 콘텐츠 분석까지 다양한 애플리케이션에서 중요한 작업이 될 수 있습니다. **LangChain**은 자연어 처리(NLP) 및 기타 데이터 작업을 효과적으로 조정할 수 있는 강력한 프레임워크로, HTML 콘텐츠를 텍스트로 변환하는 데 유용하게 사용할 수 있습니다.

이 글에서는 LangChain을 사용하여 **HTML을 텍스트로 변환하는 방법**을 다루며, 필요한 구성 요소, 단계별 가이드 및 실용적인 예제까지 함께 소개하겠습니다.

---

### **LangChain 이해하기**
HTML을 텍스트로 변환하는 구체적인 방법을 살펴보기 전에, 먼저 **LangChain이 무엇인지** 이해하는 것이 중요합니다. 

* **LangChain**은 **주로 언어 모델(Language Model)을 활용한 애플리케이션을 개발하기 위한 범용적인 프로그래밍 프레임워크**입니다. 
* 이 프레임워크는 다양한 구성 요소를 연결하는 기능을 제공하며, 대표적인 기능으로는 **문서 로더(Document Loaders)**, **텍스트 분할기(Text Splitters)** 및 **체인(Chains)**이 있습니다. 
* 이러한 기능들을 활용하면 대량의 데이터를 원활하게 처리할 수 있습니다.

* LangChain은 여러 NLP 작업에서 강력한 기능을 제공하지만, 특히 **HTML을 텍스트로 변환하는 기능**은 웹 스크래핑, 콘텐츠 재구성 등의 작업에서 매우 유용합니다. 
* HTML은 태그, 속성, 중첩된 구조를 포함하는 마크업 언어이므로, **효과적인 텍스트 변환을 통해 필요한 정보를 추출하는 것이 중요합니다.**

---

### **LangChain 환경 설정**
HTML을 텍스트로 변환하기 전에, 먼저 LangChain을 설치하고 환경을 설정해야 합니다. 아래 단계에 따라 LangChain을 사용할 준비를 해보겠습니다.

#### **1단계: 필요한 라이브러리 설치**
LangChain을 사용하려면 Python이 필요합니다. **Python 3.7 이상**이 설치되어 있는지 확인한 후, LangChain과 그 의존성(dependencies)을 설치하세요.

```bash
pip install langchain
```

LangChain은 단독으로 동작하는 것이 아니라, 보통 **BeautifulSoup**, **HTML parsing 라이브러리** 및 기타 NLP 관련 도구들과 함께 사용됩니다. 따라서, 추가적인 패키지도 설치하는 것이 좋습니다.

```bash
pip install beautifulsoup4
pip install lxml
```

이제 LangChain을 사용할 준비가 되었습니다. 다음 단계에서는 LangChain을 활용하여 HTML을 텍스트로 변환하는 방법을 구체적으로 살펴보겠습니다. 🚀

### HTML에서 텍스트 추출 및 LangChain을 활용한 처리 방법

#### 1단계: 필수 패키지 설치  
아래 명령어를 실행하여 필요한 라이브러리를 설치합니다.  
```bash
pip install langchain beautifulsoup4 requests
```
- `beautifulsoup4`: HTML 문서를 파싱하는 데 사용  
- `requests`: 웹 페이지의 HTML을 가져오는 데 사용  

---

#### 2단계: 필요한 모듈 임포트  
Python 스크립트 또는 Jupyter Notebook에서 아래 모듈을 임포트합니다.
```python
from langchain.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import LLMChain
from bs4 import BeautifulSoup
import requests
```

---

### HTML 가져오기

#### 3단계: HTML을 가져오는 함수 정의  
웹 페이지의 HTML을 가져오는 함수를 정의합니다.
```python
def fetch_html(url):
    response = requests.get(url)
    return response.text if response.ok else None
```
#### 4단계: 함수 사용하여 HTML 가져오기  
```python
url = 'https://example.com'
html_content = fetch_html(url)

if html_content:
    print("HTML content fetched successfully!")
else:
    print("Failed to fetch HTML content.")
```
위 함수는 주어진 URL에서 HTML을 가져와 `html_content` 변수에 저장합니다.

---

### HTML 파싱하여 텍스트 추출  

#### 5단계: HTML을 파싱하는 함수 정의  
BeautifulSoup을 사용하여 HTML에서 텍스트만 추출하는 함수입니다.
```python
def parse_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    return soup.get_text(strip=True)
```
#### 6단계: 함수 사용하여 텍스트 변환  
```python
html_content = fetch_html(url)
text_content = parse_html(html_content)

print(text_content)  # HTML 태그가 제거된 순수 텍스트 출력
```
이제 `text_content` 변수에 순수 텍스트가 저장됩니다.

---

### LangChain과 통합하여 텍스트 처리  

#### 7단계: 텍스트 로드  
LangChain의 `TextLoader`를 사용하여 텍스트 데이터를 문서 객체로 변환합니다.

```python
loader = TextLoader(text_content)
documents = loader.load()
```

#### 8단계: 텍스트를 작은 단위로 나누기  
LangChain의 `CharacterTextSplitter`를 사용하여 텍스트를 작은 덩어리로 분할합니다.
```python
text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
text_chunks = text_splitter.split_documents(documents)
```
- `chunk_size=1000`: 1,000자 단위로 분할  
- `chunk_overlap=100`: 100자씩 중첩되도록 분할  

이제 `text_chunks` 리스트에는 분할된 텍스트가 저장됩니다.

---

### LangChain을 이용한 NLP 처리

#### 9단계: 언어 모델 설정  
OpenAI의 GPT 모델을 사용하여 텍스트를 처리합니다.
```python
from langchain.llms import OpenAI

llm = OpenAI(model='gpt-3.5-turbo')
```

#### 10단계: 텍스트 요약 함수 정의  
LangChain의 `LLMChain`을 활용하여 텍스트를 요약합니다.
```python
def summarize_chunk(chunk):
    chain = LLMChain(llm=llm, input=chunk)
    summary = chain.run()
    return summary
```
#### 11단계: 텍스트 조각별 요약 수행  
```python
for chunk in text_chunks:
    summary = summarize_chunk(chunk)
    print(summary)
```
위 코드를 실행하면 텍스트가 작은 조각별로 요약됩니다.
---

### 예외 처리 및 오류 방지

#### 12단계: 네트워크 오류 처리  
HTML을 가져올 때 발생할 수 있는 네트워크 오류를 처리합니다.
```python
def fetch_html(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # HTTP 오류 발생 시 예외 발생
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None
```

#### 13단계: HTML이 유효한지 확인  
가져온 HTML이 비어 있거나 잘못된 경우를 방지하는 코드입니다.
```python
if html_content:
    text_content = parse_html(html_content)
    if text_content.strip():  # 공백 제거 후 텍스트가 있는지 확인
        print("Text content parsed successfully!")
    else:
        print("Parsed text is empty.")
else:
    print("Failed to fetch or parse HTML content.")
```

#### 14단계: HTML 파싱 오류 처리  
BeautifulSoup을 사용한 HTML 파싱이 실패할 경우 대비합니다.
```python
def parse_html(html):
    try:
        soup = BeautifulSoup(html, 'html.parser')
        return soup.get_text(strip=True)
    except Exception as e:
        print(f"Parsing error: {e}")
        return ""
```
이제 HTML이 잘못된 경우에도 프로그램이 비정상적으로 종료되지 않습니다.

---

### 마무리  

위 과정을 따르면:
1. 웹 페이지에서 HTML을 가져오고  
2. BeautifulSoup으로 텍스트만 추출한 뒤  
3. LangChain을 이용하여 텍스트를 분석하고 처리할 수 있습니다.  

이를 통해 웹 데이터를 NLP 모델에 활용하여 요약, 질의응답, 분류 등의 다양한 처리를 수행할 수 있습니다.