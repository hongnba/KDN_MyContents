from bson import ObjectId
from typing import List
import datetime

from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from typing import TypeVar, Type, Dict
T = TypeVar("T", bound="BaseModel")  # BaseModel에 바인딩된 타입 변수


class ContentsOrgCategory(BaseModel):
    def __init__(
        self,
        orgId: str = None,
        cateId: str = None,
        cateName: str = None,
        cateDesc: str = None,
        collectUrlInfo: str = None,
        pageUrlInfo: str = None,
        keywords: List[str] = None,
        sucYN : str = None,
        lastSucYMD : str = None,
        lastTitle : str = None,
        APIKEY1 : str = None,
        APIKEY2 : str = None,
        COL_METHOD : str = None,
        COL_HTML_TBODY_TAG : str = None,
        COL_HTML_TR_TAG : str = None,
        COL_HTML_TD_TAG : str = None,
        COL_HTML_TITLE_TAG : str = None,
        COL_HTML_DATE_N : str = None,
        COL_HTML_URL_TYPE : str = None,
        COL_HTML_URL_LINK_N : str = None,
        COL_HTML_URL_PARAM_N : str = None,
        COL_HTML_URL_ATTR : str = None,
        COL_HTML_DETAIL_PAGE_URL : str = None,
        COL_HTML_URL_PARAM_LISTN_TAG : str = None,
        COL_HTML_PAGEBAR_TAG : str = None,
        COL_HTML_NOW_PAGE_INFO1 : str = None,
        COL_HTML_NOW_PAGE_INFO2 : str = None,
        COL_HTML_NEXT_PAGE_TAG : str = None,
        REG_ID : str = None,
        REG_DT : datetime = None,
        EDIT_ID : str = None,
        EDIT_DT : datetime = None,       
        collectMethod:str=None,   
        tagAttr:str=None,
        tagAttrValue:str=None,
        tagElement:str=None,
        subscriberIds: List[str] = None
        
    ):
        self.orgId = orgId
        self.cateId = cateId
        self.cateName = cateName
        self.cateDesc = cateDesc
        self.collectUrlInfo = collectUrlInfo
        self.pageUrlInfo = pageUrlInfo
        self.keywords = keywords
        self.sucYN = sucYN
        self.lastSucYMD = lastSucYMD
        self.lastTitle = lastTitle
        self.APIKEY1 = APIKEY1
        self.APIKEY2 = APIKEY2
        self.COL_METHOD = COL_METHOD
        self.COL_HTML_TBODY_TAG = COL_HTML_TBODY_TAG
        self.COL_HTML_TR_TAG = COL_HTML_TR_TAG
        self.COL_HTML_TD_TAG = COL_HTML_TD_TAG
        self.COL_HTML_TITLE_TAG = COL_HTML_TITLE_TAG
        self.COL_HTML_DATE_N = COL_HTML_DATE_N
        self.COL_HTML_URL_TYPE = COL_HTML_URL_TYPE
        self.COL_HTML_URL_LINK_N = COL_HTML_URL_LINK_N
        self.COL_HTML_URL_PARAM_N = COL_HTML_URL_PARAM_N
        self.COL_HTML_URL_ATTR = COL_HTML_URL_ATTR
        self.COL_HTML_DETAIL_PAGE_URL = COL_HTML_DETAIL_PAGE_URL
        self.COL_HTML_URL_PARAM_LISTN_TAG = COL_HTML_URL_PARAM_LISTN_TAG
        self.COL_HTML_PAGEBAR_TAG = COL_HTML_PAGEBAR_TAG
        self.COL_HTML_NOW_PAGE_INFO1 = COL_HTML_NOW_PAGE_INFO1
        self.COL_HTML_NOW_PAGE_INFO2 = COL_HTML_NOW_PAGE_INFO2
        self.COL_HTML_NEXT_PAGE_TAG = COL_HTML_NEXT_PAGE_TAG
        self.REG_ID = REG_ID
        self.REG_DT = REG_DT
        self.EDIT_ID = EDIT_ID
        self.EDIT_DT = EDIT_DT     
        self.collectMethod = collectMethod
        self.tagAttr = tagAttr
        self.tagAttrValue = tagAttrValue
        self.tagElement = tagElement
        self.subscriberIds = subscriberIds
        
class ContentsOrgVO(BaseMongoDocument):

    collectionName = "contents_org"

    def __init__(
        self,
        orgId: str = None,
        orgName: str = None,
        orgDesc: str = None,
        orgURL: str = None,
        orgCIPath: str = None,
        kdccCIURL: str = None,
        orgCIWidth: str = None,
        orgCIHeight: str = None,
        orgCISmallYN:str = None,
        regDt: datetime = None,
        regId: str = None,
        editDt: datetime = None,
        editId: str = None,
        orgKeywordList: List[str] = None,
        categoryList: List[ContentsOrgCategory] = None,
        subscriberIds: List[str] = None,
        orgNameSynonymList: List[str] = None,
        _id: ObjectId = None,
    ):

        super().__init__(_id)  # BaseDocument의 생성자를 호출

        self.orgId = orgId
        self.orgName = orgName
        self.orgDesc = orgDesc
        self.orgURL = orgURL
        self.orgCIPath = orgCIPath
        self.kdccCIURL = kdccCIURL
        self.orgCIWidth = orgCIWidth
        self.orgCIHeight = orgCIHeight
        self.orgCISmallYN = orgCISmallYN
        self.regDt = regDt
        self.regId = regId
        self.editDt = editDt
        self.editId = editId
        self.orgKeywordList = orgKeywordList if orgKeywordList is not None else []
        self.categoryList = categoryList if categoryList is not None else []
        self.subscriberIds = subscriberIds if subscriberIds is not None else []
        self.orgNameSynonymList = orgNameSynonymList if orgNameSynonymList is not None else []
        
        
    def to_mongo(self):
        """클래스를 MongoDB 문서 형식으로 변환"""
        # 상위 클래스의 to_mongo 호출
        mongo_data = super().to_mongo()

        # 사용자 정의 객체를 변환
        if self.categoryList:
            mongo_data["categoryList"] = [item.to_mongo() for item in self.categoryList]

        return mongo_data
    
    @classmethod
    def from_mongo(cls: Type[T], mongo_data: Dict) -> T:
        """
        MongoDB 문서 데이터를 Python 객체로 변환
        """
        # 상위 클래스의 from_mongo 호출
        instance = super().from_mongo(mongo_data)

        # 요청 카테고리 변환
        instance.categoryList = [
            ContentsOrgCategory.from_mongo(category)  # OrgCategory의 from_mongo 호출
            for category in mongo_data.get("categoryList", [])
        ]

        return instance
