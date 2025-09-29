 
from bson import ObjectId
import datetime
from typing import List

import datetime
from pymongo.operations import UpdateOne

from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel 
from ksubscribe_share.db.dbmodelV2.predefineKeywordVO import PredefineKeywordVO
from ksubscribe_share.db.mongoManager import MongoManager
#컨텐츠 수집 이력 
class PredefineKeywordRelationService():
    
    mongoManager = MongoManager()           # MongoManager 싱글톤 인스턴스를 사용
    collectionName = "predefine_keyword"
        
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(PredefineKeywordRelationService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        pass 

   
    def process_keyword_relations(self, relation_keywords: List[str], relation_type: int):
        """
        Process keyword relations: create pairs, update count in MongoDB.

        Args:
            relation_keywords (List[str]): List of keywords.
            relation_type (int): Type of relation (0 for Subscribe, 1 for Unsubscribe).
        """
        # Generate keyword pairs
        keyword_pairs = [
            (relation_keywords[i], relation_keywords[j])
            for i in range(len(relation_keywords))
            for j in range(i + 1, len(relation_keywords))
        ]

        collection = self.mongoManager.getCollection(self.collectionName)
    
        # Prepare bulk operations
        operations = []
        for keyword1, keyword2 in keyword_pairs:
            # Ensure lexicographical order to avoid duplicate pairs
            if keyword1 > keyword2:
                keyword1, keyword2 = keyword2, keyword1

            # MongoDB upsert operation
            operations.append(
                UpdateOne(
                    {"keyword1": keyword1, "keyword2": keyword2, "type": relation_type},
                    {"$inc": {"count": 1}},
                    upsert=True
                )
            )

        # Execute bulk operations
        if operations:
            result = collection.bulk_write(operations)
            print(f"Matched: {result.matched_count}, Modified: {result.modified_count}, Upserts: {result.upserted_count}")

      
  
    
    