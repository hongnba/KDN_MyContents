#!/bin/bash
# 백그라운드 파이프라인 상태 확인
# 사용법: ./check_pipeline_status.sh

LOG_DIR="/home/mycontents/logs"
PID_FILE="${LOG_DIR}/pipeline.pid"

echo "========================================"
echo "파이프라인 상태 확인"
echo "========================================"
echo ""

# PID 파일 확인
if [ ! -f "$PID_FILE" ]; then
    echo "❌ PID 파일을 찾을 수 없습니다: $PID_FILE"
    echo "   백그라운드 프로세스가 실행 중이지 않습니다."
    exit 1
fi

PID=$(cat "$PID_FILE")
echo "📌 저장된 PID: $PID"
echo ""

# 프로세스 실행 여부 확인
if ps -p "$PID" > /dev/null 2>&1; then
    echo "✅ 프로세스 실행 중"
    echo ""
    ps -p "$PID" -o pid,etime,cmd
    echo ""
    
    # 최신 로그 파일 찾기
    LATEST_LOG=$(ls -t ${LOG_DIR}/pipeline_*.log 2>/dev/null | head -1)
    if [ -n "$LATEST_LOG" ]; then
        echo "📝 최신 로그 파일: $LATEST_LOG"
        echo ""
        echo "🔍 최근 로그 (마지막 20줄):"
        echo "----------------------------------------"
        tail -20 "$LATEST_LOG"
        echo "----------------------------------------"
        echo ""
        echo "💡 전체 로그 보기: tail -f $LATEST_LOG"
    fi
else
    echo "❌ 프로세스가 실행 중이지 않습니다 (PID: $PID)"
    echo ""
    
    # 최신 로그 파일에서 종료 상태 확인
    LATEST_LOG=$(ls -t ${LOG_DIR}/pipeline_*.log 2>/dev/null | head -1)
    if [ -n "$LATEST_LOG" ]; then
        echo "📝 최신 로그 파일: $LATEST_LOG"
        echo ""
        echo "🔍 마지막 20줄:"
        echo "----------------------------------------"
        tail -20 "$LATEST_LOG"
        echo "----------------------------------------"
    fi
fi

echo ""
