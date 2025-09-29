import os
from datetime import datetime
import mariadb

from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO, ContentsOrgCategory
from ksubscribe_share.db.mongoManager import MongoClient, MongoManager
from ksubscribe_share.db.data_migration.mariadb_manager import MariaDBManager
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.service.baseQueryService import BaseQueryService
from ksubscribe_share.db.service.contentsCollectHistoryService import ContentsCollectHistoryService
from ksubscribe_share.db.service.contentsImageService import ContentsImageService


#csa_organization_master, csa_organization_detail(maria) ---> contents_org(mongo) 테이블 

class data_col_col_contents():

    commonService = CommCodeService()
    contentsOrgService = ContentsOrgService()
    contentsCollectHistoryService = ContentsCollectHistoryService()
    contentsImageService = ContentsImageService()
    
    def __init__(self):
        pass
    
    def moveToMongo(self):

        # MariaDB 연결 및 리소스 관리
        with MariaDBManager().get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("select * from col_col_contents")        
                result = cursor.fetchall()
        
            for doc in result:
                SEQ = doc[0]
                ORG_ID = doc[1]
                CATE_ID = doc[2]
                TITLE = doc[3]
                URL = doc[4]
                SHORT_URL = doc[5]
                SEND_YN = doc[6]
                COL_DT = doc[7]
                REG_DT = doc[8]
                REG_ID = doc[9]
                EDIT_DT = doc[10]
                EDIT_ID = doc[11]
                
                collectYMD = ""
                # yyyyMMdd 형식으로 변환
                collectYMD = COL_DT.strftime("%Y%m%d")
                self.contentsCollectHistoryService.insertCollectHistory(
                    SEND_YN,
                    collectYMD,
                    ORG_ID,
                    CATE_ID,
                    TITLE,
                    URL, 
                    SHORT_URL, 
                    COL_DT
                )
                
                contentsVO = ContentsVO()
                contentsVO.title = TITLE 
                contentsVO.url = URL 
                contentsVO.contentsOrgId = ORG_ID 
                contentsVO.categoryId = CATE_ID 
                contentsVO.originallink = None 
                contentsVO.link = None 
                contentsVO.pubDt = COL_DT 
                contentsVO.collectDt = COL_DT 
                contentsVO.imageId = self.contentsImageService.recommendImage() 
                contentsVO.lookCount = 0
                contentsVO.likeCount = 0
                contentsVO.disLikeCount = 0
                contentsVO.lookIds = []
                contentsVO.likeIds = []
                contentsVO.disLikeIds = []                
                contentsVO.v1ContentsIdx = SEQ 
                result = BaseQueryService.insert_one(contentsVO)
                if result.inserted_id: 
                    print(f"{contentsVO.collectionName} : {contentsVO.url} : insert 되었습니다.")
                else:
                    print(f"{contentsVO.collectionName} : {contentsVO.url} : insert 실패하였습니다")
                                     
                              

