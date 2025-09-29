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


class data_migration_main():

    data_cmmn_code = data_cmmn_code()
    data_col_col_contents = data_col_col_contents()
    data_col_daily_error = data_col_daily_error() 
    data_col_daily_history = data_col_daily_history() 
    data_col_user_subs_master = data_col_user_subs_master()
    data_content_image = data_content_image()
    data_csa_cntn_status = data_csa_cntn_status()
    data_csa_keyword_dic = data_csa_keyword_dic()
    data_csa_authorinfo = data_csa_authorinfo()
    data_csa_catalog_master = data_csa_catalog_master()
    data_csa_member_quote = data_csa_member_quote() 
    data_csa_member = data_csa_member() 
    data_csa_organization = data_csa_organization() 
    data_csa_send_history = data_csa_send_history()
    data_csa_user_keyword_subs = data_csa_user_keyword_subs()
    data_predefine_relation = data_predefine_relation()
    data_validator = data_validator()
    memberService = MemberService()
    contentsOrgService = ContentsOrgService() 
    contentsService = ContentsService() 
    commCodeService = CommCodeService() 
    mongoManager = MongoManager()
    
    def __init__(self):
        pass
    
    def updateReceiveYNToMongo(self):
        self.data_csa_member.receiveYNToMongo()        
        pass
    
    def checkNotExistUserInMongo(self):
        self.data_csa_member.checkNotExistUserInMongo() 
        pass
    
    def remove_contents_KST250229(self):
        self.contentsService.remove_contents_KST250229()
        pass
        
    def moveToMongo(self):
        
        #무엇을 지울지 판단할 것 
        #self.deleteCollectionData(CommCodeVO.collectionName)  
        #self.deleteCollectionData(ContentsCollectErrorVO.collectionName)    
        
        #3waysoft에서 만든 것 
        #self.data_content_image.moveToMongo()
        
        #데이터 넣는 부분      
        #self.data_cmmn_code.moveToMongo()   #OK
        #self.data_csa_member.moveToMongo()   #OK          
        #self.data_csa_organization.moveToMongo()   #OK
        #self.data_csa_organization.get_collect_method()        #OK
        #self.data_csa_organization.get_image_width_height()    #OK
               
        #데이터 없어서 테스트 못해봄        
        #self.data_csa_keyword_dic.moveToMongo()  
        
        #self.data_csa_catalog_master.moveToMongo()    #OK
        
        #데이터 없어서 테스트 못해봄        
        #member.contentsOrgSubscribe에 사용자가 가입한 orgId, CateId 추가 
        #contentsOrg.subscriberIds 에 사용자 정보 추가 
        #self.data_col_user_subs_master.moveToMongo()    
        
        #데이터 없어서 테스트 못해봄        
        #member.keywordSubscribe 사용자가 가입한 키워드 추가 
        #predefine.subscribeIds : 키워드에 가입한 사용자 계정 추가 
        #self.data_csa_user_keyword_subs.moveToMongo() 
        
        #데이터 없어서 테스트 못해봄        
        #self.data_col_daily_error.moveToMongo()          
        
        #데이터 없어서 테스트 못해봄        
        #self.data_col_daily_history.moveToMongo()    
        
        #self.data_csa_cntn_status.moveToMongo()
        #self.data_csa_authorinfo.moveToMongo()      
        #self.data_csa_member_quote.moveToMongo()     

        #이때 contentsVO, contentsCollectHistoryVO에 데이터가 들어감 
        #self.data_col_col_contents.moveToMongo()        
        
        #여기서 부터 다시 실행해야 함. 운영DB ----------------------------------------------------------------------------------------------
        #self.data_csa_send_history.moveToMongo()        
        #self.data_predefine_relation.moveToMongo()
        
        #catename이 없는 오류 수정 
        #self.data_csa_organization.set_catename()
        
        #keywordSubscribe에 Array로 들어가 있는 것을 List[str]로 수정 
        #self.memberService.collectKeywordSubscribe()
        
        #contents에 orgName, cateName이 null인 문제 수정하는 코드
        #self.contentsService.fill_orgname_catename()
        
        #기존 회원 정보를 어떻게 처리할 것인가? 문제 
        #self.memberService.getOrgNameDistinct()
        
        #contents_org subscribIds 계정 중복 제거할 것
        #self.contentsOrgService.remove_duplicate_subscriberId()
        
        #member_account에 contentsOrgSubscribe 잘못들어가는 문제 수정 
        #self.memberService.deduplicate_and_update()
        
        #중복 카테고리 ID 수정하기 
        #self.commCodeService.remove_category_main()
        
        #수집방법 코드 넣기 
        #onlyPDF, textInTag, textInBody 
        
        #공지사항 첨부파일 옮기기  /data/kcaas/
        #수동으로 처리할 것 
        
        #member을 기관, 개인으로 강제로 초기화 : KDN 의견에 따라 .
        #self.memberService.convert_mbertype()
        
        #sentiment 가 str으로 들어간 경우 처리 
        self.data_validator.sentiment_str_to_float()
        #self.data_validator.convert_predKeywords_to_double()
        
        #기관의 별명이 들어가도록 처리 
        #self.data_csa_organization.updateOrgNameSynonym() 
        #기사의 사전정의 키워드를 nlp를 이용하여 할당한다.         
        #요약, 사전정의 키워드 ~~~ 등을 ollama를 이용하여 할당한다. 
          
                
if __name__ == "__main__":

    mainClasss = data_migration_main()
    #사용자 구독 정보 수정 
    mainClasss.updateReceiveYNToMongo()
    #mariadb에는 있는데 mongodb에는 없는 사용자 구독 정보 수정 
    mainClasss.checkNotExistUserInMongo()
    #3월 이전 데이터 삭제코드 
    #mainClasss.remove_contents_KST250229()
    
    
    
    
    