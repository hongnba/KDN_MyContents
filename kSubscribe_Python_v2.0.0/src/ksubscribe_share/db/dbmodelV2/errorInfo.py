
from bson import ObjectId
import datetime 
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from typing import TypeVar, Type, Dict
T = TypeVar("T", bound="BaseModel")  # BaseModel에 바인딩된 타입 변수

class ErrorInfo(BaseModel):
    def __init__(self, errorYN : str = None,  type: str = None, reason: str = None, date:datetime = None):
        self.errorYN = errorYN
        self.type = type
        self.reason = reason
        self.date = date



    
