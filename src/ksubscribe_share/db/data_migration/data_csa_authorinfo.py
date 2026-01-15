import os
import mariadb

from ksubscribe_share.db.dbmodelV2.authorInfoVO import AuthorInfoVO
from ksubscribe_share.db.dbmodelV2.contentsCollectErrorVO import ContentsCollectErrorVO
from ksubscribe_share.db.mongoManager import MongoClient, MongoManager
from ksubscribe_share.db.data_migration.mariadb_manager import MariaDBManager
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.service.baseQueryService import BaseQueryService


#col_daily_error(maria) ---> contents_collect_error(mongo) 테이블 

class data_csa_authorinfo():

    commonService = CommCodeService()
    
    def __init__(self):
        pass
    
    def moveToMongo(self):

        with MariaDBManager().get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("select * from csa_authorinfo")        
            result = cursor.fetchall()   
        
        for doc in result:
            author_code = doc[0]
            author_nm = doc[1]
            author_dc = doc[2]
            author_creat_de = doc[3]
            
            # 필드 초기화
            authorInfoVO = AuthorInfoVO()
            authorInfoVO.authorCode = author_code
            authorInfoVO.authorName =  author_nm
            authorInfoVO.authorDesc = author_dc
            authorInfoVO.authorCreate = author_creat_de
            
            result = BaseQueryService.insert_one(authorInfoVO)
            if result.inserted_id: 
                print(f"{authorInfoVO.collectionName} : {authorInfoVO.authorCode}  : insert 되었습니다.")
            else:
                print(f"{authorInfoVO.collectionName} : {authorInfoVO.authorCode} : insert 실패하였습니다")
                      
        