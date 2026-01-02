#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
가장 간단한 기사 분석 예제

사용법:
  python3 simple_test.py
"""

# 여기에 테스트할 기사 URL 또는 원문을 입력하세요
TEST_URL = "https://www.motie.go.kr/kor/article/ATCL2826a2625/69968/view"
TEST_TEXT = None  # 또는 "여기에 원문 직접 입력..."

# 기관 및 카테고리 정보
ORG_ID = "A0001"  # 산업통상자원부
CATEGORY_ID = "B0002"  # 사업공고

# =============================================================================
# 이하 코드는 수정 불필요
# =============================================================================

def main():
    print("="*60)
    print("🔍 간단 기사 분석 테스트")
    print("="*60)
    
    if TEST_TEXT:
        print(f"\n📝 입력 방식: 원문 직접 입력")
        print(f"본문 길이: {len(TEST_TEXT)} 자")
        print(f"기관 ID: {ORG_ID}")
        print(f"카테고리 ID: {CATEGORY_ID}")
    else:
        print(f"\n🌐 입력 방식: URL 자동 스크래핑")
        print(f"URL: {TEST_URL}")
        print(f"기관 ID: {ORG_ID}")
        print(f"카테고리 ID: {CATEGORY_ID}")
    
    print("\n" + "-"*60)
    print("⚠️  실제 분석을 실행하려면 아래 명령어를 사용하세요:")
    print("-"*60)
    
    if TEST_TEXT:
        print(f'\npython3 test_single_article.py \\')
        print(f'  --text "{TEST_TEXT[:50]}..." \\')
        print(f'  --org "{ORG_ID}" \\')
        print(f'  --category "{CATEGORY_ID}"')
        
        # 또는 파일로 저장
        filename = "test_article.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(TEST_TEXT)
        print(f'\n# 또는 파일로 저장 후:')
        print(f'python3 test_single_article.py \\')
        print(f'  --file "{filename}" \\')
        print(f'  --org "{ORG_ID}" \\')
        print(f'  --category "{CATEGORY_ID}"')
    else:
        print(f'\npython3 test_single_article.py \\')
        print(f'  --url "{TEST_URL}" \\')
        print(f'  --org "{ORG_ID}" \\')
        print(f'  --category "{CATEGORY_ID}"')
    
    print("\n" + "="*60)
    print("💡 필요한 패키지가 없으면 먼저 설치하세요:")
    print("="*60)
    print("pip3 install pytz langchain_ollama pymongo selenium beautifulsoup4")
    print()

if __name__ == "__main__":
    main()
