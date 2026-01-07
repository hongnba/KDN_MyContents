#!/bin/bash
# daily_stats 키워드 비교 분석 실행 스크립트
# 사용법: ./run_daily_stats_comparison.sh [org_id] [target_date]
# 예시: ./run_daily_stats_comparison.sh A0010 2025-12-30

# 컨테이너 이름
CONTAINER_NAME="ksubscribe_python_unified"

# 스크립트 경로 (컨테이너 내부 - 절대 경로)
SCRIPT_PATH="/app/ksubscribe_share/test/keyword_comparison_daily_stats.py"

# 로컬 결과 디렉토리 (절대 경로)
LOCAL_RESULT_DIR="/home/themiraclesoft/mycontents/Geon_KDN_MyContents/kSubscribe_Python_v2.0.0/src/ksubscribe_share/test/daily_comparison_result"

# 기본값 설정
ORG_ID=${1:-"A0010"}
TARGET_DATE=${2:-"2025-12-30"}

echo "=========================================="
echo "daily_stats 키워드 비교 분석 실행"
echo "=========================================="
echo "기관 ID: $ORG_ID"
echo "조회 날짜: $TARGET_DATE"
echo "=========================================="
echo ""

# 컨테이너가 실행 중인지 확인
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo "❌ 오류: 컨테이너 '$CONTAINER_NAME'가 실행 중이 아닙니다."
    echo "   컨테이너를 먼저 시작해주세요."
    exit 1
fi

# 스크립트 실행
echo "📊 분석 시작..."
docker exec "$CONTAINER_NAME" python3 "$SCRIPT_PATH" "$ORG_ID" "$TARGET_DATE"

# 실행 결과 확인
if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ 분석 완료!"
    echo "=========================================="
    echo ""
    echo "📁 결과 파일 위치 (컨테이너 내부):"
    echo "   /app/ksubscribe_share/test/daily_comparison_result/"
    echo ""
    echo "📁 로컬 경로:"
    echo "   $LOCAL_RESULT_DIR"
    echo ""
    echo "생성된 파일 목록:"
    ls -lh "$LOCAL_RESULT_DIR"/*${ORG_ID}_${TARGET_DATE//-}* 2>/dev/null | awk '{print "   " $9}'
    echo ""
else
    echo ""
    echo "=========================================="
    echo "❌ 분석 실패"
    echo "=========================================="
    exit 1
fi

