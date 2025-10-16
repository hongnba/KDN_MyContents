
from bson import ObjectId
import datetime
from typing import List

import datetime

from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO, ContentsOrgCategory
from ksubscribe_share.db.dbmodelV2.contentsCollectHistoryVO import ContentsCollectDetail, ContentsCollect, ContentsCollectHistoryVO
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
from ksubscribe_share.db.mongoManager import MongoManager
import mariadb


#컨텐츠 수집 이력 
class MariaDBManager():


    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MariaDBManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        pass
    
    def get_connection(self):
        import ksubscribe_share.config as Conf
        conn = mariadb.connect(
            user=Conf.MARIADB_USER, 
            password=Conf.MARIADB_PASSWORD, 
            host=Conf.MARIADB_HOST, 
            port=Conf.MARIADB_PORT, 
            database=Conf.MARIADB_DATABASE
        )
        return conn        
    
    def get_3waysoft_connection(self):
        conn = mariadb.connect(
            user="3way", password="3waysoft", host="192.168.1.200", port=3306, database="cds"
        )
        return conn            
    
    
        
        
        
        


    
    
    