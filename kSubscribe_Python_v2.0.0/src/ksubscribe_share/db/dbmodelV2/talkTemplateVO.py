from bson import ObjectId
from typing import List
from datetime import datetime
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.mongoManager import MongoClient, MongoManager
from typing import TypeVar, Type, Dict
T = TypeVar("T", bound="BaseModel")  # BaseModel에 바인딩된 타입 변수


class TalkTemplateVO(BaseMongoDocument):
    
    collectionName = "talk_template"
    
    def __init__(
        self,
        templateCode: str = None,
        templateName: str = None,
        template: str = None,
        regDt: datetime = None,
        regId: str = None,
        editDt: datetime = None,
        editId: str = None,
        _id: ObjectId = None,
    ):

        super().__init__(_id)  # BaseDocument의 생성자를 호출

        # 필드 초기화
        self.templateCode = templateCode
        self.templateName = templateName
        self.template = template
        self.regDt = regDt
        self.regId = regId
        self.editDt = editDt
        self.editId = editId

    # def to_mongo(self):
    #     """클래스를 MongoDB 문서 형식으로 변환"""
    #     return {
    #         # "_id": self._id,
    #         "authortemplateCodeity": self.templateCode,
    #         "templateName": self.templateName,
    #         "template": self.template,
    #         "regDt": self.regDt,
    #         "regId": self.regId,
    #         "editDt": self.editDt,
    #         "editId": self.editId,
    #     }



# 현재 파일이 직접 실행될 때만 아래 코드 실행
# import 되어 사용할 때는 실행되지 않음.
if __name__ == "__main__":
    
    coll = MongoManager().getCollection("talk_template")
    
    template = TalkTemplateVO()
    template.templateCode = "WK_2023082213"
    template.templateName = "3570-03"
    template.template = "#{1}에서 안내드립니다. #{2} #{3}"
    template.regDt = datetime.now()
    template.regId = "kdn"
    
    template.insert_one()
    
    