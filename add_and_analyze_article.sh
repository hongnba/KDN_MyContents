#!/bin/bash
# 새로운 기사를 추가하고 Ollama 분석을 실행하는 샘플 스크립트

# 사용법: ./add_and_analyze_article.sh

echo "=================================================="
echo "새 기사 Ollama 분석 - 대화형 스크립트"
echo "=================================================="
echo ""

# 기사 정보 입력받기
echo "📝 기사 정보를 입력하세요:"
echo ""

read -p "1. URL: " URL
read -p "2. 제목: " TITLE
read -p "3. 기관 코드 (기본값: A0013-연합뉴스): " ORG_ID
ORG_ID=${ORG_ID:-A0013}

read -p "4. 기관명 (기본값: 연합뉴스): " ORG_NAME
ORG_NAME=${ORG_NAME:-연합뉴스}

read -p "5. 카테고리 코드 (기본값: B0001-뉴스): " CATEGORY_ID
CATEGORY_ID=${CATEGORY_ID:-B0001}

read -p "6. 카테고리명 (기본값: 뉴스): " CATEGORY_NAME
CATEGORY_NAME=${CATEGORY_NAME:-뉴스}

echo ""
echo "7. 기사 본문을 입력하세요 (여러 줄 가능, 완료 후 Ctrl+D):"
CONTENTS=$(cat)

echo ""
echo "=================================================="
echo "입력 정보 확인"
echo "=================================================="
echo "URL: $URL"
echo "제목: $TITLE"
echo "기관: $ORG_NAME ($ORG_ID)"
echo "카테고리: $CATEGORY_NAME ($CATEGORY_ID)"
echo "본문 길이: ${#CONTENTS} 문자"
echo ""

read -p "계속 진행하시겠습니까? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ]; then
    echo "취소되었습니다."
    exit 0
fi

# JSON 파일 생성
JSON_FILE="/tmp/article_$(date +%s).json"
cat > "$JSON_FILE" << EOF
{
  "title": "$TITLE",
  "url": "$URL",
  "contentsOrgId": "$ORG_ID",
  "contentsOrgName": "$ORG_NAME",
  "categoryId": "$CATEGORY_ID",
  "categoryName": "$CATEGORY_NAME",
  "rawCollectSucYN": "Y",
  "contentsRaw": {
    "title": "$TITLE",
    "contents": "$CONTENTS",
    "image": "",
    "errorInfo": null
  },
  "metaSucYN": "N",
  "lookCount": 0,
  "likeCount": 0,
  "disLikeCount": 0,
  "lookIds": [],
  "likeIds": [],
  "disLikeIds": []
}
EOF

echo ""
echo "=================================================="
echo "1단계: MongoDB에 기사 추가 중..."
echo "=================================================="

RESULT=$(docker exec -i ksubscribe_mongodb mongo --quiet mycontents --eval \
  "db.contents.insertOne($(cat $JSON_FILE))" 2>&1)

if echo "$RESULT" | grep -q "insertedId"; then
    echo "✅ MongoDB 저장 성공!"
    OBJECT_ID=$(echo "$RESULT" | grep -oP 'ObjectId\("\K[^"]+')
    echo "   문서 ID: $OBJECT_ID"
else
    echo "❌ MongoDB 저장 실패:"
    echo "$RESULT"
    rm -f "$JSON_FILE"
    exit 1
fi

rm -f "$JSON_FILE"

echo ""
echo "=================================================="
echo "2단계: Ollama 분석 실행 중..."
echo "=================================================="
echo "⏱️  예상 소요 시간: 60-80초"
echo ""

docker exec python_new timeout 300 python3 /app/run_single_url_ollama.py "$URL"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "=================================================="
    echo "3단계: 결과 확인"
    echo "=================================================="
    
    docker exec -i ksubscribe_mongodb mongo --quiet mycontents --eval "
      var doc = db.contents.findOne({url: '$URL'});
      if (doc && doc.contentsMeta) {
        print('✅ 분석 완료!');
        print('');
        print('📝 짧은 요약:');
        print('   ' + doc.contentsMeta.shortSummary);
        print('');
        print('🔑 키워드:');
        doc.contentsMeta.keywords.forEach(function(k) {
          print('   - ' + k);
        });
        print('');
        print('😊 감성 분석:');
        if (doc.contentsMeta.sentiments && doc.contentsMeta.sentiments.length > 0) {
          var s = doc.contentsMeta.sentiments[0];
          print('   긍정: ' + s.positiveRatio + '%');
          print('   부정: ' + s.negativeRatio + '%');
          print('   중립: ' + s.neutralRatio + '%');
        }
      } else {
        print('❌ 분석 결과를 찾을 수 없습니다.');
      }
    "
    
    echo ""
    echo "=================================================="
    echo "🎉 완료!"
    echo "=================================================="
else
    echo ""
    echo "❌ Ollama 분석 실패 (Exit code: $EXIT_CODE)"
fi
