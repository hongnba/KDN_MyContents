from bson import ObjectId
from typing import List
import datetime

from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from typing import TypeVar, Type, Dict
T = TypeVar("T", bound="BaseModel")  # BaseModel에 바인딩된 타입 변수


class PredefineKeywordVO(BaseMongoDocument):

    collectionName = "predefine_keyword"

    def __init__(
        self,
        keyword: str = None,
        regDt: datetime = None,
        regId: str = None,
        editDt: datetime = None,
        editId: str = None,
        subscriberIds: List[str] = None,
        subkeywords: List[str] = None,
        _id: ObjectId = None,
    ):

        super().__init__(_id)  # BaseDocument의 생성자를 호출
        self.keyword = keyword
        self.regDt = regDt
        self.regId = regId
        self.editDt = editDt
        self.editId = editId
        self.subscriberIds = subscriberIds if subscriberIds is not None else []
        self.subkeywords = subkeywords if subkeywords is not None else []
        
        
        
        

