import sys
import os

# Add the src directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from ksubscribe_share.db.mongoManager import MongoManager

def check_duplicate():
    mongo_manager = MongoManager()
    collection = mongo_manager.getCollection('contents')
    
    target_url = "https://www.motie.go.kr/kor/article/ATCLc01b2801b/69175/view"
    
    query = {
        "$or": [
            { "url": target_url },
            { "link": target_url }
        ]
    }
    
    results = list(collection.find(query, {"_id": 1, "title": 1, "url": 1, "link": 1}))
    
    print(f"검색 대상 URL: {target_url}")
    print(f"검색된 문서 개수: {len(results)}")
    
    for doc in results:
        print("-" * 50)
        print(f"ID: {doc.get('_id')}")
        print(f"Title: {doc.get('title')}")
        print(f"URL: {doc.get('url')}")
        print(f"Link: {doc.get('link')}")

if __name__ == "__main__":
    check_duplicate()
