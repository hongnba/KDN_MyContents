#!/bin/bash

# 네이버 뉴스 날짜별 스크래핑 및 엑셀 저장 스크립트
# 사용법: ./collect_naver_news_by_date_excel.sh <keyword> <start_date> <end_date>
# 예시: ./collect_naver_news_by_date_excel.sh 한국전력 2025.11.01 2025.11.30

# 컨테이너 이름
CONTAINER_NAME="ksubscribe_python_unified"

# 스크립트 경로
SCRIPT_NAME="collect_naver_news_by_date_excel.py"
SCRIPT_PATH="/app/ksubscribe_share/test/${SCRIPT_NAME}"

# 인자 확인
if [ $# -lt 3 ]; then
    echo "사용법: $0 <keyword> <start_date> <end_date>"
    echo "예시: $0 한국전력 2025.11.01 2025.11.30"
    echo ""
    echo "파라미터 설명:"
    echo "  keyword    : 검색 키워드 (예: 한국전력)"
    echo "  start_date : 시작 날짜 (YYYY.MM.DD 형식, 예: 2025.11.01)"
    echo "  end_date   : 종료 날짜 (YYYY.MM.DD 형식, 예: 2025.11.30)"
    exit 1
fi

KEYWORD="$1"
START_DATE="$2"
END_DATE="$3"

# 날짜 형식 검증
if ! [[ "$START_DATE" =~ ^[0-9]{4}\.[0-9]{2}\.[0-9]{2}$ ]] || ! [[ "$END_DATE" =~ ^[0-9]{4}\.[0-9]{2}\.[0-9]{2}$ ]]; then
    echo "❌ 오류: 날짜 형식이 올바르지 않습니다."
    echo "   올바른 형식: YYYY.MM.DD (예: 2025.11.01)"
    exit 1
fi

echo "============================================================"
echo "네이버 뉴스 날짜별 스크래핑 시작"
echo "============================================================"
echo "검색어: $KEYWORD"
echo "기간: $START_DATE ~ $END_DATE"
echo "컨테이너: $CONTAINER_NAME"
echo "============================================================"
echo ""

# Python 스크립트를 컨테이너에 복사
echo "📋 Python 스크립트를 컨테이너에 복사 중..."

# 스크립트의 절대 경로 찾기
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_SCRIPT_PATH="${SCRIPT_DIR}/${SCRIPT_NAME}"

if [ ! -f "$LOCAL_SCRIPT_PATH" ]; then
    echo "❌ 오류: Python 스크립트를 찾을 수 없습니다: $LOCAL_SCRIPT_PATH"
    exit 1
fi

docker cp "$LOCAL_SCRIPT_PATH" ${CONTAINER_NAME}:${SCRIPT_PATH}

if [ $? -ne 0 ]; then
    echo "❌ 스크립트 복사 실패"
    exit 1
fi

echo "✅ 스크립트 복사 완료"
echo ""

# 컨테이너에서 스크립트 실행
echo "🚀 스크래핑 시작..."
docker exec ${CONTAINER_NAME} python ${SCRIPT_PATH} "$KEYWORD" "$START_DATE" "$END_DATE"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "============================================================"
    echo "✅ 스크래핑 완료!"
    echo "============================================================"
    echo "저장 경로: /app/ksubscribe_share/test/news_scarppings/"
    echo ""
    echo "생성된 파일 목록:"
    docker exec ${CONTAINER_NAME} sh -c "ls -lh /app/ksubscribe_share/test/news_scarppings/naver_news_${KEYWORD}_*.xlsx 2>/dev/null | tail -10"
else
    echo ""
    echo "❌ 스크래핑 중 오류 발생 (종료 코드: $EXIT_CODE)"
    exit 1
fi

