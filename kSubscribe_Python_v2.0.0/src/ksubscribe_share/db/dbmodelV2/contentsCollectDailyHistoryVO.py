
from bson import ObjectId
import datetime
from typing import List
import datetime
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from typing import TypeVar, Type, Dict
T = TypeVar("T", bound="BaseModel")  # BaseModel에 바인딩된 타입 변수

#컨텐츠 수집 이력 
class ContentsCollectDailyHistoryVO(BaseMongoDocument):
    
    collectionName = 'contents_collect_daily_history'    

    def __init__(self, 
                 collectDt: datetime.datetime = None,                                                     
                 totalCount: int =None, 
                 successCount: int = None,
                 failCount: int = None,
                 collectCount: int = None,
                 scrappingCount:int = None,
                 regDt: datetime=None,         #
                 regId: str =None,             #
                 editDt: datetime=None,        #
                 editId: str =None,            #                 
                 _id: ObjectId = None):         
        

        super().__init__(_id)  # BaseDocument의 생성자를 호출
        # 필드 초기화
        self.collectDt = collectDt
        self.totalCount = totalCount
        self.successCount = successCount
        self.failCount = failCount
        self.collectCount = collectCount
        self.scrappingCount = scrappingCount
        self.regDt = regDt
        self.regId = regId
        self.editDt = editDt
        self.editId = editId        
        
        

   
            
    
    