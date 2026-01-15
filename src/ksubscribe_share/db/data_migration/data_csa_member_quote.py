import os
from ksubscribe_share.db.dbmodelV2.memberQuoteVO import MemberQuoteVO
from ksubscribe_share.db.mongoManager import MongoClient, MongoManager
import mariadb
from ksubscribe_share.db.data_migration.mariadb_manager import MariaDBManager
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.baseQueryService import BaseQueryService
from datetime import datetime

#csa_member(maria) ---> member_account(mongo) 테이블 


class data_csa_member_quote():

    commonService = CommCodeService()
    
    def __init__(self):
        pass
    
    def moveToMongo(self):
        
        with MariaDBManager().get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("select * from csa_member_quote")        
            result = cursor.fetchall()        
        
        for doc in result:
            MBER_ID = doc[0]
            quotenum = doc[1]
            regstdt = doc[2]
            regeddt = doc[3]
            quotetype = doc[4]   
            
            # 필드 초기화
            memberQuoteVO = MemberQuoteVO()
            memberQuoteVO.mberId = MBER_ID
            memberQuoteVO.quotenum = quotenum
            memberQuoteVO.startDt = regstdt
            memberQuoteVO.endDt = regeddt
            memberQuoteVO.quotetype = quotetype
            
            # 문자열을 datetime 객체로 변환
            try:
                regstdt = datetime.strptime(regstdt, "%Y-%m-%d %H:%M:%S")
                regeddt = datetime.strptime(regeddt, "%Y-%m-%d %H:%M:%S")
            except ValueError as e:
                print(f"날짜 형식 변환 오류: {e}")
                regstdt = None
                regeddt = None            
            
            result = BaseQueryService.insert_one(memberQuoteVO)
            if result.inserted_id: 
                print(f"{memberQuoteVO.collectionName} : {memberQuoteVO.mberId} : insert 되었습니다.")
            else:
                print(f"{memberQuoteVO.collectionName} : {memberQuoteVO.mberId} : insert 실패하였습니다")
                        
            

