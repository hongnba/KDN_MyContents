from ksubscribe_share.db.dbmodelV2.contentsOrgVO import (
    ContentsOrgVO,
    ContentsOrgCategory,
)
from ksubscribe_share.db.dbmodelV2.commCodeVO import commCodeVO
from ksubscribe_share.db.mongoManager import MongoClient, MongoManager

# 1. 기관 데이터 가져오기
import mariadb
import os


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

conn = mariadb.connect(
    user="3way", password="3waysoft", host="192.168.1.200", port=3306, database="cds"
)
cursor = conn.cursor()

cursor.execute("select * from cmmncode where codeid='COM00B'")
result = cursor.fetchall()
docs = []
for doc in result:

    fileName = doc[1]+".png"
    
    commCodeVO(
        codeId=doc[0],
        code=doc[1],
        codeName=doc[2],
        codeDesc=doc[3],
        useYN=doc[4],
        imgPath=fileName,
        regDt=doc[7],
        regId=doc[8],
        editDt=doc[9],
        editId=doc[10],
        imageSource = GetImageSource(fileName),
        domain="domain.com"
    ).insert_one()

conn.close()

