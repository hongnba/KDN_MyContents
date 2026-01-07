#!/bin/bash
#
# LLM 평가 테스트 반복 실행 스크립트 (YAML 프롬프트 사용)
#
# 사용법:
#   ./run_llm_test_N_yaml_prompt.sh              # 아래 설정된 변수 사용
#   ./run_llm_test_N_yaml_prompt.sh [N]          # N번 반복 실행 (기본값: 설정된 ITERATIONS)
#   ITERATIONS=N ./run_llm_test_N_yaml_prompt.sh # 환경 변수로 N번 반복 실행
#
# 예시:
#   ./run_llm_test_N_yaml_prompt.sh 10           # 10번 반복 실행
#   ITERATIONS=5 ./run_llm_test_N_yaml_prompt.sh # 5번 반복 실행
#

# ============================================================================
# 설정 변수 (최상단 - 쉽게 편집 가능)
# ============================================================================

# YAML 프롬프트 파일 경로 (컨테이너 내부 경로 또는 로컬 경로)
# 예시: "/app/ksubscribe_server/analysis/prompts/20260102_geon_ver_1.yaml"
# 또는: "/home/themiraclesoft/mycontents/Geon_KDN_MyContents/kSubscribe_Python_v2.0.0/src/ksubscribe_server/analysis/prompts/20260102_geon_ver_1.yaml"
YAML_PROMPT_PATH="/app/ksubscribe_server/analysis/prompts/20260102_geon_ver_4.yaml"

# 실험 반복 횟수
ITERATIONS=1

# 사용할 LLM 모델명
# 예시: "gpt-oss:20b", "llama-3-Korean-Bllossom-8B-Q4_K_M:latest"
OLLAMA_MODEL="gpt-oss:20b"

# 테스트할 문서 ID 파일 (컨테이너 내부 경로)
TEST_IDS_FILE="test_ids_weekly_article_test_title_only.txt"

# ============================================================================
# 스크립트 설정 (일반적으로 수정 불필요)
# ============================================================================

# 로그 파일 설정
LOG_DIR="/home/themiraclesoft/mycontents/Geon_KDN_MyContents/kSubscribe_Python_v2.0.0/src/ksubscribe_share/test"
LOG_FILE="${LOG_DIR}/llm_test_yaml_prompt_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "${LOG_DIR}"

# 모든 출력을 로그 파일로 리다이렉트 (터미널에도 출력)
exec > >(tee -a "${LOG_FILE}")
exec 2>&1

echo "=========================================="
echo "YAML 프롬프트 LLM 테스트 스크립트"
echo "=========================================="
echo "YAML 프롬프트 파일: ${YAML_PROMPT_PATH}"
echo "반복 횟수: ${ITERATIONS}"
echo "LLM 모델: ${OLLAMA_MODEL}"
echo "테스트 ID 파일: ${TEST_IDS_FILE}"
echo "로그 파일: ${LOG_FILE}"
echo "=========================================="
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 반복 횟수 설정
# 우선순위: 1) 명령행 인자, 2) 환경 변수 ITERATIONS, 3) 위에서 설정한 ITERATIONS
DEFAULT_ITERATIONS=${ITERATIONS}
ITERATIONS=${1:-${ITERATIONS:-${DEFAULT_ITERATIONS}}}

# Ollama 컨테이너 이름
OLLAMA_CONTAINER_NAME="ksubscribe_ollama"

# 안전하게 Ollama에 로드된 모델을 언로드하는 함수
unload_gpu_models() {
    echo ""
    echo -e "${YELLOW}🔌 Unloading any models from Ollama GPU (container: ${OLLAMA_CONTAINER_NAME})...${NC}"
    LOADED_MODELS=$(docker exec ${OLLAMA_CONTAINER_NAME} ollama ps 2>/dev/null | tail -n +2 | awk '{print $1}' || true)
    if [[ -n "$LOADED_MODELS" ]]; then
        for m in $LOADED_MODELS; do
            echo -e "${YELLOW}   - stopping: ${m}${NC}"
            docker exec ${OLLAMA_CONTAINER_NAME} ollama stop "$m" 2>/dev/null || true
        done
        sleep 2
        echo -e "${GREEN}✅ Unload complete${NC}"
    else
        echo -e "${GREEN}✅ No models loaded on Ollama GPU${NC}"
    fi
}

# Ensure we attempt to unload models on exit (normal or Ctrl+C)
trap 'unload_gpu_models' EXIT

# YAML 파일 경로 검증 (컨테이너 내부 경로로 변환)
CONTAINER_YAML_PATH="${YAML_PROMPT_PATH}"
if [[ "${YAML_PROMPT_PATH}" == /home/* ]]; then
    # 로컬 경로인 경우 컨테이너 내부 경로로 변환
    # /home/themiraclesoft/mycontents/Geon_KDN_MyContents/kSubscribe_Python_v2.0.0/src/ksubscribe_server/analysis/prompts/xxx.yaml
    # -> /app/ksubscribe_server/analysis/prompts/xxx.yaml
    RELATIVE_PATH=$(echo "${YAML_PROMPT_PATH}" | sed 's|.*/kSubscribe_Python_v2.0.0/src/||')
    CONTAINER_YAML_PATH="/app/${RELATIVE_PATH}"
    echo -e "${CYAN}📝 로컬 경로 감지: ${YAML_PROMPT_PATH}${NC}"
    echo -e "${CYAN}   → 컨테이너 내부 경로: ${CONTAINER_YAML_PATH}${NC}"
fi

# YAML 파일 존재 확인
echo -e "${CYAN}🔍 YAML 프롬프트 파일 확인 중...${NC}"
if docker exec geon_python_unified test -f "${CONTAINER_YAML_PATH}" 2>/dev/null; then
    echo -e "${GREEN}✅ YAML 파일 존재 확인: ${CONTAINER_YAML_PATH}${NC}"
else
    echo -e "${RED}❌ YAML 파일을 찾을 수 없습니다: ${CONTAINER_YAML_PATH}${NC}"
    echo -e "${YELLOW}⚠️  스크립트를 계속 실행하지만, YAML 파일이 없으면 기본 프롬프트를 사용합니다.${NC}"
fi

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}🚀 Starting ${ITERATIONS} iterations of LLM evaluation test${NC}"
echo -e "${CYAN}   Model: ${OLLAMA_MODEL}${NC}"
echo -e "${CYAN}   YAML Prompt: ${CONTAINER_YAML_PATH}${NC}"
echo -e "${CYAN}========================================${NC}"

# Ensure Ollama is cleared and pull the target model before running tests
echo -e "${CYAN}⏳ Preparing Ollama: unload existing models and pull ${OLLAMA_MODEL}${NC}"
unload_gpu_models
echo -e "${CYAN}📥 Pulling model ${OLLAMA_MODEL} to Ollama (may be no-op if already present)...${NC}"
docker exec ${OLLAMA_CONTAINER_NAME} ollama pull "${OLLAMA_MODEL}" 2>/dev/null || true
sleep 3

for i in $(seq 1 $ITERATIONS)
do
    echo -e "${BLUE}────────────────────────────────────────${NC}"
    echo -e "${BLUE}Running test iteration $i/${ITERATIONS} at $(date)${NC}"
    echo -e "${BLUE}────────────────────────────────────────${NC}"
    
    # YAML 프롬프트 파일 경로를 전달하여 테스트 실행
    docker exec geon_python_unified python3 /app/ksubscribe_share/test/test_llm_evaluation.py \
        --ollama-model "${OLLAMA_MODEL}" \
        --test-ids "${TEST_IDS_FILE}" \
        --yaml-prompt "${CONTAINER_YAML_PATH}"
    
    echo -e "${GREEN}✅ Test iteration $i completed at $(date)${NC}"
    
    # 각 테스트 사이에 잠깐 대기 (선택사항)
    if [ $i -lt $ITERATIONS ]; then
        echo -e "${YELLOW}Waiting 5 seconds before next iteration...${NC}"
        sleep 5
    fi
done

echo -e "${GREEN}✅ All ${ITERATIONS} test iterations completed!${NC}"

# 엑셀 보고서 생성 (선택사항)
echo -e "${CYAN}📊 Generating Excel report...${NC}"
docker exec geon_python_unified python3 /app/ksubscribe_share/generate_excel_report.py --model "${OLLAMA_MODEL}" --iterations "${ITERATIONS}" 2>/dev/null || echo -e "${YELLOW}⚠️  Excel report generation skipped or failed${NC}"

echo ""
echo -e "${GREEN}✅ All tests and reports completed!${NC}"
echo -e "${CYAN}로그 파일: ${LOG_FILE}${NC}"

