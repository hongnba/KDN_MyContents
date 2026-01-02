#!/bin/bash

# 백그라운드에서 안정적으로 실행하는 래퍼 스크립트
# 사용법: ./run_llm_test_background.sh [반복횟수]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN_SCRIPT="/home/themiraclesoft/mycontents/run_llm_test_10_times.sh"
LOG_DIR="${SCRIPT_DIR}"
LOG_FILE="${LOG_DIR}/llm_test_background_$(date +%Y%m%d_%H%M%S).log"

# 반복 횟수 (기본값: 1)
ITERATIONS=${1:-1}

echo "=========================================="
echo "백그라운드 실행 시작"
echo "반복 횟수: ${ITERATIONS}"
echo "로그 파일: ${LOG_FILE}"
echo "=========================================="
echo ""

# setsid로 세션을 완전히 분리하고 백그라운드 실행
# nohup과 함께 사용하여 더욱 안정적으로
nohup setsid bash "${MAIN_SCRIPT}" "${ITERATIONS}" >> "${LOG_FILE}" 2>&1 &

PID=$!
echo "프로세스 ID: ${PID}"
echo "로그 파일: ${LOG_FILE}"
echo ""
echo "프로세스 확인: ps aux | grep ${PID}"
echo "로그 확인: tail -f ${LOG_FILE}"
echo ""

# PID 파일 저장 (나중에 확인용)
echo "${PID}" > "${LOG_DIR}/llm_test_last_pid.txt"
echo "PID가 ${LOG_DIR}/llm_test_last_pid.txt에 저장되었습니다."

