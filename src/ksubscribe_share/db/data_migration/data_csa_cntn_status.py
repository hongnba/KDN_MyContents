import os
import mariadb
from datetime import datetime

from ksubscribe_share.db.dbmodelV2.memberPVActionVO import MemberPVActionVO
from ksubscribe_share.db.mongoManager import MongoClient, MongoManager
from ksubscribe_share.db.data_migration.mariadb_manager import MariaDBManager
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.baseQueryService import BaseQueryService


#col_daily_error(maria) ---> contents_collect_error(mongo) 테이블 

class data_csa_cntn_status():

    commonService = CommCodeService()
    
    def __init__(self):
        pass
    
    def moveToMongo(self):

        with MariaDBManager().get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("select * from csa_cntn_status")        
            result = cursor.fetchall()   
        
        for doc in result:
            APLYID = doc[0]
            MBER_ID = doc[1]
            ORG_NM = doc[2]
            MBER_NM = doc[3]
            IPADDR = doc[4]
            CNTN_DT = doc[5]
            URL = doc[6]
            
            # 필드 초기화
            authorInfoVO = MemberPVActionVO()
            authorInfoVO.mberId =  MBER_ID
            authorInfoVO.actionType =  "PAGEVIEW"
            authorInfoVO.clientIp = IPADDR
            authorInfoVO.pageUrl = URL
            connection_date = datetime.strptime(CNTN_DT, "%Y-%m-%d %H:%M:%S")
            authorInfoVO.actionDt = connection_date
            
            # Python의 int로 변환
            if APLYID is not None:
                v1AplyId = int(APLYID)  # DECIMAL -> int 변환                
            authorInfoVO.v1AplyId = v1AplyId
            authorInfoVO.orgName = ORG_NM
            authorInfoVO.mberName = MBER_NM
            
            result = BaseQueryService.insert_one(authorInfoVO)
            if result.inserted_id: 
                print(f"{authorInfoVO.collectionName} : {authorInfoVO.mberId}  : insert 되었습니다.")
            else:
                print(f"{authorInfoVO.collectionName} : {authorInfoVO.mberId} : insert 실패하였습니다")
                      
        