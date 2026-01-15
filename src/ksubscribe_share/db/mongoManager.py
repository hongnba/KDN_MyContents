from pymongo import MongoClient
import ksubscribe_share.config as Conf


class MongoManager:
    _instance = None
    #
    connectString = f"mongodb://{Conf.MONGO_IP}:{Conf.MONGO_PORT}/?directConnection=true&serverSelectionTimeoutMS=300000&socketTimeoutMS=300000"#/replicaSet=rs0"
    databaseName = Conf.MONGO_DB_NAME

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MongoManager, cls).__new__(cls, *args, **kwargs)
            cls.client = MongoClient(cls.connectString, tz_aware=True)
            # cls.getDataBase()
            cls.dataBase = cls.client[cls.databaseName]
        return cls._instance

    def __init__(self):
        # 생성자 메서드, 객체의 초기 상태를 정의합니다.
        pass

    def getDataBase(self):
        self.dataBase = self.client[self.databaseName]

    def getCollection(self, name: str):
        return self.dataBase[name]
