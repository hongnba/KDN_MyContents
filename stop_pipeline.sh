#!/bin/bash
# 백그라운드 파이프라인 중지
# 사용법: ./stop_pipeline.sh

LOG_DIR="/home/mycontents/logs"
PID_FILE="${LOG_DIR}/pipeline.pid"

echo "========================================"
echo "파이프라인 중지"
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
    echo "🛑 프로세스 종료 중..."
    kill "$PID"
    
    # 종료 대기 (최대 10초)
    for i in {1..10}; do
        if ! ps -p "$PID" > /dev/null 2>&1; then
            echo "✅ 프로세스가 정상적으로 종료되었습니다."
            rm -f "$PID_FILE"
            exit 0
        fi
        sleep 1
    done
    
    # 강제 종료
    echo "⚠️  정상 종료 실패. 강제 종료 시도..."
    kill -9 "$PID"
    sleep 1
    
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "✅ 프로세스가 강제 종료되었습니다."
        rm -f "$PID_FILE"
    else
        echo "❌ 프로세스 종료 실패"
        exit 1
    fi
else
    echo "ℹ️  프로세스가 이미 종료되어 있습니다."
    rm -f "$PID_FILE"
fi

echo ""
