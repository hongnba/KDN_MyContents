import os
from ksubscribe_share.db.dbmodelV2.contentsImageVO import ContentsImageVO
from ksubscribe_share.db.mongoManager import MongoClient, MongoManager
from ksubscribe_share.db.service.baseQueryService import BaseQueryService



class data_content_image():

    def moveToMongo(self):

        # JPG 파일이 있는 폴더 경로
        folder_path = r"ksubscribe_share\db\data_migration\image\contents"

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
                
                contentsImageVO = ContentsImageVO(
                    keyword=keyword,
                    image=image_bytes,
                    imageType=ext,
                )
                
                result = BaseQueryService.insert_one(contentsImageVO)
                if result.inserted_id: 
                    print(f"{contentsImageVO.collectionName} : {contentsImageVO.keyword} : insert 되었습니다.")
                else:
                    print(f"{contentsImageVO.collectionName} : {contentsImageVO.keyword} : insert 실패하였습니다")
                                  
        print("모든 이미지를 MongoDB에 저장했습니다.")