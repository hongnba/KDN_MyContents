import os
from typing import List
from bson import ObjectId  # ObjectId를 사용하려면 추가로 임포트 필요
import mariadb

from ksubscribe_share.db.dbmodelV2.commCodeVO import CommCodeVO
from ksubscribe_share.db.dbmodelV2.contentsCollectErrorVO import ContentsCollectErrorVO

from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO
from ksubscribe_share.db.mongoManager import MongoClient, MongoManager
from ksubscribe_share.db.data_migration.mariadb_manager import MariaDBManager
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.service.baseQueryService import BaseQueryService
from ksubscribe_share.db.service.memberService import MemberService
from ksubscribe_share.db.service.contentsService import ContentsService
from ksubscribe_share.db.service.contentsCollectRequestService import ContentsCollectRequestService
from ksubscribe_share.db.service.predefineKeywordService import PredefineKeywordService

from ksubscribe_share.db.data_migration.data_cmmn_code import data_cmmn_code
from ksubscribe_share.db.data_migration.data_col_col_contents import data_col_col_contents
from ksubscribe_share.db.data_migration.data_col_daily_error import data_col_daily_error
from ksubscribe_share.db.data_migration.data_col_daily_history import data_col_daily_history
from ksubscribe_share.db.data_migration.data_col_user_subs_master import data_col_user_subs_master
from ksubscribe_share.db.data_migration.data_content_image import data_content_image
from ksubscribe_share.db.data_migration.data_csa_authorinfo import data_csa_authorinfo
from ksubscribe_share.db.data_migration.data_csa_catalog_master import data_csa_catalog_master
from ksubscribe_share.db.data_migration.data_csa_cntn_status import data_csa_cntn_status
from ksubscribe_share.db.data_migration.data_csa_keyword_dic import data_csa_keyword_dic
from ksubscribe_share.db.data_migration.data_csa_member_quote import data_csa_member_quote
from ksubscribe_share.db.data_migration.data_csa_member import data_csa_member
from ksubscribe_share.db.data_migration.data_csa_organization import data_csa_organization
from ksubscribe_share.db.data_migration.data_csa_send_history import data_csa_send_history
from ksubscribe_share.db.data_migration.data_csa_user_keyword_subs import data_csa_user_keyword_subs
from ksubscribe_share.db.data_migration.data_predefine_relation import data_predefine_relation
from ksubscribe_server.analysis.analysis_ollama import AnalysisOllama
from ksubscribe_share.db.data_migration.data_validator import data_validator


class data_delete_keyword():

    mongoManager = MongoManager()
    predefineKeywordService = PredefineKeywordService() 
    contentsService = ContentsService() 
    memberService = MemberService()
    contentsOrgService = ContentsOrgService() 
    contentsCollectRequestService = ContentsCollectRequestService()
    
    def __init__(self):
        pass
    
    
    def deleteKeyword(self, keyword:str):
        # 사전 정의 키워드 
        self.predefineKeywordService.remove_keyword(keyword)
        # member_account 
        #self.memberService.remove_keyword(keyword)
        pass 
      
                
if __name__ == "__main__":

    mainClasss = data_delete_keyword()
    mainClasss.deleteKeyword("한국전력")
    
    
    
    
         
    