import os
from ksubscribe_share.db.dbmodelV2.predefineKeywordVO import PredefineKeywordVO
from ksubscribe_share.db.mongoManager import MongoClient, MongoManager
import mariadb
from ksubscribe_share.db.data_migration.mariadb_manager import MariaDBManager
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.service.baseQueryService import BaseQueryService

#csa_organization_master, csa_organization_detail(maria) ---> contents_org(mongo) 테이블 

class data_csa_keyword_dic():

    commonService = CommCodeService()
    contentsOrgService = ContentsOrgService()
    
    def __init__(self):
        pass
    
    def moveToMongo(self):

        # MariaDB 연결 및 리소스 관리
        with MariaDBManager().get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("select * from csa_keyword_dic_master")        
                result = cursor.fetchall()
        
            for doc in result:
                SEQ = doc[0]
                KEYWORD = doc[1]
                REG_DT = doc[2]
                EDIT_DT = doc[3]
                
                # 필드 초기화
                predefineKeywordVO = PredefineKeywordVO()
                predefineKeywordVO.keyword = KEYWORD
                predefineKeywordVO.regDt = REG_DT
                predefineKeywordVO.editDt = EDIT_DT

                # 카테고리 데이터를 처리
                with conn.cursor() as keyword_cursor:
                    keyword_cursor.execute(
                        f"SELECT * FROM csa_keyword_dic_detail WHERE seq = '{SEQ}'"
                    )
                    keyword_result = keyword_cursor.fetchall()
                    
                    # categoryList 초기화 및 데이터 추가
                    predefineKeywordVO.subkeywords = []
                    for keyword_row in keyword_result:
                        
                        SEQ_SUB = keyword_row[0]
                        RELATED_KEYWORD = keyword_row[1]
                        REG_DT_SUB = keyword_row[2]
                        EDIT_DT_SUB = keyword_row[3]
                        predefineKeywordVO.subkeywords.append(RELATED_KEYWORD)

                result = BaseQueryService.insert_one(predefineKeywordVO)
                if result.inserted_id: 
                    print(f"{predefineKeywordVO.collectionName} : {predefineKeywordVO.keyword} : insert 되었습니다.")
                else:
                    print(f"{predefineKeywordVO.collectionName} : {predefineKeywordVO.keyword} : insert 실패하였습니다")
            
