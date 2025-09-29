import os
import mariadb
from datetime import datetime

from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO, ContentsOrgCategory
from ksubscribe_share.db.dbmodelV2.contentsCollectErrorVO import ContentsCollectErrorVO
from ksubscribe_share.db.mongoManager import MongoClient, MongoManager
from ksubscribe_share.db.data_migration.mariadb_manager import MariaDBManager
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.service.baseQueryService import BaseQueryService


#col_daily_error(maria) ---> contents_collect_error(mongo) 테이블 

class data_col_daily_error():

    commonService = CommCodeService()
    
    def __init__(self):
        pass
    
    def moveToMongo(self):

        with MariaDBManager().get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("select * from col_daily_error")        
            result = cursor.fetchall()   
        
        for doc in result:
            STD_YMD = doc[0]
            ORG_ID = doc[1]
            CATE_ID = doc[2]
            REG_DT = doc[3]
            REG_ID = doc[4]
            EDIT_DT = doc[5]
            EDIT_ID = doc[6]
            
            std_date = datetime.strptime(STD_YMD, "%Y%m%d")
            # 필드 초기화
            ContentsCollectError = ContentsCollectErrorVO()
            ContentsCollectError.collectDt = std_date
            ContentsCollectError.orgId =  ORG_ID if ORG_ID is not None else None
            ContentsCollectError.cateId = CATE_ID if CATE_ID is not None else None
            ContentsCollectError.regDt = REG_DT if REG_DT is not None else None
            ContentsCollectError.regId = REG_ID if REG_ID is not None else None
            ContentsCollectError.editDt = EDIT_DT if EDIT_DT is not None else None
            ContentsCollectError.editId = EDIT_ID if EDIT_ID is not None else None
            
            result = BaseQueryService.insert_one(ContentsCollectError)
            if result.inserted_id: 
                print(f"{ContentsCollectError.collectionName} : {ContentsCollectError.orgId} {ContentsCollectError.cateId} : insert 되었습니다.")
            else:
                print(f"{ContentsCollectError.collectionName} : {ContentsCollectError.orgId} {ContentsCollectError.cateId} : insert 실패하였습니다")
                      
        