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
from ksubscribe_share.db.service.predefineKeywordRelationService import PredefineKeywordRelationService
#csa_member(maria) ---> member_account(mongo) 테이블 
#col_user_subs_master --> member_account(mongo) 테이블에 반영 

class data_predefine_relation():

    predefineKeywordRelationService = PredefineKeywordRelationService()
    
    def __init__(self):
        pass
    
    def moveToMongo(self):

        conn = MariaDBManager().get_connection()
        cursor = conn.cursor()
        cursor.execute("select * from col_user_subs_master")        
        result = cursor.fetchall()
        
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
            
            relation_keywords : List[str] = []
            predefine_keywords = self.predefineKeywordService.getKeywordList() 

            if REQ_KEYWORD1 == "ALL" or REQ_KEYWORD2 == "ALL"  or REQ_KEYWORD3 == "ALL" : 
                relation_keywords = predefine_keywords
            else: 
                if REQ_KEYWORD1 is not None and REQ_KEYWORD1.strip() != "" and REQ_KEYWORD1 in predefine_keywords:
                    relation_keywords.append(REQ_KEYWORD1)
                if REQ_KEYWORD2 is not None and REQ_KEYWORD2.strip() != "" and REQ_KEYWORD2 in predefine_keywords:
                    relation_keywords.append(REQ_KEYWORD2)
                if REQ_KEYWORD3 is not None and REQ_KEYWORD3.strip() != "" and REQ_KEYWORD2 in predefine_keywords:
                    relation_keywords.append(REQ_KEYWORD3)
            
            if relation_keywords is not None and len(relation_keywords) > 1 : 

                self.predefineKeywordRelationService.process_keyword_relations(relation_keywords, 0)
                

            
            

            
            

