import os
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import (
    ContentsOrgVO,
    ContentsOrgCategory,
)
from ksubscribe_share.db.dbmodelV2.commCodeVO import CommCodeVO
from ksubscribe_share.db.mongoManager import MongoClient, MongoManager
import mariadb
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.data_migration.mariadb_manager import MariaDBManager
from ksubscribe_share.db.service.baseQueryService import BaseQueryService


#comncode(maria) ---> common_code(mongo) 테이블 

class data_cmmn_code():

    commonService = CommCodeService()
    org_img_dict = {}
    category_img_dict = {}

    def __init__(self):
        pass
                
    def GetImageSource(fileName):
        # JPG 파일이 있는 폴더 경로
        folder_path = r"F:\K_Subscribe\Images"
        file_path = os.path.join(folder_path, fileName)

        if os.path.isfile(file_path):
            print(f"File exists: {file_path}")
        else:
            print(f"File does not exist: {file_path}")
            
        # 이미지 파일 읽기
        with open(file_path, "rb") as file:
            image_bytes = file.read()
        
        return image_bytes
    
    def makeImageDic(self):
        # 기관에 대한 JPG 파일이 있는 폴더 경로
        org_img_folder_path = r"ksubscribe_share\db\data_migration\image\org"

        # 폴더의 모든 JPG 파일 처리
        for file_name in os.listdir(org_img_folder_path):
            if file_name.endswith(".jpg") or file_name.endswith(".png"):
                # 파일 이름 파싱
                key = file_name.split('.')[0]
                
                # 이미지 파일 읽기
                file_path = os.path.join(org_img_folder_path, file_name)
                with open(file_path, "rb") as file:
                    self.org_img_dict[key] = [file_path, file.read()]
        
    def makeCategoryImageDic(self):

        # 카테고리에 대한 JPG 파일이 있는 폴더 경로
        category_img_folder_path = r"ksubscribe_share\db\data_migration\image\category"

        # 폴더의 모든 JPG 파일 처리
        for file_name in os.listdir(category_img_folder_path):
            if file_name.endswith(".jpg") or file_name.endswith(".png"):
                # 파일 이름 파싱
                key = file_name.split('.')[0]
                
                # 이미지 파일 읽기
                file_path = os.path.join(category_img_folder_path, file_name)
                with open(file_path, "rb") as file:
                    self.category_img_dict[key] = [file_path, file.read()]
    
    def moveToMongo(self):

        self.makeImageDic()
        self.makeCategoryImageDic()
        
        with MariaDBManager().get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("select * from cmmncode")        
            result = cursor.fetchall()
        
                        
        for doc in result:
            CODEID = doc[0]
            CODE = doc[1]
            CODENM = doc[2]
            CODEDC = doc[3]
            USEYN = doc[4]
            IMGPATH = doc[5]
            CODEDESC = doc[6]
            REGDT = doc[7]
            REGID = doc[8]
            EDITDT = doc[9]
            EDITID = doc[10]
            
            commCodeVO = CommCodeVO()            
            commCodeVO.codeId = CODEID if CODEID is not None else ""
            commCodeVO.code = CODE if CODE is not None else ""
            commCodeVO.codeName = CODENM if CODENM is not None else ""
            commCodeVO.codeDc = CODEDC if CODEDC is not None else ""
            commCodeVO.codeDesc = CODEDESC if CODEDESC is not None else ""
            commCodeVO.useYN = USEYN if USEYN is not None else ""
            commCodeVO.imgPath = IMGPATH if IMGPATH is not None else ""
            commCodeVO.regDt = REGDT if REGDT is not None else ""
            commCodeVO.regId = REGID if REGID is not None else ""
            commCodeVO.editDt = EDITDT if EDITDT is not None else ""
            commCodeVO.editId = EDITID if EDITID is not None else ""
            commCodeVO.imageSource = ""
            commCodeVO.domain = ""
            
            
            if (commCodeVO.codeId == "COM00A"):   
                if (self.org_img_dict.get(commCodeVO.codeName) != None):

                    commCodeVO.imgPath=self.org_img_dict.get(commCodeVO.codeName)[0] 
                    commCodeVO.imageSource=self.org_img_dict.get(commCodeVO.codeName)[1] 
                    commCodeVO.domain=self.org_domain_dict.get(commCodeVO.codeName)
                    
            elif (commCodeVO.codeId == "COM00B"): 
                if (self.category_img_dict.get(commCodeVO.codeName) != None):

                    commCodeVO.imgPath=self.category_img_dict.get(commCodeVO.codeName)[0] 
                    commCodeVO.imageSource=self.category_img_dict.get(commCodeVO.codeName)[1] 
                    commCodeVO.domain=""

            result = BaseQueryService.insert_one(commCodeVO)    
            if result.inserted_id: 
                print(f"{commCodeVO.collectionName} : {commCodeVO.code} : insert 되었습니다.")
            else:
                print(f"{commCodeVO.collectionName} : {commCodeVO.code} : insert 실패하였습니다")
                        
                        
    org_domain_dict = {
        "산업통상자원부" : "korea.kr",
        "개인정보보호위원회" : "korea.kr",
        "과학기술정보통신부" : "korea.kr",
        "나라장터" : "korea.kr",
        "한국에너지기술평가원" : "ketep.re.kr",
        "한국인터넷진흥원" : "kisa.or.kr",
        "한국산업기술진흥원" : "kiat.or.kr",
        "한국지능정보사회진흥원" : "nia.or.kr",
        "산업기술 R&D 정보포털" : "keit.re.kr",
        "한국전력공사(주)" : "kepco.co.kr",
        "한국수력원자력(주)" : "khnp.co.kr",
        "한국전력거래소" : "kpx.or.kr",
        "한국남부발전(주)" : "kospo.co.kr",
        "한국남동발전(주)" : "koenergy.kr",
        "한국중부발전(주)" : "komipo.co.kr",
        "한국서부발전(주)" : "iwest.co.kr",
        "한국동서발전(주)" : "ewp.co.kr",
        "한국전력기술(주)" : "kepco-enc.com",
        "한전KDN(주)" : "kdn.com",
        "한전KPS(주)" : "kps.co.kr",
        "한전원자력원료(주)" : "knfc.co.kr",
        "한국에너지재단" : "koref.or.kr",
        "한국에너지공단" : "energy.or.kr",
        "NTIS" : "kisti.re.kr",
        "한국데이터산업진흥원" : "kdata.or.kr",
        "네이버 뉴스" : "",
        "한국산업지능화협회" : "koiia.or.kr",
        "전남정보문화산업진흥원" : "jcia.or.kr",
        "한국농수산식품유통공사" : "at.or.kr",
    }
        
    def reference_code(self):

        # 기관에 대한 dictionary (참고용)
        org_image_dict = {
            "motie.png" : "산업통상자원부",
            "pipc.png" : "개인정보보호위원회",
            "msit.png" : "과학기술정보통신부",
            "g2b.png" : "나라장터",
            "ketep.png" : "한국에너지기술평가원",
            "kisa.png" : "한국인터넷진흥원",
            "kiat.png" : "한국산업기술진흥원",
            "nia.png" : "한국지능정보사회진흥원",
            "keit.png" : "산업기술 R&D 정보포털",
            "kepco.png" : "한국전력공사(주)",
            "khnp.png" : "한국수력원자력(주)",
            "kpx.png" : "한국전력거래소",
            "kospo.png" : "한국남부발전(주)",
            "koen.png" : "한국남동발전(주)",
            "komipo.png" : "한국중부발전(주)",
            "enc.png" : "한국전력기술(주)",
            "iwest.jpg" : "한국서부발전(주)",
            "ewp.png" : "한국동서발전(주)",
            "kdn.png" : "한전KDN(주)",
            "enc.jpg"  : "한국전력기술(주)",
            "kps.png" : "한전KPS(주)",
            "knfc.png" : "한전원자력원료(주)",
            "koref.png" : "한국에너지재단",
            "kea.png" : "한국에너지공단",
            "ntis.png" : "NTIS",
            "kdata.png" : "한국데이터산업진흥원",
            "naver.png" : "네이버 뉴스",
            "koiia.png" : "한국산업지능화협회",
            "jcia.png" : "전남정보문화산업진흥원",
            "at.png" : "한국농수산식품유통공사",
        }
        
