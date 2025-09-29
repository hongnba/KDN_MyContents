
from bson import ObjectId
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from typing import TypeVar, Type, Dict
T = TypeVar("T", bound="BaseModel")  # BaseModel에 바인딩된 타입 변수


class ContentsImageVO(BaseMongoDocument):
    collectionName = "contents_image"

    def __init__(
        self, 
        keyword: str =None,
        image: bytearray=None,
        imageType: str =None,
        imageUrl: str =None,
        _id: ObjectId = None
    ):

        super().__init__(_id)  # BaseDocument의 생성자를 호출
        self.keyword = keyword
        self.image = image
        self.imageType = imageType
        self.imageUrl = imageUrl

    @classmethod
    def from_mongo(cls, document):
        """MongoDB 문서를 클래스로 변환"""
        if document is None:
            return cls(_id=None, keyword=None, image=None, imageType=None)

        return cls(
            _id=document.get("_id", None),
            keyword=document.get("keyword", None),
            image=document.get("image", None),
            imageType=document.get("imageType", None),
            imageUrl=document.get("imageUrl", None),
        )

    def to_mongo(self):
        """클래스를 MongoDB 문서 형식으로 변환"""
        return {
            "keyword": self.keyword,
            "image": self.image,
            "imageType": self.imageType,
            "imageUrl": self.imageUrl,
        }

    # @classmethod
    # def find_all(cls):
    #     """지원 안함"""
    #     list_result = []
    #     return list_result

    def __repr__(self):
        return f"_id={self._id}, keyword={self.keyword}, image={self.image}, imageType={self.imageType}, imageUrl={self.imageUrl}"