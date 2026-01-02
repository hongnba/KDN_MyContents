#!/bin/bash
# 백그라운드에서 파이프라인 실행 (SSH 종료 후에도 계속 실행됨)
# 사용법: ./run_pipeline_background.sh

LOG_DIR="/home/mycontents/logs"
LOG_FILE="${LOG_DIR}/pipeline_$(date +%Y%m%d_%H%M%S).log"

# 로그 디렉토리 생성
mkdir -p "$LOG_DIR"

echo "========================================" | tee -a "$LOG_FILE"
echo "파이프라인 백그라운드 실행 시작" | tee -a "$LOG_FILE"
echo "시작 시간: $(date)" | tee -a "$LOG_FILE"
echo "로그 파일: $LOG_FILE" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# nohup으로 백그라운드 실행 (SSH 종료 후에도 계속 실행)
nohup docker exec ksubscribe_python_unified \
    python3 /app/docker_shell/main_collect_and_scrapping.py \
    >> "$LOG_FILE" 2>&1 &

PID=$!

echo "" | tee -a "$LOG_FILE"
echo "✅ 백그라운드 프로세스 시작됨" | tee -a "$LOG_FILE"
echo "   PID: $PID" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "📋 명령어 안내:" | tee -a "$LOG_FILE"
echo "   - 로그 확인: tail -f $LOG_FILE" | tee -a "$LOG_FILE"
echo "   - 프로세스 확인: ps -p $PID" | tee -a "$LOG_FILE"
echo "   - 프로세스 종료: kill $PID" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# PID를 파일로 저장
PID_FILE="${LOG_DIR}/pipeline.pid"
echo "$PID" > "$PID_FILE"
echo "PID 저장 위치: $PID_FILE" | tee -a "$LOG_FILE"
echo ""
echo "🎯 퇴근하셔도 됩니다! 작업은 계속 실행됩니다."
