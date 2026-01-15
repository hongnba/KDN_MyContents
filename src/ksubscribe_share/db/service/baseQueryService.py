
from bson import ObjectId
import datetime
from typing import List

import datetime

from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO, ContentsOrgCategory
from ksubscribe_share.db.dbmodelV2.contentsCollectHistoryVO import ContentsCollectDetail, ContentsCollect, ContentsCollectHistoryVO
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
from ksubscribe_share.db.mongoManager import MongoManager

from pymongo.results import InsertOneResult, UpdateResult, DeleteResult
from typing import List, Tuple, Optional
from bson import ObjectId


# 컨텐츠 수집 이력
class BaseQueryService:
    mongoManager = MongoManager()  # MongoManager 싱글톤 인스턴스를 사용

    def __init__(self):
        pass

    # find ################################################################
    @classmethod
    def find_one(cls, mongoModel: BaseMongoDocument) -> None:
        collection = cls.mongoManager.getCollection(mongoModel.collectionName)
        document = collection.find_one({"_id": mongoModel._id})
        mongoModel.from_mongo(document)

    @classmethod
    def find_one_id(cls, mongoModel: BaseMongoDocument, _id: str) -> Optional[BaseMongoDocument]:
        collection = cls.mongoManager.getCollection(mongoModel.collectionName)
        document = collection.find_one({"_id": ObjectId(_id)})
        return mongoModel.from_mongo(document) if document else None

    @classmethod
    def find_many(
        cls, mongoModel: BaseMongoDocument, query: dict, skip: int = 0, limit: int = 1000
    ) -> Tuple[List[BaseMongoDocument], object]:
        collection = cls.mongoManager.getCollection(mongoModel.collectionName)
        cursor = collection.find(query).skip(skip).limit(limit)
        list_result = [mongoModel.from_mongo(doc) for doc in cursor]
        return list_result, cursor

    @classmethod
    def find_all(cls, mongoModel: BaseMongoDocument) -> Tuple[List[BaseMongoDocument], object]:
        collection = cls.mongoManager.getCollection(mongoModel.collectionName)
        cursor = collection.find()
        list_result = [mongoModel.from_mongo(doc) for doc in cursor]
        return list_result, cursor

    # insert ################################################################
    @classmethod
    def insert_one(cls, mongoModel: BaseMongoDocument, session=None) -> InsertOneResult:
        collection = cls.mongoManager.getCollection(mongoModel.collectionName)
        if session is None:
            result = collection.insert_one(mongoModel.to_mongo())
        else:
            result = collection.insert_one(mongoModel.to_mongo(), session=session)
        mongoModel._id = result.inserted_id  # 삽입된 문서의 _id를 설정
        return result

    @classmethod
    def insert(cls, mongoModel: BaseMongoDocument, target: dict) -> InsertOneResult:
        collection = cls.mongoManager.getCollection(mongoModel.collectionName)
        result = collection.insert_one(target)
        return result

    # update ################################################################
    @classmethod
    def update_one(cls, mongoModel: BaseMongoDocument, session=None) -> UpdateResult:
        collection = cls.mongoManager.getCollection(mongoModel.collectionName)
        if session is None:
            result = collection.update_one({"_id": mongoModel._id}, {"$set": mongoModel.to_mongo()})
        else:
            result = collection.update_one(
                {"_id": mongoModel._id}, {"$set": mongoModel.to_mongo()}, session=session
            )
        return result

    @classmethod
    def update(cls, mongoModel: BaseMongoDocument, where: dict, target: dict) -> UpdateResult:
        collection = cls.mongoManager.getCollection(mongoModel.collectionName)
        result = collection.update_many(where, {"$set": target})
        return result

    @classmethod
    def update_count(cls, mongoModel: BaseMongoDocument, where: dict, target: dict) -> UpdateResult:
        collection = cls.mongoManager.getCollection(mongoModel.collectionName)
        result = collection.update_one(where, {"$inc": target})
        return result

    @classmethod
    def update_count_byid(cls, mongoModel: BaseMongoDocument, _id: str, target: dict) -> UpdateResult:
        collection = cls.mongoManager.getCollection(mongoModel.collectionName)
        result = collection.update_one({"_id": ObjectId(_id)}, {"$inc": target})
        return result

    # delete ################################################################
    @classmethod
    def delete_one(cls, mongoModel: BaseMongoDocument) -> DeleteResult:
        collection = cls.mongoManager.getCollection(mongoModel.collectionName)
        result = collection.delete_one({"_id": mongoModel._id})
        return result
    
    # upsert #################################################################
    @classmethod
    def upsert(cls, mongoModel: BaseMongoDocument, filter_condition: dict, target: dict):
        """
        Upsert a document in the MongoDB collection.
        """
        collection = cls.mongoManager.getCollection(mongoModel.collectionName)
        result = collection.update_one(filter_condition, {"$set": target}, upsert=True)
        return result    



    
        
        


    
    
    