from bson import ObjectId
from pymongo import MongoClient
from datetime import datetime, timezone
from typing import List

from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.errorInfo import ErrorInfo
from typing import TypeVar, Type, Dict
T = TypeVar("T", bound="BaseModel")  # BaseModel에 바인딩된 타입 변수


# 컨텐츠 전송 이력
class ContentsSendHistoryVO(BaseMongoDocument):

    collectionName = "contents_send_history"

    def __init__(
        self, 
        mberId: str = None,
        sendDt: datetime = None,
        telegramSendDt: datetime = None,        
        kakaoSendDt: datetime = None,        
        emailSendDt: datetime = None,
        telegramSendYN: str = None,
        kakaoSendYN: str = None,
        emailSendYN: str = None,
        telegramSendSuccessYN: str = None,
        kakaoSendSuccessYN: str = None,
        emailSendSuccessYN: str = None,
        telegramSendResponse: dict[str, str] = None,
        kakaoSendResponse: dict[str, str] = None,
        emailSendResponse: dict[str, str] = None,
        kakaoSendIds: List[str] = None,  
        telegramSendIds: List[str] = None,  
        emailSendIds: List[str] = None,
        mergedSendIds: List[str] = None, 
        keywords : List[str] = None,
        regDt: datetime = None,       
        _id: ObjectId = None
    ):

        super().__init__(_id)  # BaseDocument의 생성자를 호출
        self.mberId = mberId
        self.sendDt = sendDt
        self.telegramSendDt = telegramSendDt
        self.kakaoSendDt = kakaoSendDt
        self.emailSendDt = emailSendDt
        self.telegramSendYN = telegramSendYN,
        self.kakaoSendYN = kakaoSendYN,
        self.emailSendYN = emailSendYN,
        self.telegramSendSuccessYN = telegramSendSuccessYN,
        self.kakaoSendSuccessYN = kakaoSendSuccessYN,
        self.emailSendSuccessYN = emailSendSuccessYN,
        self.telegramSendResponse = telegramSendResponse if telegramSendResponse is not None else {},
        self.kakaoSendResponse = kakaoSendResponse if kakaoSendResponse is not None else {},
        self.emailSendResponse = emailSendResponse if emailSendResponse is not None else {},
        self.kakaoSendIds = kakaoSendIds if kakaoSendIds is not None else []
        self.telegramSendIds = telegramSendIds if telegramSendIds is not None else []
        self.emailSendIds = emailSendIds if emailSendIds is not None else []
        self.mergedSendIds = mergedSendIds if mergedSendIds is not None else []
        self.keywords = keywords if keywords is not None else []
        self.regDt = regDt
        
    def to_mongo(self):
        """클래스를 MongoDB 문서 형식으로 변환"""
        # 상위 클래스의 to_mongo 호출
        mongo_data = super().to_mongo()

        if self.kakaoSendIds:
            mongo_data["kakaoSendIds"] = [item for item in self.kakaoSendIds]
        else:
            mongo_data["kakaoSendIds"] = []
            
        if self.telegramSendIds:
            mongo_data["telegramSendIds"] = [item for item in self.telegramSendIds]
        else:
            mongo_data["telegramSendIds"] = []
            
        if self.emailSendIds:
            mongo_data["emailSendIds"] = [item for item in self.emailSendIds]
        else:
            mongo_data["emailSendIds"] = []
            
        if self.mergedSendIds:
            mongo_data["mergedSendIds"] = [item for item in self.mergedSendIds]
        else:
            mongo_data["mergedSendIds"] = []

        # if self.kakaoSendResponse:
        #     mongo_data["kakaoSendResponse"] = {key: value for key, value in self.kakaoSendResponse.items()}
        # else:
        #     mongo_data["kakaoSendResponse"] = {}
            
        # if self.emailSendResponse:
        #     mongo_data["emailSendResponse"] = {key: value for key, value in self.emailSendResponse.items()}
        # else:
        #     mongo_data["emailSendResponse"] = {}
            
        # if self.telegramSendResponse:
        #     mongo_data["telegramSendResponse"] = {key: value for key, value in self.telegramSendResponse.items()}
        # else:
        #     mongo_data["telegramSendResponse"] = {}

        return mongo_data
    
    @classmethod
    def from_mongo(cls: Type[T], mongo_data) -> T:
        """
        MongoDB 문서 데이터를 Python 객체로 변환
        """
        try:
            # 상위 클래스의 from_mongo 호출
            instance = super().from_mongo(mongo_data)

            instance.kakaoSendIds = mongo_data.get("kakaoSendIds", [])
            instance.telegramSendIds = mongo_data.get("telegramSendIds", [])
            instance.emailSendIds = mongo_data.get("emailSendIds", [])
            instance.mergedSendIds = mongo_data.get("mergedSendIds", {})
            instance.kakaoSendResponse = mongo_data.get("kakaoSendResponse", {})
            instance.emailSendResponse = mongo_data.get("emailSendResponse", {})
            instance.telegramSendResponse = mongo_data.get("telegramSendResponse", {})
            return instance
        except Exception as ex:
            return None
            
        

    def to_update_query(self):
        """
        ContentsSendHistoryVO 속성 중 None이 아닌 값으로 MongoDB 업데이트 쿼리 생성.
        """
        set_query = {k: v for k, v in self.__dict__.items() if v not in [None, [], {}] and k != "keywords"} # keyword 는 제외, addToSet 으로 해야하기 때문
        set_on_insert_query = {"regDt": datetime.now(timezone.utc)} if "regDt" not in set_query else {}
        add_to_set_query = {"keywords": {"$each": self.keywords}} if self.keywords else {}
        
        update_query = {"$set": set_query, "$setOnInsert": set_on_insert_query}
        if add_to_set_query:
            update_query["$addToSet"] = add_to_set_query  # 중복 제거 후 배열 업데이트
            
        return update_query