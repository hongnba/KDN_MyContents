from __future__ import annotations  # Forward Reference 사용을 위한 선언

from bson import ObjectId
from pymongo import MongoClient
import datetime
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.contentsCollectHistoryVO import ContentsCollectDetail
from typing import TypeVar, Type, Dict
T = TypeVar("T", bound="BaseModel")  # BaseModel에 바인딩된 타입 변수


class ContentsQueueVO(BaseMongoDocument):

    collectionName = "contents_queue"

    def __init__(
        self,
        contentOrgId: str = None,
        cateId: str = None,
        title: str = None,
        url: str = None,
        shortUrl: datetime = None,
        pubDt:str = None,
        collectDt: str = None, 
        collectKeyword:str = None,
        _id: ObjectId = None,
    ):

        super().__init__(_id)  # BaseDocument의 생성자를 호출
        self.contentOrgId = contentOrgId
        self.cateId = cateId
        self.title = title
        self.url = url
        self.shortUrl = shortUrl 
        self.pubDt = pubDt
        self.collectKeyword = collectKeyword
        self.collectDt = collectDt 

    @classmethod
    def from_collect_detail(cls, orgId:str, cateId:str, collectDetail : ContentsCollectDetail, collectDt,collectKeyword:str) -> ContentsQueueVO: 
        """ContentsCollectDetail 객체로부터 ContentsQueueVO 생성"""
        return cls(
            contentOrgId=orgId,
            cateId=cateId,
            title=collectDetail.title,
            url=collectDetail.url,
            shortUrl=collectDetail.shortUrl,
            collectDt=collectDt,
            collectKeyword=collectKeyword,
            pubDt = collectDetail.pubDt
        )
    