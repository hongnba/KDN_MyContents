# 두 번째 실행 동작 및 중복 처리(보고서)

작성일: 2025-11-13
작성자: 자동분석 에이전트(요약용)

## 목적
팀 및 관리자에게 `main_collect_and_scrapping.py` 실행 중 **두 번째 호출이 실패 항목만 재처리하지 않고 전체 큐를 다시 처리하는 이유**, 그 영향, 근거(로그·코드 위치), 그리고 권장 조치(단기/중기)를 명확히 설명합니다.

---

## 핵심 요약
`crawl_and_analyze_ollama()`가 큐 전체를 읽어 처리하고 큐 항목을 삭제하지 않으며, 이미 존재 여부를 검사하는 로직이 비활성화되어 있습니다. 따라서 메인 스크립트에서 동일 함수를 두 번 호출하면 큐에 남아 있는 항목들이 재처리되어 중복 저장 및 불필요한 LLM 호출이 발생합니다. 두 번째 호출은 실패 항목만을 대상으로 하지 않습니다.

---

## 관련 파일 및 위치
- 메인 실행 스크립트:
  - `src/docker_shell/main_collect_and_scrapping.py` (약 69–90줄)
    - 첫 번째 호출: `contentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama()`
    - 두 번째 호출(로그에 "second time" 표기): 동일 함수 재호출
- 스크래핑/분석 구현:
  - `src/docker_scraping/contents_scraping_ollama_trafilaura.py`
    - `crawl_and_analyze_ollama(self)`
      - 내부에서 `queueContents = self.contentsQueueService.find_all()` 호출
      - `for index, contentsQueueVO in enumerate(queueContents): self.crawl_and_analyze_one_ollama(...)` 처리
    - 기본 설정: `self.delete_queue_after_processing = False` (처리 후 큐 삭제 안 함)
    - `crawl_and_analyze_one_ollama(...)` 내부의 `ContentsService().isExistContents(queueContent.url)` 검사는 주석 처리되어 있어 중복 처리 가능
    - 참고: `scrapping_for_exist_contents(start_date, end_date, is_all)`라는 보완용 함수가 있으나 메인에서 사용되지 않음

---

## 증거(로그 발췌)
실행 중 관찰된 로그 예시:
```
2025-11-13 05:52:46,167 - docker_scraping - INFO - Queue range : 14
...
2025-11-13 05:27:18,818 - docker_scraping - INFO - contentsScrapingOllamaTrafilaura.crawl_and_analyze_ollama() - second time....
2025-11-13 05:27:20,007 - docker_scraping - INFO - Queue range : 14
```
첫 호출(Queue 14)을 처리한 뒤 동일한 큐 항목 수(14)를 두 번째 호출에서도 다시 읽은 것이 확인됩니다. 그 결과 MongoDB에 중복 저장 또는 업데이트가 발생해 저장 건수가 큐 개수보다 많아진 사례가 관찰되었습니다.

---

## 기술적 원인
1. `crawl_and_analyze_ollama()`가 큐 전체를 반환하는 `find_all()`를 사용하여 모든 큐 항목을 처리합니다.
2. `delete_queue_after_processing`가 False로 설정되어 있어, 처리한 항목이 큐에 남아 있습니다.
3. `crawl_and_analyze_one_ollama()`의 중복 검사(`isExistContents`)가 주석 처리되어 있어 이미 저장된 URL도 다시 처리됩니다.
4. 메인 스크립트가 동일한 함수를 두 번 호출하기 때문에 두 번째 호출은 실패 항목만이 아닌 전체 큐를 재처리합니다.

---

## 운영 영향
- 데이터 중복 및 기록 왜곡: 동일 문서가 중복 저장되거나 `rawCollectDt`/`metaAnalyzeDt` 등 메타가 덮어써질 수 있음
- 불필요한 리소스 소모: LLM(ollama) 호출 증가로 비용·지연·부하 증가 위험
- 장애 원인 분석 난이도 증가: 첫 실패가 두 번째 실행으로 가려질 수 있음
- 외부 전파 위험: 중복 데이터가 통계·보고 시스템까지 영향을 줄 수 있음

---

## 사례(발생한 오류)
- URL: `http://www.finomy.com/news/articleView.html?idxno=240551`
  - 첫 실행: LLM 응답에서 `short_summary` 키 누락으로 `KeyError: 'short_summary'` 발생(요약 실패)
  - 두 번째 전체 재실행: 정상 응답을 얻어 DB에 저장됨
  - 결과: 최초 실패 원인 파악이 어려워짐(재현성/원인분석 방해)

---

## 권장 조치(우선순위별)

### A. 단기(즉시 적용, 저위험)
1) `crawl_and_analyze_one_ollama()`에 중복 검사 활성화 (가장 빠르고 안전한 방어책)

```python
# 함수 초반에 추가
if ContentsService().isExistContents(queueContent.url):
    self.docker_scraping_logger.info(f"이미 ContentsDB에 존재하는 contents입니다. {queueContent.url}")
    return
```

효과: DB에 이미 존재하는 URL은 재처리/재저장을 차단합니다.

2) 임시 조치로 `src/docker_shell/main_collect_and_scrapping.py`의 두 번째 호출을 주석 처리하거나 제거합니다.

효과: 중복 재처리를 즉시 차단할 수 있습니다.

### B. 중기(안정성 향상)
1) 두 번째 실행을 실패 항목 또는 메타가 누락된 항목만 처리하도록 변경
   - 구현 방안 예시:
     - `scrapping_for_exist_contents(start_date, end_date, is_all=False)` 호출로 메타 누락 항목 보완
     - 혹은 `crawl_and_analyze_ollama(..., failed_only=True)` 같은 플래그 추가
2) `delete_queue_after_processing = True` 설정 여부 검토(감사/추적 요구에 따라 신중히 결정)

### C. 장기(신뢰성 강화)
1) Ollama 응답 파싱을 방어적으로 처리

```python
short = (result_summary_json.get("short_summary")
         or result_summary_json.get("summary")
         or (result_summary_json.get("long_summary")[:300] if result_summary_json.get("long_summary") else None))
if not short:
    # 재시도 또는 실패 로깅
else:
    pred_keywords = SimularityChecker().best_keyword_of_summary(short, keywords_verify)
```

2) LLM 호출 실패 시 재시도(예: 1회)와 백오프를 도입
3) 큐 항목 상태(`processing`, `attempts` 등) 추적 필드 추가로 재처리 정책 및 모니터링 개선

---

## 제안 작업(지금 바로 수행 가능)
1. 권장(우선순위): `isExistContents` 검사 활성화 — 저위험, 즉시 적용 가능
2. 이후: `short_summary` 누락 대비 방어 로직 및 1회 재시도 추가
3. 그 다음: 두 번째 호출을 실패 항목 전용으로 변경

원하시면 1번(중복 체크 활성화)을 지금 코드에 적용하고 `ksubscribe_python_unified` 컨테이너에서 짧은 테스트를 실행해 결과를 보여드리겠습니다. 문서 상단에 변경 이력(예: 20251113 수정 내역)도 함께 추가하겠습니다.

---

## 관리자용 요약(한 문단)
현재 파이프라인은 동일 큐를 두 번 처리하도록 설정되어 있어, 처리된 항목들이 큐에 남아 재처리되어 중복 저장 및 불필요한 LLM 호출이 발생합니다. 단기적으로는 중복 검사 활성화 또는 두 번째 호출 제거로 문제를 차단하고, 중장기적으로는 실패 항목만 선택적으로 재처리하도록 개선하는 것을 권장합니다.

---

## 변경 이력
- 2025-11-13: 초안 작성 — 두 번째 전체 재처리 동작의 원인 및 권장 조치 정리


