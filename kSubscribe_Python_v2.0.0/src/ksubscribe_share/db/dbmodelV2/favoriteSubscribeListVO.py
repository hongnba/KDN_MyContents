from bson import ObjectId
from typing import List
import datetime

from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.memberVO import OrgIdAndCateId
from typing import TypeVar, Type, Dict
T = TypeVar("T", bound="BaseModel")  # BaseModel에 바인딩된 타입 변수

        
class FavoriteSubscribeListVO(BaseMongoDocument):

    collectionName = "favorite_subscribe_list"

    def __init__(
        self,
        favoriteListId: str = None,
        favoriteListGubun: str = None,
        favoriteListName: str = None,
        favoriteListDesc: str = None,
        regDt: datetime = None,
        regId: str = None,
        editDt: datetime = None,
        editId: str = None,
        imageType :str = None,
        imageSource : str = None,
        cIWidth: str = None,
        cIHeight: str = None,
        keywords: List[str] = None,
        orgIdAndCateIds : List[OrgIdAndCateId] = None, 
        _id: ObjectId = None,
    ):

        super().__init__(_id)  # BaseDocument의 생성자를 호출
        self.favoriteListId = favoriteListId
        self.favoriteListGubun = favoriteListGubun
        self.favoriteListName = favoriteListName
        self.favoriteListDesc = favoriteListDesc
        self.regDt = regDt
        self.regId = regId
        self.editDt = editDt
        self.editId = editId
        self.imageType = imageType
        self.imageSource = imageSource
        self.cIWidth: str = cIWidth,
        self.cIHeight: str = cIHeight,
        self.keywords = keywords if keywords is not None else []
        self.orgIdAndCateIds = orgIdAndCateIds if orgIdAndCateIds is not None else []
        
    def to_mongo(self):
        """클래스를 MongoDB 문서 형식으로 변환"""
        # 상위 클래스의 to_mongo 호출
        mongo_data = super().to_mongo()

        # 사용자 정의 객체를 변환
        if self.orgIdAndCateIds:
            mongo_data["orgIdAndCateIds"] = [item.to_mongo() for item in self.orgIdAndCateIds]

        return mongo_data
    
    @classmethod
    def from_mongo(cls: Type[T], mongo_data: Dict) -> T:
        """
        MongoDB 문서 데이터를 Python 객체로 변환
        """
        # 상위 클래스의 from_mongo 호출
        instance = super().from_mongo(mongo_data)

        # 요청 카테고리 변환
        instance.orgIdAndCateIds = [
            OrgIdAndCateId.from_mongo(orgIdAndCateId)   
            for orgIdAndCateId in mongo_data.get("orgIdAndCateIds", [])
        ]

        return instance
