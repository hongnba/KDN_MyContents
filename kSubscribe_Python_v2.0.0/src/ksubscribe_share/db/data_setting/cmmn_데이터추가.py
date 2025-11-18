import os
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import (
    ContentsOrgVO,
    ContentsOrgCategory,
)
from ksubscribe_share.db.dbmodelV2.commCodeVO import commCodeVO
from ksubscribe_share.db.mongoManager import MongoClient, MongoManager

# 1. 기관 데이터 가져오기
import mariadb

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



coll = MongoManager().getCollection("common_code")
coll.delete_many({})

conn = mariadb.connect(
    user="3way", password="3waysoft", host="10.100.12.71", port=3306, database="cds"
)
cursor = conn.cursor()

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


# 기관에 대한 JPG 파일이 있는 폴더 경로
org_img_folder_path = r"C:\Users\admin\Desktop\MyContents 기관 사진"
org_img_dict = {}

# 폴더의 모든 JPG 파일 처리
for file_name in os.listdir(org_img_folder_path):
    if file_name.endswith(".jpg") or file_name.endswith(".png"):
        # 파일 이름 파싱
        key = file_name.split('.')[0]
        
        # 이미지 파일 읽기
        file_path = os.path.join(org_img_folder_path, file_name)
        with open(file_path, "rb") as file:
            org_img_dict[key] = [file_path, file.read()]

# 카테고리에 대한 JPG 파일이 있는 폴더 경로
category_img_folder_path = r"C:\Users\admin\Desktop\MyContents 카테고리 사진"
category_img_dict = {}

# 폴더의 모든 JPG 파일 처리
for file_name in os.listdir(category_img_folder_path):
    if file_name.endswith(".jpg") or file_name.endswith(".png"):
        # 파일 이름 파싱
        key = file_name.split('.')[0]
        
        # 이미지 파일 읽기
        file_path = os.path.join(category_img_folder_path, file_name)
        with open(file_path, "rb") as file:
            category_img_dict[key] = [file_path, file.read()]

cursor.execute("select * from cmmncode")
result = cursor.fetchall()
docs = []
for doc in result:

    codeId = doc[0]
    codeName = doc[2]
    codeDesc = doc[3]
    
    if (codeId == "COM00A"):   #기관 
        if (org_img_dict.get(codeName) != None):
            commCodeVO(
                    codeId=doc[0],
                    code=doc[1],
                    codeName=doc[2],
                    codeDesc=doc[3],
                    useYN=doc[4],
                    # imgPath=doc[5],
                    regDt=doc[7],
                    regId=doc[8],
                    editDt=doc[9],
                    editId=doc[10],
                    imgPath=org_img_dict.get(codeName)[0],
                    imageSource=org_img_dict.get(codeName)[1],
                    domain="domain.com",
                    ).insert_one()
                
        
    elif (codeId == "COM00B"): #카테고리구분
        if (category_img_dict.get(codeName) != None):
            commCodeVO(
                codeId=doc[0],
                code=doc[1],
                codeName=doc[2],
                codeDesc=doc[3],
                useYN=doc[4],
                # imgPath=doc[5],
                regDt=doc[7],
                regId=doc[8],
                editDt=doc[9],
                editId=doc[10],
                imgPath=category_img_dict.get(codeName)[0],
                imageSource=category_img_dict.get(codeName)[1],
                domain="",
                ).insert_one()
    
    else:
        commCodeVO(
            codeId=doc[0],
            code=doc[1],
            codeName=doc[2],
            codeDesc=doc[3],
            useYN=doc[4],
            imgPath=doc[5],
            regDt=doc[7],
            regId=doc[8],
            editDt=doc[9],
            editId=doc[10],
            imageSource=None,
            domain="",
        ).insert_one()

conn.close()
