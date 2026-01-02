# LLM 분석 아키텍처 리뷰 및 실험 관리 가이드

본 문서는 `AnalysisOllamaGenerateCall` 및 `AnalysisOllamaBase` 클래스의 구조적 질문에 대한 답변과, 향후 프롬프트 실험 및 로직 변경을 체계적으로 관리하기 위한 가이드를 제공합니다.

---

## 1. AnalysisOllamaBase 클래스 구조 리뷰

### 질문
> `AnalysisOllamaBase` 클래스는 생성자(`__init__`)도 없고 속성도 없는데, 상속받아서 사용해도 괜찮은가?

### 분석 결과
**결론: 현재 구조는 Python의 문법적으로 유효하며, "Mixin" 또는 "Configuration Class" 패턴으로 작동하고 있습니다.**

1.  **작동 원리**:
    *   `AnalysisOllamaBase`에 정의된 `question_summary`, `answer_template` 등은 **클래스 속성(Class Attributes)**입니다.
    *   Python에서 클래스 속성은 인스턴스 생성(`__init__`) 없이도 `self.속성명`으로 접근할 수 있습니다.
    *   `AnalysisOllamaGenerateCall`이 이를 상속받았으므로, `AnalysisOllamaGenerateCall`의 인스턴스(`self`)는 부모 클래스의 모든 클래스 속성에 접근 가능합니다.

2.  **장점**:
    *   구현이 매우 간단합니다.
    *   모든 인스턴스가 동일한 프롬프트 템플릿을 공유하므로 메모리 효율적입니다.

3.  **단점**:
    *   **유연성 부족**: 실행 시점(Runtime)에 프롬프트를 동적으로 변경하거나, 인스턴스별로 다른 설정을 주입하기 어렵습니다.
    *   **테스트 어려움**: 프롬프트가 코드에 하드코딩되어 있어, 다른 프롬프트로 테스트하려면 코드를 수정해야 합니다.

### 권장 사항
현재 단계에서는 기능상 문제가 없으므로 그대로 사용해도 무방합니다. 단, 향후 **실험 관리**를 위해 프롬프트를 외부 파일(JSON/YAML)로 분리하거나, 생성자에서 설정 객체(Config Object)를 주입받는 방식으로 리팩토링하는 것을 권장합니다.

---

## 2. analysis_main_test 메소드 사용처 분석

### 질문
> `analysis_main_test` 메소드는 어디서 사용되고 있는가?

### 분석 결과
**결론: 현재 프로젝트 내에서 `analysis_main_test`를 호출하는 코드는 발견되지 않았습니다.**

*   **검색 범위**: 전체 워크스페이스 (`src/`, `docker_scraping/` 등 포함)
*   **결과**: `analysis_ollama_generate.py` 파일 내의 **정의(Definition)** 부분만 존재하며, 이를 호출(Call)하는 부분은 없습니다.
*   **추정**: 초기 개발 단계에서 테스트 용도로 작성되었으나, 현재는 사용되지 않는 **Dead Code**일 가능성이 높습니다.

### 권장 사항
*   혼란을 방지하기 위해 해당 메소드를 **삭제**하거나, `_deprecated_` 접두어를 붙여 사용하지 않음을 명시하는 것이 좋습니다.

---

## 3. 실험 재현성 및 복잡도 관리 방안 (Best Practices)

### 질문
> `analysis_main_3step` 등 새로운 실험을 할 때마다 코드가 복잡해지고, 이전 실험의 재현성이 떨어짐. 어떻게 관리해야 하는가?

### 문제점 진단
현재 방식은 **"코드 수정 = 실험 설정 변경"**이 동일하게 이루어지고 있어, 다음과 같은 문제가 발생합니다.
1.  **하드코딩된 프롬프트**: 프롬프트를 조금만 바꿔도 코드를 수정해야 함.
2.  **로직의 파편화**: `3step`, `5step`, `scenario2` 등 메소드가 계속 추가됨.
3.  **추적 불가**: 어떤 결과가 어떤 프롬프트/로직에서 나왔는지 나중에 알기 어려움.

### 해결 방안: "설정과 로직의 분리"

다음 3단계 전략을 제안합니다.

#### 전략 1: 프롬프트의 외부화 (Configuration)
프롬프트를 Python 코드(`AnalysisOllamaBase`)에서 분리하여 **JSON 또는 YAML 파일**로 관리합니다.

*   **구조 예시**:
    ```yaml
    # prompts/experiment_v1.yaml
    version: "1.0"
    prompts:
      summary: "다음 내용을 요약해줘: {content}"
      sentiment: "다음 내용의 감성을 분석해줘..."
    ```
*   **코드 변경**:
    ```python
    class AnalysisOllamaGenerateCall:
        def __init__(self, config_path="prompts/default.yaml"):
            self.config = load_yaml(config_path)
    
        def analysis_main(self, ...):
            prompt = self.config['prompts']['summary']
            # ...
    ```
*   **효과**: 코드를 수정하지 않고 YAML 파일만 교체하여 다양한 프롬프트 실험 가능.

#### 전략 2: 전략 패턴 (Strategy Pattern) 도입
분석 로직(3단계, 5단계, 시나리오2 등)을 하나의 클래스에 메소드로 계속 추가하지 말고, **별도의 클래스**로 분리합니다.

*   **구조 예시**:
    ```python
    # 인터페이스 정의
    class AnalysisStrategy(ABC):
        @abstractmethod
        def analyze(self, content, ...): pass

    # 구현체 1: 기존 5단계
    class Legacy5StepStrategy(AnalysisStrategy):
        def analyze(self, content, ...):
            # 기존 analysis_main 로직
            pass

    # 구현체 2: 신규 3단계
    class New3StepStrategy(AnalysisStrategy):
        def analyze(self, content, ...):
            # analysis_main_3step 로직
            pass
    ```
*   **실행 코드**:
    ```python
    # 실험 시 전략만 교체
    analyzer = AnalysisContext(strategy=New3StepStrategy())
    analyzer.run(...)
    ```

#### 전략 3: 실험 버전 관리 (Experiment Tracking)
실험 결과를 저장할 때, **어떤 설정(Config)과 어떤 전략(Strategy)**을 사용했는지 메타데이터를 함께 저장합니다.

*   **DB/로그 저장 시 추가 필드**:
    *   `experiment_id`: "EXP_20251210_3STEP_V2"
    *   `prompt_version`: "v2.1"
    *   `model_name`: "llama3"

### 요약 및 실행 가이드

당장 코드를 대대적으로 뜯어고치기 어렵다면, **"전략 1 (프롬프트 외부화)"**부터 작게 시작하는 것을 추천합니다.

1.  `prompts/` 폴더를 만들고 현재 `AnalysisOllamaBase`의 프롬프트들을 `default_prompts.json`으로 저장하세요.
2.  `AnalysisOllamaGenerateCall` 생성자에서 이 JSON을 로드하도록 수정하세요.
3.  새로운 실험을 할 때는 `experiment_A.json`을 만들고, 생성자에 파일 경로만 다르게 주면 코드는 그대로 둔 채 실험이 가능합니다.

---

## 4. 프롬프트 외부화 심화 FAQ

### Q1. 실험별 설정 파일에 공통 프롬프트를 중복해서 넣어도 괜찮은가?
> "실험1과 실험2에서 공통적으로 사용하는 프롬프트들도 각각 넣어야 할까? 용량 문제는 없나?"

**답변: 네, 중복해서 넣는 것을 강력히 권장합니다.**

1.  **실험의 독립성 (Isolation)**:
    *   만약 `common_prompts.yaml`을 만들어 공유한다면, 실험1을 위해 공통 프롬프트를 수정했을 때 의도치 않게 실험2의 결과가 변할 수 있습니다.
    *   실험 설정 파일은 그 자체로 **완전한 스냅샷(Snapshot)**이어야 합니다. 나중에 "실험1 당시의 설정"을 완벽하게 복원하려면 모든 내용이 하나의 파일에 있는 것이 유리합니다.
2.  **용량 문제 없음**:
    *   프롬프트 텍스트는 아무리 길어도 수 KB 수준입니다. 수천 개의 실험 파일을 만들어도 디스크 용량에는 거의 영향이 없습니다.
3.  **관리의 용이성**:
    *   `experiment_v1.yaml` 파일 하나만 열면 해당 실험의 모든 맥락을 파악할 수 있어 유지보수가 훨씬 쉽습니다.

### Q2. 프롬프트의 실행 순서도 외부 설정으로 정의할 수 있는가?
> "프롬프트 순서도 외부화를 통해 정의할 수 있나?"

**답변: 네, 가능하며 이를 통해 '파이프라인(Pipeline)' 구조를 만들 수 있습니다.**

단순히 프롬프트 텍스트만 저장하는 것이 아니라, **실행 단계(Steps)**를 리스트 형태로 정의하면 됩니다. 이를 지원하려면 코드가 순차적 실행(`step1() -> step2()`)에서 **반복적 실행(Loop)** 구조로 변경되어야 합니다.

#### 설정 파일 예시 (YAML)
```yaml
experiment_name: "3-Step Analysis V2"
pipeline:
  - step_id: "verify"
    prompt_template: "verify_prompt_v1"  # 아래 prompts 섹션의 키 참조
    output_key: "verification_result"
    
  - step_id: "summary"
    prompt_template: "summary_prompt_v2"
    input_mapping: 
      context: "verification_result" # 이전 단계 출력을 입력으로 사용
    output_key: "summary_result"

prompts:
  verify_prompt_v1: "다음 내용이 주제와 관련이 있는지 검증해줘: {content}"
  summary_prompt_v2: "다음 내용을 요약해줘: {content}"
```

### Q3. JSON vs YAML: 어떤 형식이 더 적합한가?
> "JSON은 주석을 넣기 어려운데 내가 모르는 건가? Java 개발자들은 YAML에 친숙한가?"

**답변: 프롬프트 관리에는 JSON보다 YAML을 강력히 추천합니다.**

1.  **주석 (Comments) 지원 여부**:
    *   **JSON**: 표준 JSON은 **주석을 지원하지 않습니다.** (`//`나 `#` 사용 불가). 주석을 넣으려면 비표준 파서(JSON5 등)를 써야 하거나, `_comment` 같은 더미 필드를 만들어야 해서 불편합니다.
    *   **YAML**: `#` 기호를 통해 **주석을 완벽하게 지원**합니다. 실험 설정 파일에 "왜 이 프롬프트를 썼는지" 설명을 적어두기에 매우 적합합니다.

2.  **멀티라인 문자열 (Multi-line Strings)**:
    *   **JSON**: 줄바꿈을 하려면 `\n`을 직접 넣어야 해서 프롬프트 가독성이 매우 떨어집니다.
    *   **YAML**: `|` 또는 `>` 문법을 사용하여 줄바꿈이 포함된 긴 텍스트(프롬프트)를 **있는 그대로 깔끔하게 작성**할 수 있습니다.

3.  **Java 개발자의 친숙도**:
    *   **매우 친숙함**: Java 생태계(Spring Boot, Kubernetes, GitHub Actions 등)에서 설정 파일의 표준으로 YAML이 널리 쓰입니다. Java 개발자라면 `application.yml` 등을 통해 이미 YAML에 익숙할 확률이 매우 높습니다.

**결론**: 프롬프트와 같이 "긴 텍스트"와 "설명(주석)"이 필요한 설정 파일에는 **YAML**이 최고의 선택입니다.

---

## 5. 파이프라인 구현 방식 비교: Custom YAML vs LangChain

### 질문
> "순서를 YAML로 관리하는 방식(Custom Pipeline)과 LangChain을 이용하는 방식의 장단점은? 그리고 현재 프로젝트에서 LangChain 사용이 가능한가?"

### 1. 현재 프로젝트의 LangChain 사용 가능 여부
**결론: 사용 가능합니다 (이미 사용 중).**

*   **확인된 사실**: `analysis_ollama_generate.py` 및 `analysis_ollama_base.py` 파일 상단에 이미 LangChain 관련 라이브러리가 임포트되어 있습니다.
    ```python
    from langchain_ollama import ChatOllama
    from langchain_core.prompts import ChatPromptTemplate
    ```
*   따라서 별도의 설치 없이 즉시 LangChain 기능을 활용할 수 있습니다.

### 2. 방식 비교: Custom YAML Pipeline vs LangChain (Code-based)

실험 관리와 유지보수 관점에서 두 가지 접근 방식을 비교합니다.

| 특징 | **A. Custom YAML Pipeline** (설정 파일 기반) | **B. LangChain LCEL** (코드 기반) |
| :--- | :--- | :--- |
| **구현 방식** | 실행 순서와 데이터 흐름을 **YAML 파일**에 정의하고, Python은 이를 해석하는 '엔진' 역할만 수행 | Python 코드 내에서 `chain = prompt | model | parser` 형태로 **체인 로직**을 직접 작성 |
| **실험 유연성** | **최상**. 코드 수정/배포 없이 YAML 파일만 바꿔서 순서 변경, 단계 추가/삭제 가능 | **중간**. 프롬프트 내용은 외부화 가능하지만, **실행 순서(로직)**를 바꾸려면 Python 코드를 수정해야 함 |
| **구현 난이도** | **높음**. YAML을 읽어서 순차적으로 실행하고 데이터를 전달하는 '파이프라인 엔진'을 직접 개발해야 함 | **낮음**. LangChain이 제공하는 `RunnablePassthrough`, `itemgetter` 등을 쓰면 데이터 전달이 매우 쉬움 |
| **가독성** | YAML 파일만 보면 전체 흐름 파악 가능 (비개발자도 이해 용이) | Python 코드를 읽어야 흐름 파악 가능 (개발자 친화적) |
| **디버깅** | 엔진 자체 버그가 아니면, 설정 파일 오류 찾기가 까다로울 수 있음 | Python 디버거를 통해 단계별 데이터 확인이 용이함 |

### 3. 추천 전략

**목표에 따른 선택 가이드:**

1.  **"나는 코드를 건드리지 않고 다양한 실험(순서 변경, 단계 추가)을 마구 해보고 싶다"**
    *   👉 **Custom YAML Pipeline** 추천
    *   초기에 '파이프라인 실행기(Runner)'를 만드는 비용이 들지만, 이후 실험 비용이 0에 수렴합니다.

2.  **"실험보다는 안정적인 서비스 개발이 우선이고, 순서가 자주 바뀌진 않는다"**
    *   👉 **LangChain (LCEL)** 추천
    *   표준화된 방식이며, 개발 속도가 빠르고 커뮤니티 지원을 받을 수 있습니다.

**절충안 (Hybrid):**
*   기본적으로 **LangChain**을 사용하여 각 단계(Step)의 실행 로직을 구현합니다.
*   이 단계들을 조합하는 **순서(Sequence)**만 **YAML**에서 읽어와서 동적으로 LangChain의 `Chain`을 구성하는 방식도 가능합니다. (가장 추천하는 고급 방식)
