import os
from ksubscribe_share.db.dbmodelV2.contentsImageVO import contentsImageVO
from ksubscribe_share.db.mongoManager import MongoClient, MongoManager

coll = MongoManager().getCollection("contents_image")
coll.delete_many({})



# JPG 파일이 있는 폴더 경로
folder_path = r"C:\Users\admin\Desktop\MyContents 키워드 사진"

# 폴더의 모든 JPG 파일 처리
for file_name in os.listdir(folder_path):
    if file_name.endswith(".jpg") or file_name.endswith(".png"):
        # 파일 이름 파싱
        keyword = file_name.split('_')[0]
        
        ext = os.path.splitext(file_name)[1][1:]
        
        # 이미지 파일 읽기
        file_path = os.path.join(folder_path, file_name)
        with open(file_path, "rb") as file:
            image_bytes = file.read()
        
        # MongoDB에 저장
        # document = {
        #     "keyword": keyword,
        #     "image": image_bytes
        # }
        
        document = contentsImageVO(
            keyword=keyword,
            image=image_bytes,
            imageType=ext,
        ).insert_one()

print("모든 이미지를 MongoDB에 저장했습니다.")