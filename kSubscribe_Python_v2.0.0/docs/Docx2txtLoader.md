
https://wikidocs.net/253711

---

# Docx2txtLoader

`Docx2txtLoader`는 `.docx` 파일을 문서로 불러오기 위해 `docx2txt` 라이브러리를 사용하는 로더입니다.

## 설치

먼저, `docx2txt` 라이브러리를 설치해야 합니다:

```bash
pip install -qU docx2txt
```

## 사용법

아래는 `Docx2txtLoader`를 사용하여 `.docx` 파일을 로드하는 예제입니다:

```python
from langchain_community.document_loaders import Docx2txtLoader

# 로더 초기화
loader = Docx2txtLoader("./data/sample-word-document.docx")

# 문서 로드
docs = loader.load()

# 로드한 문서의 개수 출력
print(len(docs))  # 출력: 1
```

위 코드는 지정한 경로의 `.docx` 파일을 로드하고, 로드한 문서의 개수를 출력합니다.

---

위 내용은 [위키독스의 '06. Word' 문서](https://wikidocs.net/253711)를 기반으로 작성되었습니다. 
