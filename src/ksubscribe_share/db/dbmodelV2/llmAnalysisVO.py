from bson import ObjectId
from typing import List
from datetime import datetime
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.mongoManager import MongoClient, MongoManager
from typing import TypeVar, Type, Dict
T = TypeVar("T", bound="BaseModel")  # BaseModel에 바인딩된 타입 변수


class LLMAnalysisVO(BaseModel):
    
    def __init__(
        self,
        contents_id :str = None,
        analyze_type : str = None, #현재는 AllInOne, 향후, 요약/키워드분석/평판분석이 달라질 수 있음. 
        response_metadata_model: str = None,
        response_metadata_createdDt: datetime = None,
        response_metadata_done: bool = None,
        response_metadata_doneReason: str = None,
        response_metadata_totalDuration: int = None,
        response_metadata_loadDuration :int = None,
        response_metadata_promptEvalCount: int = None,
        response_metadata_promptEvalDuration: int = None,
        response_metadata_evalCount: int = None,
        response_metadata_evalDuration: int = None,        
        usage_metadata_inputToken : int = None,
        usage_metadata_outputToken : int = None,
        usage_metadata_totalToken: int = None,
        regDt:datetime = None,
    ):
    
        self.contents_id = contents_id
        self.analyze_type = analyze_type
        self.response_metadata_model = response_metadata_model
        self.response_metadata_createdDt = response_metadata_createdDt
        self.response_metadata_done = response_metadata_done
        self.response_metadata_doneReason = response_metadata_doneReason
        self.response_metadata_totalDuration = response_metadata_totalDuration
        self.response_metadata_loadDuration = response_metadata_loadDuration
        self.response_metadata_promptEvalCount = response_metadata_promptEvalCount
        self.response_metadata_promptEvalDuration = response_metadata_promptEvalDuration
        self.response_metadata_evalCount = response_metadata_evalCount
        self.response_metadata_evalDuration = response_metadata_evalDuration
        self.usage_metadata_inputToken = usage_metadata_inputToken
        self.usage_metadata_outputToken = usage_metadata_outputToken
        self.usage_metadata_totalToken = usage_metadata_totalToken
        self.regDt = regDt


    