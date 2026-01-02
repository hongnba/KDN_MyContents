
import sys
import os
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 Python path에 추가
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, "/app") # Docker container path

from ksubscribe_share.db.service.predefineKeywordService import PredefineKeywordService
from ksubscribe_share.db.dbmodelV2.predefineKeywordVO import PredefineKeywordVO

def verify_operations():
    service = PredefineKeywordService()
    target_keyword = "더미라클소프트"
    test_keyword = "더미라클소프트_TEST"

    print("=== 1. 기존 키워드 확인 ===")
    # 직접 쿼리하여 확인
    collection = service.mongoManager.getCollection(service.collectionName)
    existing = collection.find_one({"keyword": target_keyword})
    
    if existing:
        print(f"✅ '{target_keyword}' 키워드가 존재합니다.")
        print(f"   ID: {existing.get('_id')}")
        print(f"   Data: {existing}")
    else:
        print(f"❌ '{target_keyword}' 키워드를 찾을 수 없습니다.")

    print("\n=== 2. 테스트 키워드 추가/삭제 검증 ===")
    
    # 2-1. 테스트 키워드 추가
    print(f"👉 '{test_keyword}' 추가 시도...")
    new_vo = PredefineKeywordVO(
        keyword=test_keyword,
        regDt=datetime.now(),
        editDt=datetime.now(),
        subscriberIds=[]
    )
    
    if service.add_keyword(new_vo):
        print(f"✅ '{test_keyword}' 추가 성공")
    else:
        print(f"❌ '{test_keyword}' 추가 실패")
        return

    # 2-2. 추가 확인
    check = collection.find_one({"keyword": test_keyword})
    if check:
        print(f"✅ DB에서 '{test_keyword}' 조회 확인")
    else:
        print(f"❌ DB에서 '{test_keyword}' 조회 실패")

    # 2-3. 테스트 키워드 삭제
    print(f"👉 '{test_keyword}' 삭제 시도...")
    service.remove_keyword(test_keyword)
    
    # 2-4. 삭제 확인
    check_deleted = collection.find_one({"keyword": test_keyword})
    if not check_deleted:
        print(f"✅ '{test_keyword}' 삭제 확인 (성공)")
    else:
        print(f"❌ '{test_keyword}' 삭제 실패 (여전히 존재함)")

if __name__ == "__main__":
    verify_operations()
