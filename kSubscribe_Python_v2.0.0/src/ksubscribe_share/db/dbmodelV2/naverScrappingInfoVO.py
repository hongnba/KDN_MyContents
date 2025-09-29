from bson import ObjectId
from pymongo import MongoClient
import datetime
from typing import List

from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodel.newsMeta import NewsMeta
from ksubscribe_share.db.dbmodel.newsContents import NewsContents
from ksubscribe_share.db.dbmodelV2.errorInfo import ErrorInfo
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO
from ksubscribe_share.db.dbmodelV2.dbEnums import SignMethodEnum
from typing import TypeVar, Type, Dict
T = TypeVar("T", bound="BaseModel")  # BaseModel에 바인딩된 타입 변수

from Crypto.Cipher import AES
import base64
import ksubscribe_share.config as Conf

# 사용자 계정 정보 클래스 백업 : V2.0.0 에서 만들었던 클래스가 MongoDB 에서 Python 객체로 변환이 안되는 현상이 있음.
# - 접속 IP, 접속일시 정보도 모두 기록


class NaverScrappingInfoVO(BaseModel):
    
    collectionName = "naver_scrapping_info"
    
    def __init__(
        self,
        domain: str = None,
        collectMethod:str=None,   
        tagAttr:str=None,
        tagAttrValue:str=None,
        tagElement:str=None,
    ):
        self.domain = domain
        self.collectMethod = collectMethod
        self.tagAttr = tagAttr
        self.tagAttrValue = tagAttrValue
        self.tagElement = tagElement        
  
