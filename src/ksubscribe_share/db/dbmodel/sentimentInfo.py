
from bson import ObjectId

class SentimentInfo:
    def __init__(self, positiveRatio: str, negativeRatio: str , reason : str ):
        self.positiveRatio = positiveRatio
        self.negativeRatio = negativeRatio
        self.reason = reason
    @classmethod
    def from_mongo(cls, document):
        """MongoDB 문서를 클래스로 변환"""
        
        
        return cls(
            positiveRatio=document.get('positiveRatio'),
            negativeRatio=document.get('negativeRatio'),
            reason=document.get('reason'),

        )

    def to_mongo(self):
        """클래스를 MongoDB 문서 형식으로 변환"""
        return {
            "positiveRatio": self.positiveRatio,
            "negativeRatio": self.negativeRatio,
            "reason": self.reason
        }

    def __repr__(self):
        return f"User(positiveRatio={self.positiveRatio}, negativeRatio={self.negativeRatio}, reason={self.reason})"
    
    
    
