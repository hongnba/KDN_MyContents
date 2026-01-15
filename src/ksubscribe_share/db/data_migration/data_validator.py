import os
from ksubscribe_share.db.dbmodelV2.commCodeVO import CommCodeVO
from ksubscribe_share.db.dbmodelV2.contentsCollectErrorVO import ContentsCollectErrorVO

from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO
from ksubscribe_share.db.mongoManager import MongoClient, MongoManager
import mariadb
from ksubscribe_share.db.data_migration.mariadb_manager import MariaDBManager
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.service.baseQueryService import BaseQueryService
from ksubscribe_share.db.service.memberService import MemberService
from ksubscribe_share.db.service.contentsService import ContentsService

from ksubscribe_share.db.data_migration.data_cmmn_code import data_cmmn_code
from ksubscribe_share.db.data_migration.data_col_col_contents import data_col_col_contents
from ksubscribe_share.db.data_migration.data_col_daily_error import data_col_daily_error
from ksubscribe_share.db.data_migration.data_col_daily_history import data_col_daily_history
from ksubscribe_share.db.data_migration.data_col_user_subs_master import data_col_user_subs_master
from ksubscribe_share.db.data_migration.data_content_image import data_content_image
from ksubscribe_share.db.data_migration.data_csa_authorinfo import data_csa_authorinfo
from ksubscribe_share.db.data_migration.data_csa_catalog_master import data_csa_catalog_master
from ksubscribe_share.db.data_migration.data_csa_cntn_status import data_csa_cntn_status
from ksubscribe_share.db.data_migration.data_csa_keyword_dic import data_csa_keyword_dic
from ksubscribe_share.db.data_migration.data_csa_member_quote import data_csa_member_quote
from ksubscribe_share.db.data_migration.data_csa_member import data_csa_member
from ksubscribe_share.db.data_migration.data_csa_organization import data_csa_organization
from ksubscribe_share.db.data_migration.data_csa_send_history import data_csa_send_history
from ksubscribe_share.db.data_migration.data_csa_user_keyword_subs import data_csa_user_keyword_subs
from ksubscribe_share.db.data_migration.data_predefine_relation import data_predefine_relation
from ksubscribe_server.analysis.analysis_ollama import AnalysisOllama
from typing import List
from bson import ObjectId  # ObjectId를 사용하려면 추가로 임포트 필요

class data_validator():

    mongoManager = MongoManager()
    
    def __init__(self):
        pass


    #sentiments의 positiveRatio, negativeRatio, neutralRatio가 str 로 들어가는 문제 
    def convert_sentiment_str_to_float(self):
        
        collection = self.mongoManager.getCollection("contents") 
        
        # 특정 _id 필터 추가
        #filter_condition = {"_id": ObjectId('678dddd3b1af9e27f5e1ca73')}  # _id 필터 조건
        #filter_condition = {"url": "http://biz.heraldcorp.com/view.php?ud=202310091726415357898_1"}  # _id 필터 조건
                
        # 모든 문서에서 sentiments 배열 내의 값들을 float로 변환

        # 업데이트 파이프라인
        pipeline = [
            {
                "$set": {
                    "contentsMeta.sentiments": {
                        "$map": {
                            "input": "$contentsMeta.sentiments",
                            "as": "sentiment",
                            "in": {
                                "orgId": "$$sentiment.orgId",
                                "orgName": "$$sentiment.orgName",
                                "positiveRatio": {
                                    "$convert": {
                                        "input": "$$sentiment.positiveRatio",
                                        "to": "double",
                                        "onError": None,
                                        "onNull": None
                                    }
                                },
                                "negativeRatio": {
                                    "$convert": {
                                        "input": "$$sentiment.negativeRatio",
                                        "to": "double",
                                        "onError": None,
                                        "onNull": None
                                    }
                                },
                                "neutralRatio": {
                                    "$convert": {
                                        "input": "$$sentiment.neutralRatio",
                                        "to": "double",
                                        "onError": None,
                                        "onNull": None
                                    }
                                },
                                "reason": "$$sentiment.reason"
                            }
                        }
                    }
                }
            }
        ]
        # 업데이트 수행
        result = collection.update_many({}, pipeline)        
        
        # 결과 출력
        if result.matched_count > 0:
            print(f"contents_collect_error {result.matched_count}개의 문서를 찾았습니다")
        else:
            print("contents_collect_error 조건에 맞는 문서를 찾을 수 없습니다.")
              
        # 결과 출력
        if result.modified_count > 0:
            print(f"contents_collect_error {result.modified_count}개의 문서가 업데이트되었습니다.")
        else:
            print("contents_collect_error 조건에 맞는 문서를 찾을 수 없습니다.")
        
          

    def convert_predKeywords_to_double(self):
        
        collection = self.mongoManager.getCollection("contents") 
        
        try:
            # MongoDB 업데이트 파이프라인
            pipeline = [
                {
                    "$set": {
                        "contentsMeta.predKeywords": {
                            "$map": {
                                "input": {"$objectToArray": "$contentsMeta.predKeywords"},  # 객체를 배열로 변환
                                "as": "keyword",
                                "in": {
                                    "k": "$$keyword.k",  # 키 유지
                                    "v": {
                                        "$convert": {
                                            "input": "$$keyword.v",
                                            "to": "double",
                                            "onError": None,
                                            "onNull": None
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                {
                    "$set": {
                        "contentsMeta.predKeywords": {
                            "$arrayToObject": "$contentsMeta.predKeywords"  # 다시 Dict 형태로 변환
                        }
                    }
                }
            ]

            # 업데이트 수행
            result = collection.update_many({}, pipeline)
            # 특정 URL을 가진 문서 하나만 업데이트
            #url = "https://www.newsfreezone.co.kr/news/articleView.html?idxno=608322"
            #result = collection.update_one({"url": url}, pipeline)

            # 결과 출력
            print(f"🔹 변환된 문서 개수: {result.modified_count}")

        except Exception as e:
            print(f"❌ 변환 중 오류 발생: {e}")
                