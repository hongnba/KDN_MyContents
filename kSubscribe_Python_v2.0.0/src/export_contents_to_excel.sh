#!/bin/bash
# MongoDB contents collection에서 날짜별로 데이터를 조회하여 Excel로 저장하는 스크립트
# 사용법: ./export_contents_to_excel.sh 2025-11-22 2025-11-26

# 컨테이너 이름
CONTAINER_NAME="ksubscribe_python_unified"

# 날짜 인자 확인
if [ $# -eq 0 ]; then
    echo "❌ 사용법: $0 <날짜1> <날짜2> ..."
    echo "예시: $0 2025-11-22 2025-11-26"
    exit 1
fi

# 날짜 리스트를 인자로 받기
DATE_ARGS="$@"

echo "🚀 Excel 내보내기 시작..."
echo "📅 날짜: $DATE_ARGS"
echo ""

# 스크립트 파일을 컨테이너에 복사
SCRIPT_PATH="/home/themiraclesoft/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src/export_contents_to_excel.py"
docker cp "$SCRIPT_PATH" ${CONTAINER_NAME}:/app/ 2>/dev/null || echo "⚠️  스크립트 파일 복사 건너뜀 (이미 존재할 수 있음)"

# Python 스크립트 실행
echo "📊 MongoDB 쿼리 실행 중..."
docker exec ${CONTAINER_NAME} python /app/export_contents_to_excel.py $DATE_ARGS

# 실행 결과 확인
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo "❌ 실행 실패 (종료 코드: $EXIT_CODE)"
    exit $EXIT_CODE
fi

# 생성된 Excel 파일 찾기
echo ""
echo "📁 파일 복사 중..."

# 컨테이너 내부에서 최신 파일 찾기 (ksubscribe_share/test/daily_summary 폴더)
LATEST_FILE=$(docker exec ${CONTAINER_NAME} sh -c "ls -t /app/ksubscribe_share/test/daily_summary/contents_export_*.xlsx 2>/dev/null | head -1" | tr -d '\r\n')

if [ -z "$LATEST_FILE" ]; then
    echo "❌ Excel 파일을 찾을 수 없습니다."
    echo "디버깅: 컨테이너 내부 파일 목록:"
    docker exec ${CONTAINER_NAME} ls -la /app/ksubscribe_share/test/daily_summary/contents_export_*.xlsx 2>/dev/null || echo "  /app/ksubscribe_share/test/daily_summary에 xlsx 파일 없음"
    exit 1
fi

# 파일명 추출
FILENAME=$(basename "$LATEST_FILE")

# 호스트의 ksubscribe_share/test/daily_summary 폴더 생성 (절대 경로로 고정)
# Python 스크립트 경로를 기준으로 출력 디렉토리 계산
PYTHON_SCRIPT_DIR="/home/themiraclesoft/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src"
OUTPUT_DIR="${PYTHON_SCRIPT_DIR}/ksubscribe_share/test/daily_summary"
mkdir -p "$OUTPUT_DIR"

# 파일 복사
docker cp ${CONTAINER_NAME}:${LATEST_FILE} "$OUTPUT_DIR/"

if [ $? -eq 0 ]; then
    FULL_PATH="${OUTPUT_DIR}/${FILENAME}"
    echo "✅ 파일 복사 완료: $FILENAME"
    echo "📄 저장 경로: $FULL_PATH"
    echo "📁 절대 경로: $(cd "$OUTPUT_DIR" && pwd)/$FILENAME"
else
    echo "❌ 파일 복사 실패"
    exit 1
fi

echo ""
echo "✅ 완료!"

