import os
from typing import List
import mariadb
from ksubscribe_share.db.dbmodelV2.favoriteSubscribeListVO import FavoriteSubscribeListVO, OrgIdAndCateId
from ksubscribe_share.db.mongoManager import MongoClient, MongoManager
from ksubscribe_share.db.data_migration.mariadb_manager import MariaDBManager
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.baseQueryService import BaseQueryService


#csa_catalog_master, csa_catalog_detail(maria) ---> favorite_subscribe_list(mongo) 테이블 

class data_csa_catalog_master():

    commonService = CommCodeService()
    
    def __init__(self):
        pass
    
    def moveToMongo(self):

        # MariaDB 연결 및 리소스 관리
        with MariaDBManager().get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("select * from csa_catalog_master where catg_gubun != 'D0007'")        
                result = cursor.fetchall()
        
            for doc in result:
                CATG_ID = doc[0]
                CATG_GUBUN = doc[1]
                CATG_NM = doc[2]
                CATG_CI_PATH = doc[3]
                CATG_DESC = doc[4]
                CATG_KEYWORD1 = doc[5]
                CATG_KEYWORD2 = doc[6]
                CATG_KEYWORD3 = doc[7]
                CATG_KEYWORD4 = doc[8]
                CATG_KEYWORD5 = doc[9]
                REG_DT = doc[10]
                REG_ID = doc[11]
                EDIT_DT = doc[12]
                EDIT_ID = doc[13]
                KDCC_CI_URL = doc[14]
                CATG_CI_WIDTH = doc[15]
                CATG_CI_HEIGHT = doc[16]
                CATG_CI_SMALL_YN = doc[17]
                
                # 필드 초기화
                favoriteSubscribeListVO = FavoriteSubscribeListVO()
                favoriteSubscribeListVO.favoriteListId = CATG_ID if CATG_ID is not None else None
                favoriteSubscribeListVO.favoriteListGubun = CATG_GUBUN if CATG_GUBUN is not None else None
                favoriteSubscribeListVO.favoriteListName = CATG_NM if CATG_NM is not None else None
                favoriteSubscribeListVO.favoriteListDesc = CATG_DESC if CATG_DESC is not None else None
                favoriteSubscribeListVO.regDt = REG_DT if REG_DT is not None else None
                favoriteSubscribeListVO.regId = REG_ID if REG_ID is not None else None
                favoriteSubscribeListVO.editDt = EDIT_DT if EDIT_DT is not None else None
                favoriteSubscribeListVO.editId = EDIT_ID if EDIT_ID is not None else None
                favoriteSubscribeListVO.imageType = ""
                favoriteSubscribeListVO.imageSource = ""            
                favoriteSubscribeListVO.cIWidth = "120px"
                favoriteSubscribeListVO.cIHeight = "auto"
                
                keywords : List[str] = []
                if CATG_KEYWORD1 is not None and CATG_KEYWORD1.strip() != "":
                    keywords.append(CATG_KEYWORD1)
                if CATG_KEYWORD2 is not None and CATG_KEYWORD2.strip() != "":
                    keywords.append(CATG_KEYWORD2)
                if CATG_KEYWORD3 is not None and CATG_KEYWORD3.strip() != "":
                    keywords.append(CATG_KEYWORD3)
                if CATG_KEYWORD4 is not None and CATG_KEYWORD4.strip() != "":
                    keywords.append(CATG_KEYWORD4)
                if CATG_KEYWORD5 is not None and CATG_KEYWORD5.strip() != "":
                    keywords.append(CATG_KEYWORD5)
                                    
                favoriteSubscribeListVO.keywords = keywords if keywords is not None else []
                
                # 카테고리 데이터를 처리
                with conn.cursor() as category_cursor:
                    category_cursor.execute(
                        f"SELECT * FROM csa_catalog_detail WHERE catg_id = '{CATG_ID}'"
                    )
                    category_result = category_cursor.fetchall()
                    
                    # categoryList 초기화 및 데이터 추가
                    favoriteSubscribeListVO.orgIdAndCateIds = []
                    for category_row in category_result:
                        
                        CATG_ID = category_row[0]
                        ORG_ID = category_row[1]
                        CATE_ID = category_row[2]
                        REG_DT = category_row[3]
                        REG_ID = category_row[4]
                        EDIT_DT = category_row[5]
                        EDIT_ID = category_row[6]
                        
                        orgIdAndCateId = OrgIdAndCateId()
                        orgIdAndCateId.orgId = ORG_ID if ORG_ID is not None else None
                        orgIdAndCateId.cateId = CATE_ID if CATE_ID is not None else None
                        orgIdAndCateId.regDt = REG_DT if REG_DT is not None else None
                        orgIdAndCateId.regId = REG_ID if REG_ID is not None else None
                        orgIdAndCateId.editDt = EDIT_DT if EDIT_DT is not None else None     
                        orgIdAndCateId.editId = EDIT_ID if EDIT_ID is not None else None
                        
                        favoriteSubscribeListVO.orgIdAndCateIds.append(orgIdAndCateId)

                result = BaseQueryService.insert_one(favoriteSubscribeListVO)
                if result.inserted_id: 
                    print(f"{favoriteSubscribeListVO.collectionName} : {favoriteSubscribeListVO.favoriteListId} : insert 되었습니다.")
                else:
                    print(f"{favoriteSubscribeListVO.collectionName} : {favoriteSubscribeListVO.favoriteListId} : insert 실패하였습니다")
                
                

