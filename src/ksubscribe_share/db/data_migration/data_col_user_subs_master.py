import os
import mariadb
from typing import List
from ksubscribe_share.db.dbmodelV2.memberVO import MemberVO
from ksubscribe_share.db.dbmodelV2.predefineKeywordVO import PredefineKeywordVO
from ksubscribe_share.db.mongoManager import MongoClient, MongoManager
from ksubscribe_share.db.data_migration.mariadb_manager import MariaDBManager
from ksubscribe_share.db.dbmodelV2.dbEnums import SignMethodEnum
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.memberService import MemberService
from ksubscribe_share.db.service.predefineKeywordService import PredefineKeywordService
from ksubscribe_share.db.service.memberActionService import MemberActionService
from ksubscribe_share.db.service.baseQueryService import BaseQueryService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
#csa_member(maria) ---> member_account(mongo) 테이블 
#col_user_subs_master --> member_account(mongo) 테이블에 반영 

class data_col_user_subs_master():

    commonService = CommCodeService()
    memberService = MemberService()
    predefineKeywordService = PredefineKeywordService()
    memberActionService = MemberActionService()
    contentsOrgService = ContentsOrgService()
    
    def __init__(self):
        pass
    
    def moveToMongo(self):

        conn = MariaDBManager().get_connection()
        cursor = conn.cursor()
        cursor.execute("select * from col_user_subs_master")        
        result = cursor.fetchall()
        cursor.close()
        
        for doc in result:
            MBER_ID = doc[0]
            CATG_ID = doc[1]
            ORG_ID = doc[2]
            CATE_ID = doc[3]
            REQ_KEYWORD1 = doc[4]
            REQ_KEYWORD2 = doc[6]
            REQ_KEYWORD3 = doc[8]
            REG_DT = doc[12]
            REG_ID = doc[13]
            EDIT_DT = doc[14]
            EDIT_ID = doc[15]
            
            keywords : List[str] = []
            
            if REQ_KEYWORD1 == "ALL" or REQ_KEYWORD2 == "ALL"  or REQ_KEYWORD3 == "ALL" : 
                keywords = self.predefineKeywordService.getKeywordList() 
            else: 
                if REQ_KEYWORD1 is not None and REQ_KEYWORD1.strip() != "":
                    keywords.append(REQ_KEYWORD1)
                if REQ_KEYWORD2 is not None and REQ_KEYWORD2.strip() != "":
                    keywords.append(REQ_KEYWORD2)
                if REQ_KEYWORD3 is not None and REQ_KEYWORD3.strip() != "":
                    keywords.append(REQ_KEYWORD3)
            
            if keywords is not None and keywords and len(keywords) > 0 : 
                #member collection에 넣어야 하고 
                self.memberService.subscribeKeywordList(MBER_ID, keywords)
                #predefinekeyword collection에도 가입자 정보를 넣아야 함 

            orgName = self.commonService.get_orgName_by_orgId(ORG_ID)
            cateName = self.commonService.get_cateName_by_cateId(CATE_ID) 
            #사용자의 카테고리 가입 정보 추가            
            self.memberService.subscribeCateId(MBER_ID, ORG_ID, orgName, CATE_ID, cateName)
            #기관의 가입자 정보 추가 
            self.contentsOrgService.add_subscriber_to_org(ORG_ID, MBER_ID)
            #기관의 카테고리 가입자 정보 추가 
            self.contentsOrgService.add_subscriber_to_orgcate(ORG_ID, CATE_ID, MBER_ID)
                        
            self.memberActionService.insert_sub_keyword_action(MBER_ID, REG_DT, "Y", keywords)
            self.memberActionService.insert_sub_category_action(MBER_ID, REG_DT, "Y", ORG_ID, CATE_ID)
            
            

            
            

