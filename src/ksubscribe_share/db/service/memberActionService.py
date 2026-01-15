
from bson import ObjectId
import datetime
from typing import List

import datetime

from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO, ContentsOrgCategory
from ksubscribe_share.db.dbmodelV2.memberActionVO import MemberActionVO
from ksubscribe_share.db.dbmodelV2.memberVO import MemberVO
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.dbmodelV2.dbEnums import ActionTypeEnum, SignMethodEnum
from ksubscribe_share.db.service.baseQueryService import BaseQueryService

#컨텐츠 수집 이력 
class MemberActionService():
    
    mongoManager = MongoManager()           # MongoManager 싱글톤 인스턴스를 사용
    collectionName = "member_action"
        
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MemberActionService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        pass 

    def insert_login_action(self, mberId, actionDt, successYN, signMethod, signIp):
        member_action = MemberActionVO()
        member_action.mberId = mberId
        member_action.actionDt = actionDt
        member_action.sucYN = "Y" if successYN else "N"
        member_action.actionType = ActionTypeEnum.LOGIN
        member_action.signMethod = signMethod
        member_action.signIp = signIp
        result = BaseQueryService.insert_one(member_action)
        return member_action

    def insert_logout_action(self, mberId, actionDt, successYN, signIp):
        member_action = MemberActionVO()
        member_action.mberId = mberId
        member_action.actionDt = actionDt
        member_action.sucYN = "Y" if successYN else "N"
        member_action.actionType = ActionTypeEnum.LOGOUT
        member_action.signIp = signIp
        result = BaseQueryService.insert_one(member_action)
        return member_action

    def insert_signup_action(self, mberId, actionDt):
        member_action = MemberActionVO()
        member_action.mberId = mberId
        member_action.actionDt = actionDt
        member_action.sucYN = "Y"
        member_action.actionType = ActionTypeEnum.SIGNUP
        result = BaseQueryService.insert_one(member_action)
        return member_action

    def insert_sub_org_action(self, mberId, actionDt, successYN, orgId):
        member_action = MemberActionVO()
        member_action.mberId = mberId
        member_action.actionDt = actionDt
        member_action.sucYN = "Y" if successYN else "N"
        member_action.orgId = orgId
        member_action.actionType = ActionTypeEnum.SUBORG
        result = BaseQueryService.insert_one(member_action)
        return member_action

    def insert_sub_category_action(self, mberId, actionDt, successYN, orgId, cateId):
        member_action = MemberActionVO()
        member_action.mberId = mberId
        member_action.actionDt = actionDt
        member_action.sucYN = "Y" if successYN else "N"
        member_action.orgId = orgId
        member_action.cateId = cateId
        member_action.actionType = ActionTypeEnum.SUBCATEGORY
        result = BaseQueryService.insert_one(member_action)
        return member_action

    def insert_sub_category_actions(self, mberId, actionDt, successYN, contentsOrg:ContentsOrgVO):
        try:
            for category in contentsOrg.categoryList:
                member_action = MemberActionVO()
                member_action.mberId = mberId
                member_action.actionDt = actionDt
                member_action.sucYN = "Y" if successYN else "N"
                member_action.orgId = contentsOrg.orgId
                member_action.cateId = category.cateId
                member_action.actionType = ActionTypeEnum.SUBCATEGORY
                result = BaseQueryService.insert_one(member_action)
            return True
        except Exception as e:
            return False

    def insert_sub_keyword_action(self, mberId, actionDt, successYN, keywordList: List[str]):
        try:
            for keyword in keywordList:
                member_action = MemberActionVO()
                member_action.mberId = mberId
                member_action.actionDt = actionDt
                member_action.sucYN = "Y" if successYN else "N"
                member_action.keyword = keyword
                member_action.actionType = ActionTypeEnum.SUBKEYWORD
                result = BaseQueryService.insert_one(member_action)
            return True
        except Exception as e:
            return False    