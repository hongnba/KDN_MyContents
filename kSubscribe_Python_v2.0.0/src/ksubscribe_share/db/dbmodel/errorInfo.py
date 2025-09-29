
from bson import ObjectId

class ErrorInfo:
    def __init__(self, type: str, reason: str):
        self.type = type
        self.reason = reason

    @classmethod
    def from_mongo(cls, document):
        """MongoDB 문서를 클래스로 변환"""
        
        
        return cls(
            type=document.get('type'),
            reason=document.get('reason')
        )

    def to_mongo(self):
        """클래스를 MongoDB 문서 형식으로 변환"""
        return {
            "type": self.type,
            "reason": self.reason,
        }

    def __repr__(self):
        return f"User(type={self.type}, reason={self.reason})"
    
    
    
