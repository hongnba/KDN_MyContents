from bson import ObjectId
from ksubscribe_share.db.mongoManager import MongoManager
from pymongo import MongoClient
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument
from ksubscribe_share.db.dbmodel.newsMeta import NewsMeta
from ksubscribe_share.db.dbmodel.newsContents import NewsContents
from ksubscribe_share.db.dbmodelV2.errorInfo import ErrorInfo
import datetime


class News(BaseMongoDocument):

    collectionName = "news"

    def __init__(
        self,
        title: str,
        organization: str,
        category: str,
        originallink: str,
        link: str,
        pubDate: str,
        look: int,
        good: int,
        bad: int,
        modificationTime: datetime,
        flag: bool = False,
        newsContents: NewsContents = None,
        newsMeta: NewsMeta = None,
        error: ErrorInfo = None,
        _id: ObjectId = None,
    ):

        super().__init__(_id)  # BaseDocument의 생성자를 호출
        self.title = title
        # self.description = description
        self.organization = organization
        self.category = category
        self.originallink = originallink
        self.link = link
        self.flag = flag
        self.newsContents = newsContents
        self.newsMeta = newsMeta
        self.error = error
        self.look = look
        self.good = good
        self.bad = bad
        self.pubDate = pubDate
        self.modificationTime = modificationTime

    @classmethod
    def from_mongo(cls, document):
        """MongoDB 문서를 클래스로 변환"""

        newsMeta_data = document.get("newsMeta", {})
        newsMeta = NewsMeta.from_mongo(newsMeta_data) if newsMeta_data else None

        newsContents_data = document.get("newsContents", {})
        newsContents = (
            NewsContents.from_mongo(newsContents_data) if newsContents_data else None
        )

        error_data = document.get("error", {})
        error = ErrorInfo.from_mongo(error_data) if error_data else None

        return cls(
            _id=document.get("_id"),
            title=document.get("title"),
            # description=document.get('description'),
            organization=document.get("organization"),
            category=document.get("category"),
            originallink=document.get("originallink"),
            link=document.get("link"),
            flag=document.get("flag"),
            newsContents=newsContents,  # fullContent 추가
            newsMeta=newsMeta,
            error=error,
            look=document.get("look"),
            good=document.get("good"),
            bad=document.get("bad"),
            pubDate=document.get("pubDate"),
            modificationTime=document.get("modificationTime"),
        )

    def to_mongo(self):
        """클래스를 MongoDB 문서 형식으로 변환"""
        return {
            # "_id": self._id,
            "title": self.title,
            # "description": self.description,
            "organization": self.organization,
            "category": self.category,
            "originallink": self.originallink,
            "link": self.link,
            "flag": self.flag,
            "newsContents": (
                self.newsContents.to_mongo() if self.newsContents else None
            ),  # fullContent 추가
            "newsMeta": self.newsMeta.to_mongo() if self.newsMeta else None,
            "error": self.error.to_mongo() if self.error else None,
            "look": self.look,
            "good": self.good,
            "bad": self.bad,
            "pubDate": self.pubDate,
            "modificationTime": self.category,
        }

    @classmethod
    def find_all(cls):
        """지원 안함"""
        list_result = []
        return list_result

    def __repr__(self):
        return f"User(_id={self._id}, title={self.title}, originallink={self.originallink}, link={self.link}, description={self.description}, pubDate={self.pubDate}, newsMeta={self.newsMeta}, error={self.error}, look={self.look}, modificationTime={self.modificationTime})"

    # return f"User(_id={self._id}, title={self.title}, organization={self.organization}, category={self.category}, originallink={self.originallink}, link={self.link},  flag={self.flag}, newsContents={self.newsContents},  newsMeta={self.newsMeta}, look={self.look}, pubDate={self.pubDate}, modificationTime={self.modificationTime})"
