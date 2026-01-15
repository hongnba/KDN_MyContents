#!/bin/bash

# 4-GPU 병렬 LLM 테스트 실행 스크립트 (N회 반복 지원 - 비동기 병렬 처리 버전)
# asyncio를 사용한 비동기 병렬 처리로 GPU 활용률 95%+ 달성
# Usage: ./run_llm_test_parallel_4gpu_asyncio_parallel.sh [iterations]
#
# 예시:
#   ./run_llm_test_parallel_4gpu_asyncio_parallel.sh           # 기본값 사용 (1회)
#   ./run_llm_test_parallel_4gpu_asyncio_parallel.sh 5         # 5회 반복
#   ./run_llm_test_parallel_4gpu_asyncio_parallel.sh 10        # 10회 반복
#   ITERATIONS=10 ./run_llm_test_parallel_4gpu_asyncio_parallel.sh  # 환경변수로 10회

set -e

# 기본값 설정
DEFAULT_ITERATIONS=1
ITERATIONS="${1:-${ITERATIONS:-${DEFAULT_ITERATIONS}}}"
TEST_IDS_FILE="/app/ksubscribe_share/test/test_ids_article_elec_organization.txt"
YAML_PROMPT_FILE="/app/ksubscribe_server/analysis/prompts/20260102_geon_ver_5.yaml"
BASE_TEST_DIR="/app/ksubscribe_share/test"
MODEL_NAME="gpt-oss:20b"
MODEL_NAME_SAFE="${MODEL_NAME//:/_}"  # 파일명에 사용하기 위해 콜론을 언더스코어로 변경
LOG_DIR="./logs"
SESSION_ID=$(date +"%Y%m%d_%H%M%S")  # 전체 세션 ID
SESSION_START_TIME_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# 세션별 결과 디렉토리
SESSION_DIR="${BASE_TEST_DIR}/gpu_4way_asyncio_${SESSION_ID}"
TEMP_OID_DIR="${SESSION_DIR}/temp_oids"  # OID 분할 파일 저장 디렉토리

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 로그 디렉토리 생성
mkdir -p "${LOG_DIR}"

# 세션별 출력 디렉토리 구조 생성 (컨테이너 내부에서 - 한 번에)
echo -e "${CYAN}📁 세션별 출력 디렉토리 생성 중...${NC}"
echo -e "   📂 ${SESSION_DIR}"
docker exec geon_python_unified mkdir -p \
    "${SESSION_DIR}/gpu_0_result" \
    "${SESSION_DIR}/gpu_0_test_summary" \
    "${SESSION_DIR}/gpu_1_result" \
    "${SESSION_DIR}/gpu_1_test_summary" \
    "${SESSION_DIR}/gpu_2_result" \
    "${SESSION_DIR}/gpu_2_test_summary" \
    "${SESSION_DIR}/gpu_3_result" \
    "${SESSION_DIR}/gpu_3_test_summary" \
    "${SESSION_DIR}/gpu_4way_result" \
    "${SESSION_DIR}/gpu_4way_test_summary" \
    "${TEMP_OID_DIR}" 2>/dev/null

echo -e "   ├─ gpu_0_result/ & gpu_0_test_summary/"
echo -e "   ├─ gpu_1_result/ & gpu_1_test_summary/"
echo -e "   ├─ gpu_2_result/ & gpu_2_test_summary/"
echo -e "   ├─ gpu_3_result/ & gpu_3_test_summary/"
echo -e "   ├─ gpu_4way_result/ (통합 JSON)"
echo -e "   ├─ gpu_4way_test_summary/ (통합 Excel)"
echo -e "   └─ temp_oids/"
echo -e "${GREEN}✅ 출력 디렉토리 생성 완료${NC}"
echo ""

echo -e "${CYAN}==========================================${NC}"
echo -e "${CYAN}🚀 4-GPU 병렬 LLM 테스트 (N회 반복 실행 - Asyncio 병렬 처리)${NC}"
echo -e "${CYAN}==========================================${NC}"
echo -e "📁 TEST_IDS_FILE: ${TEST_IDS_FILE}"
echo -e "📝 YAML_PROMPT_FILE: ${YAML_PROMPT_FILE}"
echo -e "🔄 반복 횟수: ${ITERATIONS}"
echo -e "🤖 모델: ${MODEL_NAME}"
echo -e "⚡ 처리 방식: Asyncio 비동기 병렬 (GPU 활용률 95%+)"
echo -e "📊 로그 디렉토리: ${LOG_DIR}"
echo -e "📂 세션 디렉토리: ${SESSION_DIR}"
echo -e "💾 GPU별 JSON 저장: gpu_X_result/ (각 ${ITERATIONS}개)"
echo -e "💾 통합 JSON 저장: gpu_4way_result/ (${ITERATIONS}개)"
echo -e "💾 GPU별 Excel 저장: gpu_X_test_summary/ (각 1개)"
echo -e "💾 통합 Excel 저장: gpu_4way_test_summary/ (1개)"
echo -e "⏰ 세션 시작 (UTC): ${SESSION_START_TIME_UTC}"
echo -e "🆔 세션 ID: ${SESSION_ID}"
echo -e "${CYAN}==========================================${NC}"
echo ""

# 안전하게 Ollama에 로드된 모델을 언로드하는 함수
unload_gpu_models() {
    echo ""
    echo -e "${YELLOW}🔌 Unloading any models from Ollama GPU...${NC}"
    for i in 0 1 2 3; do
        LOADED_MODELS=$(docker exec ksubscribe_ollama${i} ollama ps 2>/dev/null | tail -n +2 | awk '{print $1}' || true)
        if [[ -n "$LOADED_MODELS" ]]; then
            for m in $LOADED_MODELS; do
                echo -e "${YELLOW}   GPU${i}: stopping ${m}${NC}"
                docker exec ksubscribe_ollama${i} ollama stop "$m" 2>/dev/null || true
            done
        fi
    done
    sleep 2
    echo -e "${GREEN}✅ Unload complete${NC}"
}

# Ctrl+C 등으로 종료 시 모델 언로드
trap 'unload_gpu_models' EXIT

# GPU 상태 점검
echo -e "${CYAN}🔍 GPU 상태 점검 중...${NC}"
nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv,noheader
echo ""

# Ollama 컨테이너 GPU 접근 확인
echo "🔧 Ollama 컨테이너 GPU 접근 확인 중..."
GPU_ACCESS_OK=true
for i in 0 1 2 3; do
    echo -n "  GPU${i}: "
    if docker exec ksubscribe_ollama${i} nvidia-smi --query-gpu=index --format=csv,noheader &>/dev/null; then
        echo "✅ GPU 접근 가능"
    else
        echo "❌ GPU 접근 불가 - 컨테이너 재시작 필요"
        GPU_ACCESS_OK=false
    fi
done

# GPU 접근 불가 시 컨테이너 재시작
if [ "$GPU_ACCESS_OK" = false ]; then
    echo ""
    echo "⚠️  일부 컨테이너가 GPU에 접근할 수 없습니다."
    echo "🔄 Ollama 컨테이너 재시작 중..."
    docker-compose -f docker-compose-geon-gpu_4way.yml restart ollama0 ollama1 ollama2 ollama3
    
    echo "⏳ 컨테이너 초기화 대기 중 (30초)..."
    sleep 30
    
    echo "🔍 GPU 접근 재확인 중..."
    for i in 0 1 2 3; do
        echo -n "  GPU${i}: "
        if docker exec ksubscribe_ollama${i} nvidia-smi --query-gpu=index --format=csv,noheader &>/dev/null; then
            echo "✅ GPU 접근 가능"
        else
            echo "❌ GPU 접근 실패 - 스크립트 중단"
            exit 1
        fi
    done
    echo "✅ 모든 컨테이너 GPU 접근 정상"
fi
echo ""

# 각 Ollama 컨테이너의 모델 상태 확인 및 정리
echo "🧹 Ollama 모델 정리 중..."
for i in 0 1 2 3; do
    echo "  GPU${i}: 실행 중인 모델 확인..."
    
    # 실행 중인 모델 확인
    RUNNING_MODELS=$(docker exec ksubscribe_ollama${i} ollama ps 2>/dev/null | tail -n +2 | awk '{print $1}')
    
    if [ -n "$RUNNING_MODELS" ]; then
        echo "    ⚠️  실행 중인 모델 발견, 언로드 중..."
        while IFS= read -r model; do
            if [ -n "$model" ]; then
                echo "      - ${model} 언로드..."
                docker exec ksubscribe_ollama${i} ollama stop "${model}" 2>/dev/null || true
            fi
        done <<< "$RUNNING_MODELS"
        
        # 언로드 확인 (5초 대기)
        sleep 5
        
        STILL_RUNNING=$(docker exec ksubscribe_ollama${i} ollama ps 2>/dev/null | tail -n +2)
        if [ -z "$STILL_RUNNING" ]; then
            echo "    ✅ 모델 언로드 완료"
        else
            echo "    ⚠️  일부 모델이 여전히 실행 중"
        fi
    else
        echo "    ✅ 실행 중인 모델 없음"
    fi
done
echo ""

# GPU 메모리 정리 후 상태 재확인
echo "🔍 정리 후 GPU 상태:"
nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv,noheader
echo ""

# gpt-oss:20b 모델 사전 로드 및 메모리 적재 확인
echo "📦 gpt-oss:20b 모델 사전 로드 시작..."
echo ""

# 각 GPU에 병렬로 모델 로드 (ollama run 사용 - 가장 확실한 방법)
for i in 0 1 2 3; do
    echo "🔄 GPU${i}: 모델 로딩 중..."
    # 백그라운드로 실행하되, 간단한 프롬프트로 모델을 로드
    docker exec ksubscribe_ollama${i} bash -c "echo 'init' | ollama run gpt-oss:20b --verbose 2>&1 | head -20" > /dev/null 2>&1 &
done

echo "⏳ 모델 로딩 대기 중..."
wait
echo ""

# GPU 메모리 적재 확인 루프
echo "🔍 GPU 메모리 적재 확인 중 (최대 60초 대기)..."
ALL_LOADED=true
for i in 0 1 2 3; do
    echo -n "  GPU${i}: "
    LOADED=false
    for retry in {1..30}; do
        # 메모리 사용량이 10000MB 이상이면 로드된 것으로 간주 (gpt-oss:20b는 13GB 사용)
        MEM=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i $i | awk '{print int($1)}')
        if [ "$MEM" -gt 10000 ]; then
            echo "✅ 로드 완료 (${MEM}MiB)"
            LOADED=true
            break
        fi
        # 진행 표시
        if [ $((retry % 5)) -eq 0 ]; then
            echo -n "."
        fi
        sleep 2
    done
    
    if [ "$LOADED" = false ]; then
        echo "❌ 로드 실패 (메모리 사용량: ${MEM}MiB)"
        echo "    -> 오류: 모델이 GPU에 올라가지 않았습니다. 'ollama ps'로 확인하세요."
        ALL_LOADED=false
    fi
done

if [ "$ALL_LOADED" = false ]; then
    echo ""
    echo "❌ 일부 GPU에 모델 로드 실패 - 스크립트 중단"
    echo "💡 해결 방법:"
    echo "   1. docker exec ksubscribe_ollama0 ollama ps 로 상태 확인"
    echo "   2. GPU 메모리 부족 여부 확인: nvidia-smi"
    echo "   3. 컨테이너 재시작: docker-compose -f docker-compose-geon-gpu_4way.yml restart"
    exit 1
fi

echo "✅ 모든 GPU에 모델 로드 완료"
echo ""

# 최종 GPU 상태
echo "🔍 모델 로드 후 GPU 상태:"
nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv,noheader
echo ""

# Ollama 실행 상태 확인
echo "🔍 Ollama 모델 상태 확인:"
for i in 0 1 2 3; do
    echo "  GPU${i}:"
    docker exec ksubscribe_ollama${i} ollama ps | tail -n +2 | sed 's/^/    /'
done
echo ""

# 컨테이너 헬스 체크
echo "🏥 컨테이너 상태 확인 중..."
for i in 0 1 2 3; do
    HEALTH=$(docker inspect ksubscribe_ollama${i} --format='{{.State.Health.Status}}' 2>/dev/null || echo "no_health")
    STATUS=$(docker inspect ksubscribe_ollama${i} --format='{{.State.Status}}' 2>/dev/null || echo "not_found")
    
    if [ "$STATUS" != "running" ]; then
        echo "❌ ksubscribe_ollama${i} 컨테이너가 실행 중이 아닙니다 (Status: ${STATUS})"
        exit 1
    fi
    
    if [ "$HEALTH" = "healthy" ]; then
        echo "✅ ollama${i}: ${STATUS} (${HEALTH})"
    elif [ "$HEALTH" = "no_health" ]; then
        echo "✅ ollama${i}: ${STATUS} (healthcheck 없음)"
    else
        echo "⚠️  ollama${i}: ${STATUS} (${HEALTH})"
    fi
done

# Python 컨테이너 확인
PYTHON_STATUS=$(docker inspect geon_python_unified --format='{{.State.Status}}' 2>/dev/null || echo "not_found")
if [ "$PYTHON_STATUS" != "running" ]; then
    echo "❌ geon_python_unified 컨테이너가 실행 중이 아닙니다"
    exit 1
fi
echo "✅ geon_python_unified: ${PYTHON_STATUS}"
echo ""

# ============================================================================
# OID 파일 4분할 (1회만 수행 - N번 실험에서 재사용)
# ============================================================================

echo -e "${CYAN}✂️  OID 파일 4분할 중 (1회만 수행)...${NC}"
docker exec geon_python_unified python3 -c "
import sys
import os

# OID 파일 읽기
oid_file = '${TEST_IDS_FILE}'
if not os.path.exists(oid_file):
    print(f'❌ OID 파일을 찾을 수 없습니다: {oid_file}', file=sys.stderr)
    sys.exit(1)

with open(oid_file, 'r') as f:
    oids = [line.strip() for line in f if line.strip()]

total = len(oids)
print(f'📊 전체 OID 수: {total}')

if total == 0:
    print('❌ OID가 없습니다', file=sys.stderr)
    sys.exit(1)

# 4분할
chunk_size = (total + 3) // 4  # 올림 나눗셈
chunks = [oids[i:i+chunk_size] for i in range(0, total, chunk_size)]

# 임시 파일 생성 (세션 전체에서 재사용)
temp_dir = '${TEMP_OID_DIR}'
for idx, chunk in enumerate(chunks):
    chunk_file = f'{temp_dir}/gpu{idx}_oids.txt'
    with open(chunk_file, 'w') as f:
        f.write('\\n'.join(chunk))
    print(f'✅ GPU{idx}: {len(chunk)}개 OID -> {chunk_file}')
" 2>&1

if [ $? -ne 0 ]; then
    echo "❌ OID 분할 실패"
    exit 1
fi
echo ""

# ============================================================================
# N회 반복 실행 시작
# ============================================================================

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}🚀 Starting ${ITERATIONS} iterations of 4-GPU parallel test${NC}"
echo -e "${BLUE}   (모델은 N회 실험 동안 GPU에 유지됨)${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

for ITERATION in $(seq 1 $ITERATIONS)
do
    echo -e "${CYAN}────────────────────────────────────────${NC}"
    echo -e "${CYAN}🔄 Iteration ${ITERATION}/${ITERATIONS} started at $(date)${NC}"
    echo -e "${CYAN}────────────────────────────────────────${NC}"
    
    # 각 iteration별 타임스탬프
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    START_TIME_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    PID_FILE="${LOG_DIR}/workers_${SESSION_ID}_iter${ITERATION}.pids"
    START_TIME_FILE="${LOG_DIR}/start_time_${SESSION_ID}_iter${ITERATION}.txt"
    
    # 실행 시작 시간 기록
    echo "${START_TIME_UTC}" > "${START_TIME_FILE}"
    
    echo -e "   ⏰ Iteration 시작 시간: ${START_TIME_UTC}"
    echo -e "   📄 시작 시간 파일: ${START_TIME_FILE}"
    echo ""

    # 4개 워커 병렬 실행
    echo "🔥 4개 워커 병렬 실행 시작..."
    echo "📌 PID 파일: ${PID_FILE}"
    echo ""

    for GPU_ID in 0 1 2 3; do
        OLLAMA_URL="http://ksubscribe_ollama${GPU_ID}:11434"
        TEMP_OID_FILE="${TEMP_OID_DIR}/gpu${GPU_ID}_oids.txt"  # 미리 분할된 파일 재사용
        LOG_FILE="${LOG_DIR}/worker_${GPU_ID}_${SESSION_ID}_iter${ITERATION}.log"
        JSON_OUTPUT_DIR="${SESSION_DIR}/gpu_${GPU_ID}_result"
        EXCEL_OUTPUT_DIR="${SESSION_DIR}/gpu_${GPU_ID}_test_summary"
        
        echo "🚀 GPU${GPU_ID} 워커 시작..."
        echo "   OLLAMA_URL: ${OLLAMA_URL}"
        echo "   OID_FILE: ${TEMP_OID_FILE}"
        echo "   LOG_FILE: ${LOG_FILE}"
        echo "   JSON_DIR: ${JSON_OUTPUT_DIR}"
        echo "   EXCEL_DIR: ${EXCEL_OUTPUT_DIR}"
        
        nohup docker exec \
            -e OLLAMA_URL="${OLLAMA_URL}" \
            -e GPU_ID="${GPU_ID}" \
            -e ITERATION="${ITERATION}" \
            -e SESSION_ID="${SESSION_ID}" \
            -e JSON_OUTPUT_DIR="${JSON_OUTPUT_DIR}" \
            -e EXCEL_OUTPUT_DIR="${EXCEL_OUTPUT_DIR}" \
            geon_python_unified \
            python3 /app/ksubscribe_share/test/test_llm_evaluation_asyncio_parallel.py \
            --test-ids "${TEMP_OID_FILE}" \
            --yaml-prompt "${YAML_PROMPT_FILE}" \
            --ollama-model "${MODEL_NAME}" \
            > "${LOG_FILE}" 2>&1 &
        
        WORKER_PID=$!
        echo "${WORKER_PID}" >> "${PID_FILE}"
        echo "   PID: ${WORKER_PID}"
        echo ""
        
        sleep 2  # 워커 간 시작 간격
    done

    echo "✅ 4개 워커 모두 백그라운드에서 실행 중"
    echo ""
    echo "📊 실시간 로그 확인:"
    echo "   tail -f ${LOG_DIR}/worker_0_${SESSION_ID}_iter${ITERATION}.log"
    echo "   tail -f ${LOG_DIR}/worker_1_${SESSION_ID}_iter${ITERATION}.log"
    echo "   tail -f ${LOG_DIR}/worker_2_${SESSION_ID}_iter${ITERATION}.log"
    echo "   tail -f ${LOG_DIR}/worker_3_${SESSION_ID}_iter${ITERATION}.log"
    echo ""
    echo "🔍 전체 로그 모니터링:"
    echo "   tail -f ${LOG_DIR}/worker_*_${SESSION_ID}_iter${ITERATION}.log"
    echo ""
    echo "⏹️  중지 명령:"
    echo "   kill \$(cat ${PID_FILE})"
    echo ""
    echo "📁 워커 PID 목록:"
    cat "${PID_FILE}"
    echo ""
    echo ""

    # 워커 완료 대기
    echo -e "${YELLOW}⏳ Iteration ${ITERATION} 워커 완료 대기 중...${NC}"
    while true; do
        # PID 파일에서 살아있는 프로세스 개수 확인
        ALIVE=0
        while IFS= read -r pid; do
            if kill -0 "$pid" 2>/dev/null; then
                ALIVE=$((ALIVE + 1))
            fi
        done < "${PID_FILE}"
        
        if [ $ALIVE -eq 0 ]; then
            echo -e "${GREEN}✅ Iteration ${ITERATION} 모든 워커 완료!${NC}"
            break
        fi
        
        echo "   실행 중인 워커: ${ALIVE}/4"
        sleep 30
    done

    echo ""
    echo -e "${GREEN}✅ Iteration ${ITERATION}/${ITERATIONS} completed at $(date)${NC}"
    
    # Iteration 완료 후 4-way 통합 JSON 생성
    echo ""
    echo -e "${CYAN}🔄 Iteration ${ITERATION} 통합 JSON 생성 중...${NC}"
    docker exec geon_python_unified python3 /app/ksubscribe_share/merge_gpu_results.py \
        --session-dir "${SESSION_DIR}" \
        --iteration "${ITERATION}" \
        --model-name "${MODEL_NAME}"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Iteration ${ITERATION} 통합 JSON 생성 완료!${NC}"
    else
        echo -e "${YELLOW}⚠️  Iteration ${ITERATION} 통합 JSON 생성 실패${NC}"
    fi
    
    # 다음 iteration 전 대기 (마지막 iteration이 아닌 경우)
    if [ $ITERATION -lt $ITERATIONS ]; then
        echo -e "${YELLOW}⏳ Waiting 10 seconds before next iteration...${NC}"
        sleep 10
        echo ""
    fi
    
done

# ============================================================================
# N회 실험 완료 후 각 GPU별 Excel 생성 (N회 결과 통합)
# ============================================================================

echo ""
echo -e "${CYAN}📊 각 GPU별 Excel 생성 중 (N회 결과 통합)...${NC}"
for GPU_ID in 0 1 2 3; do
    JSON_OUTPUT_DIR="${SESSION_DIR}/gpu_${GPU_ID}_result"
    EXCEL_OUTPUT_DIR="${SESSION_DIR}/gpu_${GPU_ID}_test_summary"
    
    echo "  GPU${GPU_ID}: JSON 폴더 ${JSON_OUTPUT_DIR}"
    docker exec geon_python_unified python3 /app/ksubscribe_share/generate_excel_report.py \
        --model "${MODEL_NAME}" \
        --json-dir "${JSON_OUTPUT_DIR}" \
        --iterations "${ITERATIONS}" \
        --output-dir "${EXCEL_OUTPUT_DIR}"
    
    if [ $? -eq 0 ]; then
        echo "  ✅ GPU${GPU_ID} Excel 생성 완료!"
    else
        echo "  ⚠️  GPU${GPU_ID} Excel 생성 실패"
    fi
done

# ============================================================================
# 4-Way 통합 Excel 생성 (N회 결과 통합)
# ============================================================================

echo ""
echo -e "${CYAN}📊 4-Way 통합 Excel 생성 중 (N회 결과 통합)...${NC}"
JSON_4WAY_DIR="${SESSION_DIR}/gpu_4way_result"
EXCEL_4WAY_DIR="${SESSION_DIR}/gpu_4way_test_summary"

docker exec geon_python_unified python3 /app/ksubscribe_share/generate_excel_report.py \
    --model "${MODEL_NAME}" \
    --json-dir "${JSON_4WAY_DIR}" \
    --iterations "${ITERATIONS}" \
    --output-dir "${EXCEL_4WAY_DIR}"

if [ $? -eq 0 ]; then
    echo "  ✅ 4-Way 통합 Excel 생성 완료!"
else
    echo "  ⚠️  4-Way 통합 Excel 생성 실패"
fi

# ============================================================================
# 전체 반복 완료 - 4-way 통합 보고서 생성
# ============================================================================

echo ""
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}✅ All ${ITERATIONS} iterations completed!${NC}"
echo -e "${GREEN}==========================================${NC}"

echo ""
echo "📁 생성된 JSON 파일 목록:"
for GPU_ID in 0 1 2 3; do
    JSON_COUNT=$(docker exec geon_python_unified bash -c "ls ${SESSION_DIR}/gpu_${GPU_ID}_result/*.json 2>/dev/null | wc -l" || echo "0")
    echo "  GPU${GPU_ID}: ${JSON_COUNT}개 JSON 파일"
done

echo ""
MERGED_JSON_COUNT=$(docker exec geon_python_unified bash -c "ls ${SESSION_DIR}/gpu_4way_result/*.json 2>/dev/null | wc -l" || echo "0")
echo "  4-Way 통합: ${MERGED_JSON_COUNT}개 JSON 파일 (gpu_4way_result/)"

echo ""
echo "📁 생성된 GPU별 Excel 파일:"
for GPU_ID in 0 1 2 3; do
    EXCEL_FILES=$(docker exec geon_python_unified bash -c "ls ${SESSION_DIR}/gpu_${GPU_ID}_test_summary/*.xlsx 2>/dev/null" || echo "")
    if [ -n "$EXCEL_FILES" ]; then
        echo "  GPU${GPU_ID}: ✅ Excel 생성됨"
    else
        echo "  GPU${GPU_ID}: ⚠️  Excel 없음"
    fi
done

echo ""
EXCEL_4WAY=$(docker exec geon_python_unified bash -c "ls ${SESSION_DIR}/gpu_4way_test_summary/*.xlsx 2>/dev/null" || echo "")
if [ -n "$EXCEL_4WAY" ]; then
    echo "  4-Way 통합: ✅ Excel 생성됨 (gpu_4way_test_summary/)"
else
    echo "  4-Way 통합: ⚠️  Excel 없음"
fi

echo ""
echo -e "${CYAN}📊 결과 요약:${NC}"
echo -e "   반복 횟수: ${ITERATIONS}"
echo -e "   세션 ID: ${SESSION_ID}"
echo -e "   모델: ${MODEL_NAME}"
echo -e "   세션 디렉토리: ${SESSION_DIR}"
echo -e "   GPU별 JSON: gpu_X_result/ (각 GPU당 ${ITERATIONS}개)"
echo -e "   통합 JSON: gpu_4way_result/ (${ITERATIONS}개)"
echo -e "   GPU별 Excel: gpu_X_test_summary/ (각 GPU당 1개)"
echo -e "   통합 Excel: gpu_4way_test_summary/ (1개)"
echo -e "   로그 경로: ${LOG_DIR}"

# 임시 OID 파일 정리
echo ""
echo "🧹 임시 OID 파일 정리 중..."
docker exec geon_python_unified bash -c "rm -rf ${TEMP_OID_DIR}" 2>/dev/null || true
echo -e "${GREEN}✅ 정리 완료${NC}"

echo ""
echo -e "${GREEN}🎉 전체 작업 완료!${NC}"
