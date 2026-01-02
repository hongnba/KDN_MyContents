# Ollama API 타임아웃 에러 해결 방안

> 작성일: 2025-12-22  
> 에러: `httpcore.ReadTimeout: timed out`  
> 발생 위치: `question_summary` 프롬프트 실행 중

---

## 🔍 문제 분석

### 에러 내용
```
httpcore.ReadTimeout: timed out
File "/app/ksubscribe_server/analysis/analysis_ollama_generate.py", line 157
result_summary = self.chat_ollama._client.generate(...)
```

### 원인

1. **현재 Timeout 설정**: 180초
   ```python
   self.chat_ollama.client_kwargs["timeout"] = 180
   ```

2. **문제점**:
   - `client_kwargs["timeout"]`는 `ChatOllama` 초기화 시 사용되지만
   - `_client.generate()`를 직접 호출할 때는 이 설정이 적용되지 않을 수 있음
   - `_client`는 내부적으로 `ollama.Client`를 사용하며, 이는 별도의 httpx 클라이언트를 가짐
   - httpx 클라이언트의 timeout이 제대로 설정되지 않았을 가능성

3. **추가 요인**:
   - `short_summary2` 작업 지시 추가로 프롬프트가 더 길어짐
   - 모델이 느리거나 서버 부하가 높을 때 180초를 초과할 수 있음
   - `gpt-oss-20b` 같은 큰 모델은 처리 시간이 더 오래 걸림

---

## 💡 해결 방안

### 방안 1: Timeout 값 증가 + _client timeout 직접 설정 (권장)

**핵심**: `_client` 객체의 내부 httpx 클라이언트 timeout도 직접 설정

```python
def __init__(self):
    self.chat_ollama = ChatOllama(
        model=CONF.OLLAMA_MODEL,
        base_url=CONF.OLLAMA_URL, 
        format=(None if "gpt-oss" in CONF.OLLAMA_MODEL else "json")
    )
    
    self.keywords = PredefineKeywordService().getKeywordList()
    
    # Timeout 설정 (300초 = 5분)
    timeout_seconds = 300
    self.chat_ollama.client_kwargs["timeout"] = timeout_seconds
    self.chat_ollama._set_clients()
    
    # _client의 내부 httpx 클라이언트 timeout도 직접 설정
    try:
        # ollama.Client는 내부적으로 httpx.AsyncClient 또는 httpx.Client를 사용
        if hasattr(self.chat_ollama._client, '_client'):
            # httpx 클라이언트의 timeout 설정
            import httpx
            if isinstance(self.chat_ollama._client._client, httpx.Client):
                # httpx.Client의 timeout은 Timeout 객체로 설정
                self.chat_ollama._client._client.timeout = httpx.Timeout(timeout_seconds, connect=10.0)
            elif hasattr(self.chat_ollama._client._client, 'timeout'):
                # 이미 Timeout 객체가 설정되어 있을 수 있음
                self.chat_ollama._client._client.timeout = timeout_seconds
    except Exception as e:
        # timeout 설정 실패해도 계속 진행 (로깅만)
        import logging
        logging.warning(f"Failed to set _client timeout: {e}")
    
    self.contentsQueueService = ContentsQueueService()
```

### 방안 2: Timeout 값만 증가 (간단한 방법)

**현재**: 180초  
**제안**: 300초 (5분) 또는 600초 (10분)

```python
# 2025-12-22: timeout 180초 → 300초로 증가 (short_summary2 작업 추가로 프롬프트 길이 증가)
self.chat_ollama.client_kwargs["timeout"] = 300
```

**장점**: 간단  
**단점**: 여전히 타임아웃 발생 가능

### 방안 3: Retry 로직 추가

**제안**: 타임아웃 발생 시 자동 재시도

```python
import time
from httpcore import ReadTimeout

def _generate_with_retry(self, prompt, max_retries=2, mycontents_logger=None):
    """Timeout 발생 시 재시도하는 generate 래퍼"""
    for attempt in range(max_retries + 1):
        try:
            result = self.chat_ollama._client.generate(
                model=CONF.OLLAMA_MODEL,
                prompt=prompt,
                format=(None if "gpt-oss" in CONF.OLLAMA_MODEL else "json")
            )
            return result
        except (ReadTimeout, TimeoutError) as e:
            if attempt < max_retries:
                wait_time = (attempt + 1) * 10  # 10초, 20초...
                if mycontents_logger:
                    mycontents_logger.warning(f"⏱️ Timeout 발생 (시도 {attempt + 1}/{max_retries + 1}), {wait_time}초 후 재시도...")
                time.sleep(wait_time)
                continue
            else:
                if mycontents_logger:
                    mycontents_logger.error(f"❌ Timeout 재시도 실패 ({max_retries + 1}회 시도)")
                raise
        except Exception as e:
            # Timeout이 아닌 다른 에러는 즉시 raise
            raise
```

**사용 예시**:
```python
# 기존
result_summary = self.chat_ollama._client.generate(...)

# 변경 후
result_summary = self._generate_with_retry(
    new_question_summary, 
    max_retries=2, 
    mycontents_logger=mycontents_logger
)
```

---

## 🎯 최종 권장사항

### 즉시 적용: 방안 1 (Timeout 증가 + _client timeout 직접 설정)

**이유**:
1. ✅ `_client`의 내부 httpx 클라이언트 timeout도 명시적으로 설정
2. ✅ Timeout 값을 300초로 증가 (5분)
3. ✅ 대부분의 케이스에서 효과적

### 추가 개선: 방안 3 (Retry 로직) - 선택적

- 타임아웃 발생 시 자동 재시도
- 일시적인 네트워크 문제나 서버 부하 시 유용

---

## 📝 구현 코드

### 수정 전
```python
self.chat_ollama.client_kwargs["timeout"] = 180
self.chat_ollama._set_clients()
```

### 수정 후
```python
# Timeout 설정 (300초 = 5분)
timeout_seconds = 300
self.chat_ollama.client_kwargs["timeout"] = timeout_seconds
self.chat_ollama._set_clients()

# _client의 내부 httpx 클라이언트 timeout도 직접 설정
try:
    import httpx
    if hasattr(self.chat_ollama._client, '_client'):
        if isinstance(self.chat_ollama._client._client, httpx.Client):
            # httpx.Client의 timeout은 Timeout 객체로 설정
            self.chat_ollama._client._client.timeout = httpx.Timeout(timeout_seconds, connect=10.0)
        elif hasattr(self.chat_ollama._client._client, 'timeout'):
            self.chat_ollama._client._client.timeout = timeout_seconds
except Exception as e:
    # timeout 설정 실패해도 계속 진행
    import logging
    logging.warning(f"Failed to set _client timeout: {e}")
```

---

## 📊 해결 방안 비교

| 방안 | 복잡도 | 효과 | 추천도 |
|------|--------|------|--------|
| **방안 1: _client timeout 직접 설정** | 중간 | 높음 | ⭐⭐⭐⭐⭐ |
| **방안 2: Timeout 값 증가** | 낮음 | 중간 | ⭐⭐⭐ |
| **방안 3: Retry 로직** | 높음 | 높음 | ⭐⭐⭐⭐ |

---

## 📝 추가 고려사항

### 1. 모델별 최적 Timeout

- **빠른 모델**: 180초
- **느린 모델 (gpt-oss-20b 등)**: 300초 이상
- **매우 긴 문서**: 600초 (10분)

### 2. 모니터링

- 타임아웃 발생 빈도 추적
- 평균 처리 시간 모니터링
- Timeout 값 동적 조정 고려

### 3. 에러 처리

- 타임아웃 발생 시 사용자에게 명확한 메시지
- 부분 결과라도 저장 (가능한 경우)

---

## ✅ 결론

**문제**: `_client.generate()` 호출 시 timeout 설정이 적용되지 않음

**해결**:
1. Timeout 값 증가: 180초 → 300초 (5분)
2. `_client`의 내부 httpx 클라이언트 timeout 직접 설정
3. (선택) Retry 로직 추가

이렇게 하면 타임아웃 에러를 대부분 해결할 수 있습니다.



