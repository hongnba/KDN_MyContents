import os
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO, ContentsOrgCategory
from ksubscribe_share.db.mongoManager import MongoClient, MongoManager
import mariadb
from ksubscribe_share.db.data_migration.mariadb_manager import MariaDBManager
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.service.baseQueryService import BaseQueryService

#csa_organization_master, csa_organization_detail(maria) ---> contents_org(mongo) 테이블 

class data_csa_organization():

    commonService = CommCodeService()
    contentsOrgService = ContentsOrgService()
    
    def __init__(self):
        pass
    
    def moveToMongo(self, orgId:str=None):

        # MariaDB 연결 및 리소스 관리
        with MariaDBManager().get_connection() as conn:
        #with MariaDBManager().get_3waysoft_connection() as conn:
            
            with conn.cursor() as cursor:
                if orgId is None:
                    cursor.execute("select * from csa_organization_master")        
                else:
                    cursor.execute(f"select * from csa_organization_master where org_id = '{orgId}'")        
                result = cursor.fetchall()
        
            count = 0
            failcount = 0
            for doc in result:
                ORG_ID = doc[0]
                ORG_NM = doc[1]
                ORG_DESC = doc[2]
                ORG_URL = doc[3]
                ORG_CI_PATH = doc[4]
                KDCC_CI_URL = doc[5]
                ORG_CI_WIDTH = doc[6]
                ORG_CI_HEIGHT = doc[7]
                ORG_CI_SMALL_YN = doc[8]
                ORG_SEARCH_KEYWORD1 = doc[9]
                ORG_SEARCH_KEYWORD2 = doc[10]
                ORG_SEARCH_KEYWORD3 = doc[11]
                REG_DT = doc[12]
                REG_ID = doc[13]
                EDIT_DT = doc[14]
                EDIT_ID = doc[15]
                
                # 필드 초기화
                contentsOrgVO = ContentsOrgVO()
                contentsOrgVO.orgId = ORG_ID
                contentsOrgVO.orgName = ORG_NM if ORG_NM is not None else None
                contentsOrgVO.orgDesc = ORG_DESC if ORG_DESC is not None else None
                contentsOrgVO.orgURL = ORG_URL if ORG_URL is not None else None
                contentsOrgVO.orgCIPath = ORG_CI_PATH if ORG_CI_PATH is not None else None
                contentsOrgVO.kdccCIURL = KDCC_CI_URL if KDCC_CI_URL is not None else None
                contentsOrgVO.orgCIWidth = ORG_CI_WIDTH if ORG_CI_WIDTH is not None else None
                contentsOrgVO.orgCIHeight = ORG_CI_HEIGHT if ORG_CI_HEIGHT is not None else None
                contentsOrgVO.orgCISmallYN = ORG_CI_SMALL_YN if ORG_CI_SMALL_YN is not None else None
                contentsOrgVO.regDt = REG_DT if REG_DT is not None else None            
                contentsOrgVO.regId = REG_ID if REG_ID is not None else None
                contentsOrgVO.editDt = EDIT_DT if EDIT_DT is not None else None
                contentsOrgVO.editId = EDIT_ID if EDIT_ID is not None else None
                
                if contentsOrgVO.orgKeywordList is None:
                    contentsOrgVO.orgKeywordList = []  # 리스트 초기화
                    
                if ORG_SEARCH_KEYWORD1 is not None and ORG_SEARCH_KEYWORD1 != "":                
                    contentsOrgVO.orgKeywordList.append(ORG_SEARCH_KEYWORD1)
                if ORG_SEARCH_KEYWORD2 is not None and ORG_SEARCH_KEYWORD2 != "":                
                    contentsOrgVO.orgKeywordList.append(ORG_SEARCH_KEYWORD2)
                if ORG_SEARCH_KEYWORD3 is not None and ORG_SEARCH_KEYWORD3 != "":                
                    contentsOrgVO.orgKeywordList.append(ORG_SEARCH_KEYWORD3)

                # 카테고리 데이터를 처리
                with conn.cursor() as category_cursor:
                    category_cursor.execute(
                        f"SELECT * FROM csa_organization_detail WHERE org_id = '{contentsOrgVO.orgId}'"
                    )
                    category_result = category_cursor.fetchall()
                    
                    # categoryList 초기화 및 데이터 추가
                    contentsOrgVO.categoryList = []
                    for category_row in category_result:
                        
                        SEQ = category_row[0]
                        ORG_ID = category_row[1]
                        CATE_ID = category_row[2]
                        COL_URL_INFO = category_row[3]
                        PAGE_URL_INFO = category_row[4]
                        SUC_YN = category_row[5]
                        LAST_SUC_YMD = category_row[6]
                        APIKEY1 = category_row[7]
                        APIKEY2 = category_row[8]
                        COL_METHOD = category_row[9]
                        ORG_MAIN_KEYWORD1 = category_row[10]
                        ORG_MAIN_KEYWORD2 = category_row[11]
                        ORG_MAIN_KEYWORD3 = category_row[12]
                        ORG_MAIN_KEYWORD4 = category_row[13]
                        ORG_MAIN_KEYWORD5 = category_row[14]
                        COL_HTML_TBODY_TAG = category_row[15]
                        COL_HTML_TR_TAG = category_row[16]
                        COL_HTML_TD_TAG = category_row[17]
                        COL_HTML_TITLE_TAG = category_row[18]
                        COL_HTML_DATE_N = category_row[19]
                        COL_HTML_URL_TYPE = category_row[20]
                        COL_HTML_URL_LINK_N = category_row[21]
                        COL_HTML_URL_PARAM_N = category_row[22]
                        COL_HTML_URL_ATTR = category_row[23]
                        COL_HTML_DETAIL_PAGE_URL = category_row[24]
                        COL_HTML_URL_PARAM_LISTN_TAG = category_row[25]
                        COL_HTML_PAGEBAR_TAG = category_row[26]
                        COL_HTML_NOW_PAGE_INFO1 = category_row[27]
                        COL_HTML_NOW_PAGE_INFO2 = category_row[28]
                        COL_HTML_NEXT_PAGE_TAG = category_row[29]
                        REG_ID = category_row[30]
                        REG_DT = category_row[31]
                        EDIT_ID = category_row[32]
                        EDIT_DT = category_row[33]
                                    
                        contentsOrgCategory = ContentsOrgCategory()
                        contentsOrgCategory.orgId = ORG_ID
                        contentsOrgCategory.cateId = CATE_ID
                        contentsOrgCategory.cateName = self.commonService.get_cateName_by_cateId(CATE_ID)
                        contentsOrgCategory.cateDesc = ""
                        contentsOrgCategory.collectUrlInfo = COL_URL_INFO
                        contentsOrgCategory.pageUrlInfo = PAGE_URL_INFO

                        if contentsOrgCategory.keywords is None:
                            contentsOrgCategory.keywords = []  # 리스트 초기화
                            
                        if ORG_MAIN_KEYWORD1 is not None and ORG_MAIN_KEYWORD1 != "":                
                            contentsOrgCategory.keywords.append(ORG_MAIN_KEYWORD1)
                        if ORG_MAIN_KEYWORD2 is not None and ORG_MAIN_KEYWORD2 != "":                
                            contentsOrgCategory.keywords.append(ORG_MAIN_KEYWORD2)
                        if ORG_MAIN_KEYWORD3 is not None and ORG_MAIN_KEYWORD3 != "":                
                            contentsOrgCategory.keywords.append(ORG_MAIN_KEYWORD3)
                        if ORG_MAIN_KEYWORD4 is not None and ORG_MAIN_KEYWORD4 != "":                
                            contentsOrgCategory.keywords.append(ORG_MAIN_KEYWORD4)
                        if ORG_MAIN_KEYWORD5 is not None and ORG_MAIN_KEYWORD5 != "":                
                            contentsOrgCategory.keywords.append(ORG_MAIN_KEYWORD5)
                        
                        contentsOrgCategory.sucYN = SUC_YN
                        contentsOrgCategory.lastSucYMD = LAST_SUC_YMD
                        contentsOrgCategory.lastTitle = ""
                        contentsOrgCategory.APIKEY1 = APIKEY1
                        contentsOrgCategory.APIKEY2 = APIKEY2
                        contentsOrgCategory.COL_METHOD = COL_METHOD
                        contentsOrgCategory.COL_HTML_TBODY_TAG = COL_HTML_TBODY_TAG
                        contentsOrgCategory.COL_HTML_TR_TAG = COL_HTML_TR_TAG
                        contentsOrgCategory.COL_HTML_TD_TAG = COL_HTML_TD_TAG
                        contentsOrgCategory.COL_HTML_TITLE_TAG = COL_HTML_TITLE_TAG
                        contentsOrgCategory.COL_HTML_DATE_N = COL_HTML_DATE_N
                        contentsOrgCategory.COL_HTML_URL_TYPE = COL_HTML_URL_TYPE
                        contentsOrgCategory.COL_HTML_URL_LINK_N = COL_HTML_URL_LINK_N
                        contentsOrgCategory.COL_HTML_URL_PARAM_N = COL_HTML_URL_PARAM_N
                        contentsOrgCategory.COL_HTML_URL_ATTR = COL_HTML_URL_ATTR
                        contentsOrgCategory.COL_HTML_DETAIL_PAGE_URL = COL_HTML_DETAIL_PAGE_URL
                        contentsOrgCategory.COL_HTML_URL_PARAM_LISTN_TAG = COL_HTML_URL_PARAM_LISTN_TAG
                        contentsOrgCategory.COL_HTML_PAGEBAR_TAG = COL_HTML_PAGEBAR_TAG
                        contentsOrgCategory.COL_HTML_NOW_PAGE_INFO1 = COL_HTML_NOW_PAGE_INFO1
                        contentsOrgCategory.COL_HTML_NOW_PAGE_INFO2 = COL_HTML_NOW_PAGE_INFO2
                        contentsOrgCategory.COL_HTML_NEXT_PAGE_TAG = COL_HTML_NEXT_PAGE_TAG
                        contentsOrgCategory.REG_ID = REG_ID
                        contentsOrgCategory.REG_DT = REG_DT
                        contentsOrgCategory.EDIT_ID = EDIT_ID
                        contentsOrgCategory.EDIT_DT = EDIT_DT     
                        
                        contentsOrgVO.categoryList.append(contentsOrgCategory)

                result = BaseQueryService.insert_one(contentsOrgVO)
                if result.inserted_id: 
                    count +=1
                    print(f"{contentsOrgVO.collectionName} : {contentsOrgVO.orgId} : insert 되었습니다.")
                else:
                    failcount += 1
                    print(f"{contentsOrgVO.collectionName} : {contentsOrgVO.orgId} : insert 실패하였습니다")
                
        print(f"{contentsOrgVO.collectionName} : {count} : insert 되었습니다.")
        print(f"{contentsOrgVO.collectionName} : {failcount} : insert 실패하였습니다.")
        
    def set_catename(self):
        
        collection = MongoManager().getCollection(ContentsOrgVO.collectionName)
        
        try:
            # 모든 문서 가져오기
            documents = collection.find()

            for doc in documents:
                category_list = doc.get("categoryList", [])

                # categoryList 순회하며 cateName 업데이트
                for category in category_list:
                    cateId = category.get("cateId")
                    cateName = self.commonService.get_cateName_by_cateId(cateId)
                    # cateName 업데이트
                    category["cateName"] = cateName

                # MongoDB 업데이트 수행
                collection.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"categoryList": category_list}}
                )

                print(f"Updated cateName for document with _id: {doc['_id']}")

        except Exception as e:
            print(f"An error occurred: {e}")
   

    image_inputs = [
            {"orgId":"A0001", "orgCIWidth":"200px", "orgCIHeight":"auto"},
            {"orgId":"A0002","orgCIWidth":"200px", "orgCIHeight":"auto"} ,
            {"orgId":"A0003","orgCIWidth":"200px", "orgCIHeight":"auto"} ,
            {"orgId":"A0004","orgCIWidth":"200px", "orgCIHeight":"auto"} ,
            {"orgId":"A0005","orgCIWidth":"200px", "orgCIHeight":"auto"} ,
            {"orgId":"A0006","orgCIWidth":"158px", "orgCIHeight":"auto"} ,
            {"orgId":"A0007","orgCIWidth":"200px", "orgCIHeight":"auto"} ,
            {"orgId":"A0008","orgCIWidth":"200px", "orgCIHeight":"auto"} ,
            {"orgId":"A0009","orgCIWidth":"220px", "orgCIHeight":"auto"} ,
            {"orgId":"A0010","orgCIWidth":"90px", "orgCIHeight":"56px"}  ,
            {"orgId":"A0011","orgCIWidth":"90px", "orgCIHeight":"56px"}  ,
            {"orgId":"A0012","orgCIWidth":"90px", "orgCIHeight":"56px"}  ,
            {"orgId":"A0013","orgCIWidth":"90px", "orgCIHeight":"56px"}  ,
            {"orgId":"A0014","orgCIWidth":"120px", "orgCIHeight":"auto"} ,
            {"orgId":"A0015","orgCIWidth":"180px", "orgCIHeight":"auto"} ,
            {"orgId":"A0016","orgCIWidth":"90px", "orgCIHeight":"56px"}  ,
            {"orgId":"A0017","orgCIWidth":"90px", "orgCIHeight":"56px"}  ,
            {"orgId":"A0018","orgCIWidth":"90px", "orgCIHeight":"56px"}  ,
            {"orgId":"A0019","orgCIWidth":"90px", "orgCIHeight":"56px"}  ,
            {"orgId":"A0020","orgCIWidth":"90px", "orgCIHeight":"56px"}  ,
            {"orgId":"A0021","orgCIWidth":"90px", "orgCIHeight":"56px"}  ,
            {"orgId":"A0022","orgCIWidth":"158px", "orgCIHeight":"auto"} ,
            {"orgId":"A0023","orgCIWidth":"158px", "orgCIHeight":"auto"} ,
            {"orgId":"A0024","orgCIWidth":"200px", "orgCIHeight":"auto"} ,
            {"orgId":"A0025","orgCIWidth":"220px", "orgCIHeight":"auto"} ,
            {"orgId":"A0026","orgCIWidth":"auto", "orgCIHeight":"100px"} ,
            {"orgId":"A0027","orgCIWidth":"120px", "orgCIHeight":"auto"} ,
            {"orgId":"A0028","orgCIWidth":"200px", "orgCIHeight":"auto"} ,
            {"orgId":"A0029","orgCIWidth":"210px", "orgCIHeight":"auto"} 
        ]
        
    def get_image_width_height(self):
        for item in self.image_inputs: 
            self.contentsOrgService.updateImageInfo(item["orgId"],item["orgCIWidth"],item["orgCIHeight"])
        

    def get_image_width_height_of_org(self, orgId:str):

        for item in self.image_inputs: 
            if item["orgId"] == orgId:
                self.contentsOrgService.updateImageInfo(item["orgId"],item["orgCIWidth"],item["orgCIHeight"])
                break
           

    collect_method_inputs = [
            {"org_id":"A0001", "category_id":"B0001", "collectMethod":"onlyPdf","tagElement":"","tagAttr":"","tagAttrValue":"" },                                   
            {"org_id":"A0001", "category_id":"B0002", "collectMethod":"textInTag","tagElement":"article","tagAttr":"id","tagAttrValue":"cont-body" },
            {"org_id":"A0001", "category_id":"B0010", "collectMethod":"textInBody","tagElement":"","tagAttr":"","tagAttrValue":"" },
            {"org_id":"A0001", "category_id":"B0011", "collectMethod":"textInTag","tagElement":"article","tagAttr":"id","tagAttrValue":"cont-body"},
            {"org_id":"A0001", "category_id":"B0012", "collectMethod":"textInTag","tagElement":"article","tagAttr":"id","tagAttrValue":"cont-body"},
            {"org_id":"A0002", "category_id":"B0001", "collectMethod":"textInTag","tagElement":"div","tagAttr":"id","tagAttrValue":"start_contents"},
            {"org_id":"A0002", "category_id":"B0003", "collectMethod":"textInTag","tagElement":"div","tagAttr":"id","tagAttrValue":"start_contents"},
            {"org_id":"A0002", "category_id":"B0010", "collectMethod":"textInBody","tagElement":"","tagAttr":"","tagAttrValue":"" },
            {"org_id":"A0003", "category_id":"B0002", "collectMethod":"textInTag","tagElement":"div","tagAttr":"class","tagAttrValue":"sub_cont"},
            {"org_id":"A0003", "category_id":"B0003", "collectMethod":"textInTag","tagElement":"div","tagAttr":"class","tagAttrValue":"sub_cont"},
            {"org_id":"A0003", "category_id":"B0010", "collectMethod":"textInBody","tagElement":"","tagAttr":"","tagAttrValue":"" },
            {"org_id":"A0004", "category_id":"B0005", "collectMethod":"","tagElement":"","tagAttr":"","tagAttrValue":""},
            {"org_id":"A0005", "category_id":"B0002", "collectMethod":"textInTag","tagElement":"div","tagAttr":"id","tagAttrValue":"divBrd_cont"},
            {"org_id":"A0005", "category_id":"B0003", "collectMethod":"textInTag","tagElement":"div","tagAttr":"id","tagAttrValue":"container-sub"},
            {"org_id":"A0005", "category_id":"B0005", "collectMethod":"textInTag","tagElement":"div","tagAttr":"id","tagAttrValue":"container-sub"},
            {"org_id":"A0005", "category_id":"B0010", "collectMethod":"textInBody","tagElement":"","tagAttr":"","tagAttrValue":"" },
            {"org_id":"A0006", "category_id":"B0001", "collectMethod":"textInTag","tagElement":"section","tagAttr":"class","tagAttrValue":"lb_con"},
            {"org_id":"A0006", "category_id":"B0003", "collectMethod":"textInTag","tagElement":"section","tagAttr":"class","tagAttrValue":"lb_con"},
            {"org_id":"A0006", "category_id":"B0005", "collectMethod":"textInTag","tagElement":"section","tagAttr":"class","tagAttrValue":"lb_con"},
            {"org_id":"A0006", "category_id":"B0010", "collectMethod":"textInBody","tagElement":"","tagAttr":"","tagAttrValue":"" },
            {"org_id":"A0007", "category_id":"B0002", "collectMethod":"textInTag","tagElement":"section","tagAttr":"id","tagAttrValue":"content"},
            {"org_id":"A0007", "category_id":"B0010", "collectMethod":"textInBody","tagElement":"","tagAttr":"","tagAttrValue":"" },
            {"org_id":"A0008", "category_id":"B0003", "collectMethod":"textInTag","tagElement":"section","tagAttr":"id","tagAttrValue":"sub_contentsArea"},
            {"org_id":"A0008", "category_id":"B0005", "collectMethod":"textInTag","tagElement":"section","tagAttr":"id","tagAttrValue":"sub_contentsArea"},
            {"org_id":"A0008", "category_id":"B0010", "collectMethod":"textInBody","tagElement":"","tagAttr":"","tagAttrValue":"" },
            {"org_id":"A0009", "category_id":"B0002", "collectMethod":"textInTag","tagElement":"div","tagAttr":"id","tagAttrValue":"bbs1view2"},
            {"org_id":"A0009", "category_id":"B0010", "collectMethod":"textInBody","tagElement":"","tagAttr":"","tagAttrValue":"" },
            {"org_id":"A0010", "category_id":"B0001", "collectMethod":"onlyPDF","tagElement":"","tagAttr":"","tagAttrValue":""},
            {"org_id":"A0010", "category_id":"B0010", "collectMethod":"textInBody","tagElement":"","tagAttr":"","tagAttrValue":"" },
            {"org_id":"A0011", "category_id":"B0001", "collectMethod":"textInTag","tagElement":"article","tagAttr":"","tagAttrValue":""},
            {"org_id":"A0011", "category_id":"B0010", "collectMethod":"textInBody","tagElement":"","tagAttr":"","tagAttrValue":"" },
            {"org_id":"A0012", "category_id":"B0001", "collectMethod":"textInTag","tagElement":"div","tagAttr":"id","tagAttrValue":"contents_body"},    
            {"org_id":"A0012", "category_id":"B0010", "collectMethod":"textInBody","tagElement":"","tagAttr":"","tagAttrValue":"" },
            {"org_id":"A0013", "category_id":"B0001", "collectMethod":"textInBody","tagElement":"","tagAttr":"","tagAttrValue":""},
            {"org_id":"A0013", "category_id":"B0010", "collectMethod":"textInBody","tagElement":"","tagAttr":"","tagAttrValue":"" },
            {"org_id":"A0014", "category_id":"B0001", "collectMethod":"textInTag","tagElement":"section","tagAttr":"id","tagAttrValue":"subContent"},
            {"org_id":"A0014", "category_id":"B0010", "collectMethod":"textInBody","tagElement":"","tagAttr":"","tagAttrValue":"" },
            {"org_id":"A0015", "category_id":"B0001", "collectMethod":"textInTag","tagElement":"table","tagAttr":"class","tagAttrValue":"tableV"},
            {"org_id":"A0015", "category_id":"B0010", "collectMethod":"textInBody","tagElement":"","tagAttr":"","tagAttrValue":"" },
            {"org_id":"A0016", "category_id":"B0001", "collectMethod":"textInTag","tagElement":"div","tagAttr":"class","tagAttrValue":"dataView"},
            {"org_id":"A0016", "category_id":"B0010", "collectMethod":"textInBody","tagElement":"","tagAttr":"","tagAttrValue":"" },
            {"org_id":"A0017", "category_id":"B0001", "collectMethod":"textInTag","tagElement":"div","tagAttr":"class","tagAttrValue":"wrap"},
            {"org_id":"A0017", "category_id":"B0010", "collectMethod":"textInBody","tagElement":"","tagAttr":"","tagAttrValue":"" },
            {"org_id":"A0018", "category_id":"B0001", "collectMethod":"textInTag","tagElement":"div","tagAttr":"class","tagAttrValue":"scSec_cont bb_n"},
            {"org_id":"A0018", "category_id":"B0010", "collectMethod":"textInBody","tagElement":"","tagAttr":"","tagAttrValue":"" },
            {"org_id":"A0019", "category_id":"B0001", "collectMethod":"textInTag","tagElement":"div","tagAttr":"id","tagAttrValue":"contents_body"},
            {"org_id":"A0019", "category_id":"B0010", "collectMethod":"textInBody","tagElement":"","tagAttr":"","tagAttrValue":"" },
            {"org_id":"A0020", "category_id":"B0001", "collectMethod":"textInTag","tagElement":"div","tagAttr":"id","tagAttrValue":"right_column"},
            {"org_id":"A0020", "category_id":"B0010", "collectMethod":"textInBody","tagElement":"","tagAttr":"","tagAttrValue":"" },
            {"org_id":"A0021", "category_id":"B0001", "collectMethod":"textInTag","tagElement":"section","tagAttr":"id","tagAttrValue":"content"},
            {"org_id":"A0021", "category_id":"B0010", "collectMethod":"textInBody","tagElement":"","tagAttr":"","tagAttrValue":"" },
            {"org_id":"A0022", "category_id":"B0003", "collectMethod":"textInTag","tagElement":"div","tagAttr":"id","tagAttrValue":"content"},
            {"org_id":"A0022", "category_id":"B0010", "collectMethod":"textInBody","tagElement":"","tagAttr":"","tagAttrValue":"" },
            {"org_id":"A0022", "category_id":"B0004", "collectMethod":"textInTag","tagElement":"div","tagAttr":"id","tagAttrValue":"content"},
            {"org_id":"A0023", "category_id":"B0003", "collectMethod":"textInTag","tagElement":"div","tagAttr":"class","tagAttrValue":"board_wrap"},
            {"org_id":"A0023", "category_id":"B0004", "collectMethod":"textInTag","tagElement":"div","tagAttr":"class","tagAttrValue":"board_wrap"},
            {"org_id":"A0023", "category_id":"B0010", "collectMethod":"textInBody","tagElement":"","tagAttr":"","tagAttrValue":"" },
            {"org_id":"A0024", "category_id":"B0006", "collectMethod":"textInTag","tagElement":"div","tagAttr":"class","tagAttrValue":"notice_view"},
            {"org_id":"A0024", "category_id":"B0010", "collectMethod":"textInBody","tagElement":"","tagAttr":"","tagAttrValue":"" },
            {"org_id":"A0025", "category_id":"B0003", "collectMethod":"textInTag","tagElement":"div","tagAttr":"class","tagAttrValue":"cont"},
            {"org_id":"A0025", "category_id":"B0010", "collectMethod":"textInBody","tagElement":"","tagAttr":"","tagAttrValue":"" },
            {"org_id":"A0026", "category_id":"B0010", "collectMethod":"textInBody","tagElement":"","tagAttr":"","tagAttrValue":"" },
            {"org_id":"A0027", "category_id":"B0001", "collectMethod":"textInTag","tagElement":"div","tagAttr":"class","tagAttrValue":"content sub_content"},
            {"org_id":"A0027", "category_id":"B0010", "collectMethod":"textInBody","tagElement":"","tagAttr":"","tagAttrValue":"" },
            {"org_id":"A0027", "category_id":"B0003", "collectMethod":"textInTag","tagElement":"div","tagAttr":"class","tagAttrValue":"content sub_content"},
            {"org_id":"A0028", "category_id":"B0001", "collectMethod":"textInTag","tagElement":"div","tagAttr":"id","tagAttrValue":"contents_start"},
            {"org_id":"A0028", "category_id":"B0002", "collectMethod":"textInTag","tagElement":"div","tagAttr":"id","tagAttrValue":"contents_start"},
            {"org_id":"A0028", "category_id":"B0005", "collectMethod":"textInTag","tagElement":"article","tagAttr":"id","tagAttrValue":"cont-body"},
            {"org_id":"A0028", "category_id":"B0010", "collectMethod":"textInBody","tagElement":"","tagAttr":"","tagAttrValue":"" },
            {"org_id":"A0029", "category_id":"B0001", "collectMethod":"onlyPDF","tagElement":"","tagAttr":"","tagAttrValue":""},
            {"org_id":"A0029", "category_id":"B0005", "collectMethod":"onlyPDF","tagElement":"","tagAttr":"","tagAttrValue":""},
            {"org_id":"A0029", "category_id":"B0003", "collectMethod":"onlyPDF","tagElement":"","tagAttr":"","tagAttrValue":""}    
        ]               
               
    def get_collect_method(self): 

        for item in self.collect_method_inputs: 
            self.contentsOrgService.updateCollectInfo(item["org_id"],item["category_id"],item["collectMethod"],item["tagElement"],item["tagAttr"],item["tagAttrValue"])
         
    def get_collect_method_of_org(self, orgId:str): 

        for item in self.collect_method_inputs: 
            if orgId == item["org_id"]: 
                self.contentsOrgService.updateCollectInfo(orgId,item["category_id"],item["collectMethod"],item["tagElement"],item["tagAttr"],item["tagAttrValue"])
                break
         
    org_name_synonym_list = [
            {"orgId":"A0001", "orgNameSynonym": ["산업통상자원부","산업부"]},				
            {"orgId":"A0002", "orgNameSynonym": ["개인정보보호위원회","개보위"]},				
            {"orgId":"A0003", "orgNameSynonym": ["과학기술정보통신부","과기부"]},				
            {"orgId":"A0004", "orgNameSynonym": ["나라장터"]},
            {"orgId":"A0005", "orgNameSynonym": ["한국에너지기술평가원","에기평"]},
            {"orgId":"A0006", "orgNameSynonym": ["한국인터넷진흥원","KISA"]},
            {"orgId":"A0007", "orgNameSynonym": ["한국산업기술진흥원","KIAT"]},
            {"orgId":"A0008", "orgNameSynonym": ["한국지능정보사회진흥원","NIA"]},
            {"orgId":"A0009", "orgNameSynonym": ["산업기술 R&D 정보포털"]},
            {"orgId":"A0010", "orgNameSynonym": ["한국전력공사","한국전력"]},
            {"orgId":"A0011", "orgNameSynonym": ["한국수력원자력","한수원"]},
            {"orgId":"A0012", "orgNameSynonym": ["한국전력거래소","전력거래소"]},
            {"orgId":"A0013", "orgNameSynonym": ["한국남부발전","남부발전"]},
            {"orgId":"A0014", "orgNameSynonym": ["한국남동발전","남동발전"]},
            {"orgId":"A0015", "orgNameSynonym": ["한국중부발전","중부발전"]},
            {"orgId":"A0016", "orgNameSynonym": ["한국서부발전","서부발전"]},
            {"orgId":"A0017", "orgNameSynonym": ["한국동서발전","동서발전"]},
            {"orgId":"A0018", "orgNameSynonym": ["한전KDN"]},
            {"orgId":"A0019", "orgNameSynonym": ["한국전력기술"]},
            {"orgId":"A0020", "orgNameSynonym": ["한전KPS"]},
            {"orgId":"A0021", "orgNameSynonym": ["한전원자력원료"]},
            {"orgId":"A0022", "orgNameSynonym": ["한국에너지재단"]},
            {"orgId":"A0023", "orgNameSynonym": ["한국에너지공단"]},
            {"orgId":"A0024", "orgNameSynonym": ["NTIS"]},
            {"orgId":"A0025", "orgNameSynonym": ["한국데이터산업진흥원","KDATA"]},
            {"orgId":"A0026", "orgNameSynonym": ["네이버"]},
            {"orgId":"A0027", "orgNameSynonym": ["한국산업지능화협회"]},
            {"orgId":"A0028", "orgNameSynonym": ["전남정보문화산업진흥원"]},
            {"orgId":"A0029", "orgNameSynonym": ["한국농수산식품유통공사"]}
        ]

    #mongodb에 alias 정보 넣기         
    def updateOrgNameSynonym(self):
        for item in self.org_name_synonym_list: 
            self.contentsOrgService.updateOrgNameSynonym(item["orgId"],item["orgNameSynonym"])
         
if __name__ == "__main__":

    data_csa_organization_class = data_csa_organization()
    data_csa_organization_class.updateOrgNameSynonym()
    
    
    