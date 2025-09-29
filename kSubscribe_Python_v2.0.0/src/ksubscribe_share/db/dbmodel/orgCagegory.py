
from bson import ObjectId
from typing import List

class OrgCagegory:
    def __init__(self, orgId: str, categoryIdList: List[str]):
        self.orgId = orgId
        self.categoryIdList = categoryIdList if categoryIdList is not None else []

    @classmethod
    def from_mongo(cls, document):
        """MongoDB 문서를 클래스로 변환"""
                
        return cls(
            orgId=document.get('orgId'),
            categoryIdList=document.get('categoryIdList', []),
            
        )

    def to_mongo(self):
        """클래스를 MongoDB 문서 형식으로 변환"""
        return {
            "orgId": self.orgId,
            "categoryIdList": self.categoryIdList
        }

    def __repr__(self):
        return f"User(orgId={self.orgId}, categoryIdList={self.categoryIdList})"
    
    
    
