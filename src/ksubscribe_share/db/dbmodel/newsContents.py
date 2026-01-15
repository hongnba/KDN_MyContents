
from bson import ObjectId

class NewsContents:
    def __init__(self, title: str, contents: str, image: str):
        self.title = title
        self.contents = contents
        self.image = image

    @classmethod
    def from_mongo(cls, document):
        """MongoDB 문서를 클래스로 변환"""
                
        return cls(
            title=document.get('title'),
            contents=document.get('contents'),
            image=document.get('image')
        )

    def to_mongo(self):
        """클래스를 MongoDB 문서 형식으로 변환"""
        return {
            "title": self.title,
            "contents": self.contents,
            "image": self.image
        }

    def __repr__(self):
        return f"User(title={self.title}, contents={self.contents}, image={self.image})"
    
    
    
