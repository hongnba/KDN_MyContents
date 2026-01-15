from ksubscribe_share.db.dbmodelV2.contentsOrgVO import (
    ContentsOrgVO,
    ContentsOrgCategory,
)
from ksubscribe_share.db.dbmodelV2.commCodeVO import commCodeVO
from ksubscribe_share.db.mongoManager import MongoClient, MongoManager
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgCategory

# 1. 기관 데이터 가져오기
import mariadb

coll = MongoManager().getCollection("contents_org")
coll.delete_many({})

conn = mariadb.connect(
    user="3way", password="3waysoft", host="192.168.1.200", port=3306, database="cds"
)
cursor = conn.cursor()

cursor.execute("select * from csa_organization_master")
result = cursor.fetchall()
docs = []
for org in result:
    # print(org)
    org_code = org[0]
    cursor.execute(f"select * from csa_organization_detail where ORG_ID='{org_code}'")
    categories = cursor.fetchall()
    category_id_list = []

    for cate in categories:
        cate_id = cate[2]
        cursor.execute(f"select * from cmmncode where CODE='{cate_id}'")
        cmmn = cursor.fetchone()
        category_id_list.append(
            ContentsOrgCategory(
                cateId=cate[2],
                cateName=cmmn[2],
                cateDesc="",
                collectUrlInfo=cate[3],
                pageUrlInfo=cate[4],
                keywords=[
                    cate[10],
                    cate[11],
                    cate[12],
                    cate[13],
                    cate[14],
                ],
            )
        )

    doc = ContentsOrgVO(
        orgId=org[0],
        orgName=org[1],
        orgDesc=org[2],
        orgCIPath=org[4],
        kdccCIURL=org[5],
        orgCIWidth=org[6],
        orgCIHeight=org[7],
        orgKeywordList=[org[9], org[10], org[11]],
        regId=org[13],
        regDt=org[12],
        editDt=org[14],
        editId=org[15],
        contentsOrgCategoryList=category_id_list,
    ).insert_one()

conn.close()
