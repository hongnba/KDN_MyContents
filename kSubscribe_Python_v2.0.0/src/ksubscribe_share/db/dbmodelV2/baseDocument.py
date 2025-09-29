from bson import ObjectId
from bson import ObjectId
from typing import Type, TypeVar

from ksubscribe_share.db.dbmodel.newsMeta import NewsMeta
from ksubscribe_share.db.mongoManager import MongoManager
from pymongo import MongoClient

T = TypeVar("T", bound="BaseModel")

class BaseModel:

    def _initialize_fields(self, fields: dict):
        """동적으로 필드를 초기화"""
        for key, value in fields.items():
            #if key != "self" and not key.startswith("_"):  # self와 _로 시작하는 내부 변수 제외
            setattr(self, key, value)                
                
    @classmethod
    def from_mongo(cls: Type[T], document: dict) -> T:
        """MongoDB 문서를 클래스로 변환"""
        instance = cls.__new__(cls)  # __init__ 호출 없이 객체 생성
        for key, value in document.items():
            #if hasattr(instance, key):  # 클래스에 정의된 속성만 설정
            setattr(instance, key, value)
        return instance

    def to_mongo(self) -> dict:
        """클래스를 MongoDB 문서 형식으로 변환"""
        # MongoDB 문서 형식으로 변환된 데이터를 변수에 저장
        mongo_data = {
            key: value
            for key, value in vars(self).items()
            if key == "_id" or not key.startswith("_")  # 내부 변수를 제외
        }
        # 디버깅을 위해 데이터 출력 (필요시 제거)
        #print("MongoDB Document:", mongo_data)
        return mongo_data

    def __repr__(self):
        """객체의 멤버 변수를 문자열로 출력"""
        class_name = self.__class__.__name__
        attributes = ", ".join(f"{key}={value}" for key, value in vars(self).items())
        return f"{class_name}({attributes})"    
    
    
class BaseMongoDocument(BaseModel):

    mongoManager = MongoManager()  # MongoManager 싱글톤 인스턴스를 사용
    collectionName = ""  # 자식 클래스에서 이 값을 설정해야 함

    def __init__(self, _id: str = None):
        # _id가 None이거나 문자열일 때 처리
        if _id:
            self._id = ObjectId(_id) if isinstance(_id, str) else _id
        else:
            self._id = ObjectId()  # _id가 없으면 None으로 설정

    
    def insert_one(self):
        collection = self.mongoManager.getCollection(self.collectionName)
        result = collection.insert_one(self.to_mongo())
        self._id = result.inserted_id  # 삽입된 문서의 _id를 설정

    def find_one(self):
        collection = self.mongoManager.getCollection(self.collectionName)
        document = collection.find_one({"_id": self._id})
        self.from_mongo(document)

    def update_one(self):
        collection = self.mongoManager.getCollection(self.collectionName)
        collection.update_one({"_id": self._id}, {"$set": self.to_mongo()})

    def delete_one(self):
        collection = self.mongoManager.getCollection(self.collectionName)
        collection.delete_one({"_id": self._id})

    @classmethod
    def find_one_id(cls, _id: str):
        collection = cls.mongoManager.getCollection(cls.collectionName)
        document = collection.find_one({"_id": ObjectId(_id)})
        return cls.from_mongo(document) if document else None

    @classmethod
    def find_one(cls, query: dict):
        collection = cls.mongoManager.getCollection(cls.collectionName)
        document = collection.find_one(query)
        return cls.from_mongo(document) if document else None

    @classmethod
    def find_many(cls, query: dict, skip: int = 0, limit: int = 1000):
        collection = cls.mongoManager.getCollection(cls.collectionName)
        cursor = collection.find(query).skip(skip).limit(limit)

        # list_result = [cls.from_mongo(doc) for doc in cursor]
        list_result = []
        for doc in cursor:
            list_result.append(cls.from_mongo(doc))

        return list_result

    @classmethod
    def find_all(cls):
        collection = cls.mongoManager.getCollection(cls.collectionName)
        cursor = collection.find()
        list_result = [cls.from_mongo(doc) for doc in cursor]
        return list_result

    @classmethod
    def update(cls, where: dict, target: dict):
        collection = cls.mongoManager.getCollection(cls.collectionName)
        collection.update_many(where, {"$set": target})

    @classmethod
    def update_count(cls, where: dict, target: dict):
        collection = cls.mongoManager.getCollection(cls.collectionName)
        collection.update_one(where, {"$inc": target})

    @classmethod
    def update_count_byid(cls, _id: str, target: dict):
        collection = cls.mongoManager.getCollection(cls.collectionName)
        collection.update_one({"_id": ObjectId(_id)}, {"$inc": target})

    @classmethod
    def insert(cls, target: dict):
        collection = cls.mongoManager.getCollection(cls.collectionName)
        collection.insert_one(target)
