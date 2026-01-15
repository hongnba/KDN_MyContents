import os
from ksubscribe_share.db.dbmodelV2.predefineKeywordVO import PredefineKeywordVO
from ksubscribe_share.db.mongoManager import MongoClient, MongoManager
import mariadb
from ksubscribe_share.db.data_migration.mariadb_manager import MariaDBManager
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.memberService import MemberService
from ksubscribe_share.db.service.predefineKeywordService import PredefineKeywordService
from ksubscribe_share.db.service.baseQueryService import BaseQueryService


class data_csa_user_keyword_subs():
    """
    csa_user_keyword_subs_master 테이블을 처리하는 클래스 
    MBER_ID, PRDEF_REQ_KEYWORD
    - member_account.keywordSubscribe 에 PRDEF_REQ_KEYWORD 추가 
    - predefine_keyword.subscribeIds에 MBER_ID 추가 
    """
    commonService = CommCodeService()
    memberService = MemberService()
    predefineKeywordService = PredefineKeywordService()
    
    def __init__(self):
        pass
    
    def moveToMongo(self):

        # MariaDB 연결 및 리소스 관리
        with MariaDBManager().get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("select * from csa_user_keyword_subs_master where use_YN='Y'")        
                result = cursor.fetchall()
        
            for doc in result:
                SEQ = doc[0]
                MBER_ID = doc[1]
                PRDEF_REQ_KEYWORD = doc[2]
                INPUT_REQ_KEYWORD = doc[3]
                USE_YN = doc[3]
                REG_DT = doc[3]
                
                if PRDEF_REQ_KEYWORD is not None and MBER_ID is not None: 
                    keyword = self.keyword_dic[str(PRDEF_REQ_KEYWORD)]
                    self.memberService.subscribeKeyword(MBER_ID, keyword)
                    self.predefineKeywordService.addSubscribe(MBER_ID, keyword)
                
     
    keyword_dic = {
        "1" : "데이터",
        "2" : "AI",
        "3" : "플랫폼",
        "4" : "디지털",
        "5" : "반도체",
        "6" : "에너지",
        "7" : "정보보호",
        "8" : "전력",
    }                
