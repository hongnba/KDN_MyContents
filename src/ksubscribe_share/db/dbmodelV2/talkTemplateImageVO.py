from bson import ObjectId
from typing import List
import datetime
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from typing import List
from typing import TypeVar, Type, Dict
T = TypeVar("T", bound="BaseModel")  # BaseModel에 바인딩된 타입 변수


class talkTemplateImageVO(BaseMongoDocument):
    
    collectionName = "talk_template_image"
    
    def __init__(
        self,
        name: str = None,
        imageUrl: str = None,
        imageSource: str = None,
        imageType: str = None,
        _id: ObjectId = None,
    ):

        super().__init__(_id)  # BaseDocument의 생성자를 호출

        # 필드 초기화
        self.name = name
        self.imageUrl = imageUrl
        self.imageSource = imageSource
        self.imageType = imageType
        
    @classmethod
    def from_mongo(cls: Type[T], mongo_data: Dict) -> T:
        """
        MongoDB 문서 데이터를 Python 객체로 변환
        """
        # 상위 클래스의 from_mongo 호출
        instance = super().from_mongo(mongo_data)
        return instance
        
        
