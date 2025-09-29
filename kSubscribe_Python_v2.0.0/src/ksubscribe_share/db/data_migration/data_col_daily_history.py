import os
import mariadb
from datetime import datetime

from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO, ContentsOrgCategory
from ksubscribe_share.db.dbmodelV2.contentsCollectDailyHistoryVO import ContentsCollectDailyHistoryVO
from ksubscribe_share.db.mongoManager import MongoClient, MongoManager
from ksubscribe_share.db.data_migration.mariadb_manager import MariaDBManager
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.service.baseQueryService import BaseQueryService


#col_daily_history(maria) ---> contents_collect_daily_history(mongo) 테이블 

class data_col_daily_history():

    commonService = CommCodeService()
    
    def __init__(self):
        pass
    
    def moveToMongo(self):

        with MariaDBManager().get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("select * from col_daily_history")        
            result = cursor.fetchall()     
        
        for doc in result:
            STD_YMD = doc[0]
            EXEC_YN = doc[1]
            TOT_CNT = doc[2]
            SUC_CNT = doc[3]
            FAIL_CNT = doc[4]
            COL_CNT = doc[5]
            REG_DT = doc[3]
            REG_ID = doc[4]
            EDIT_DT = doc[5]
            EDIT_ID = doc[6]
            
            std_date = datetime.strptime(STD_YMD, "%Y%m%d")
            
            # 필드 초기화
            dailyHistory = ContentsCollectDailyHistoryVO()
            dailyHistory.collectDt = std_date
            dailyHistory.totalCount =  TOT_CNT if TOT_CNT is not None else 0
            dailyHistory.successCount = SUC_CNT if SUC_CNT is not None else 0
            dailyHistory.failCount = FAIL_CNT if FAIL_CNT is not None else 0
            dailyHistory.collectCount = COL_CNT if COL_CNT is not None else 0
            dailyHistory.scrappingCount = 0 
            dailyHistory.regDt = REG_DT if REG_DT is not None else None
            dailyHistory.regId = REG_ID if REG_ID is not None else None
            dailyHistory.editDt = EDIT_DT if EDIT_DT is not None else None
            dailyHistory.editId = EDIT_ID if EDIT_ID is not None else None

            result = BaseQueryService.insert_one(dailyHistory)
            if result.inserted_id: 
                print(f"{dailyHistory.collectionName} : {dailyHistory.collectDt} : insert 되었습니다.")
            else:
                print(f"{dailyHistory.collectionName} : {dailyHistory.collectDt} : insert 실패하였습니다")
            
            
        