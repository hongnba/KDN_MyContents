from ksubscribe_share.db.dbmodelV2.contentsOrgVO import (
    ContentsOrgVO,
    ContentsOrgCategory,
)
from ksubscribe_share.db.dbmodelV2.commCodeVO import commCodeVO
from ksubscribe_share.db.mongoManager import MongoClient, MongoManager

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
                sucYN=cate[5],
                lastSucYMD=cate[6],
                APIKEY1=cate[7],
                APIKEY2=cate[8],
                COL_METHOD=cate[9],
                COL_HTML_TBODY_TAG=cate[15],
                COL_HTML_TR_TAG=cate[16],
                COL_HTML_TD_TAG=cate[17],
                COL_HTML_TITLE_TAG=cate[18],
                COL_HTML_DATE_N=cate[19],
                COL_HTML_URL_TYPE=cate[20],
                COL_HTML_URL_LINK_N=cate[21],
                COL_HTML_URL_PARAM_N=cate[22],
                COL_HTML_URL_ATTR=cate[23],
                COL_HTML_DETAIL_PAGE_URL=cate[24],
                COL_HTML_URL_PARAM_LISTN_TAG=cate[25],
                COL_HTML_PAGEBAR_TAG=cate[26],
                COL_HTML_NOW_PAGE_INFO1=cate[27],
                COL_HTML_NOW_PAGE_INFO2=cate[28],
                COL_HTML_NEXT_PAGE_TAG=cate[29],
                REG_ID=cate[30],
                REG_DT=cate[31],
                EDIT_ID=cate[32],
                EDIT_DT=cate[32],
            )
        )

    doc = ContentsOrgVO(
        orgId=org[0],
        orgName=org[1],
        orgDesc=org[2],
        orgURL=org[3],
        orgCIPath=org[4],
        kdccCIURL=org[5],
        orgCIWidth=org[6],
        orgCIHeight=org[7],
        orgKeywordList=[org[9], org[10], org[11]],
        regId=org[13],
        regDt=org[12],
        editDt=org[14],
        editId=org[15],
        categoryList=category_id_list,
    ).insert_one()

conn.close()
