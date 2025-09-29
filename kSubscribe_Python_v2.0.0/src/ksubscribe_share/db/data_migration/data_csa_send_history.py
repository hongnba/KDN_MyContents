import os
from ksubscribe_share.db.dbmodelV2.contentsSendHistoryVO import ContentsSendHistoryVO
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO
from ksubscribe_share.db.mongoManager import MongoClient, MongoManager
import mariadb
from ksubscribe_share.db.data_migration.mariadb_manager import MariaDBManager
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.memberService import MemberService
from ksubscribe_share.db.service.predefineKeywordService import PredefineKeywordService
from ksubscribe_share.db.service.baseQueryService import BaseQueryService
from ksubscribe_share.db.service.contentsService import ContentsService


class data_csa_send_history():
    """
    data_csa_send_history 테이블을 처리하는 클래스 
    - [고려사항] predefine_keyword, member, contents를 먼저 넣아야 함.
    - [고려사항] contents·v1ContentsIdx에 맞는 id를 찾아서 넣어야 함. 
    - INQCNT는 넣지 못함 
    """
    commonService = CommCodeService()
    memberService = MemberService()
    predefineKeywordService = PredefineKeywordService()
    contentsService = ContentsService()
    
    def __init__(self):
        pass
    
    def moveToMongo(self):

        # MariaDB 연결 및 리소스 관리
        with MariaDBManager().get_connection() as conn:
            with conn.cursor() as cursor:
                # SQL 쿼리
                query = """
                SELECT 
                    mber_id,
                    send_dt,
                    GROUP_CONCAT(CONTENTS_IDX) AS c_idx_list,
                    GROUP_CONCAT(MATCH_KEYWORD1) AS key1_list,
                    GROUP_CONCAT(MATCH_KEYWORD2) AS key2_list,
                    GROUP_CONCAT(MATCH_KEYWORD3) AS key3_list
                FROM 
                    csa_send_history
                GROUP BY 
                    mber_id, send_dt;
                """                
                cursor.execute(query)        
                result = cursor.fetchall()
        
            for doc in result:
                mber_id = doc[0]
                send_dt = doc[1]
                c_idx_list = doc[2]
                key1_list = doc[3]
                key2_list = doc[4]
                key3_list = doc[5]

                contentsSendHistoryVO = ContentsSendHistoryVO()
                contentsSendHistoryVO.mberId = mber_id
                contentsSendHistoryVO.sendDt = send_dt
                contentsSendHistoryVO.regDt = send_dt

                #키워드 ##########################################   
                merged_keywords = []
                if key1_list is not None: 
                    merged_keywords.extend(key1_list.split(","))
                    if "ALL" in key1_list:
                        merged_keywords.extend(self.keyword_list)

                if key2_list is not None: 
                    merged_keywords.extend(key2_list.split(","))
                    if "ALL" in key2_list:
                        merged_keywords.extend(self.keyword_list)

                if key3_list is not None: 
                    merged_keywords.extend(key3_list.split(","))
                    if "ALL" in key3_list:
                        merged_keywords.extend(self.keyword_list)

                merged_keywords = sorted(set(merged_keywords))      

                if merged_keywords is not None and len(merged_keywords) > 0:
                    merged_keywords =  [item for item in merged_keywords if item != "ALL"]
                    
                contentsSendHistoryVO.keywords = merged_keywords

                #전송컨텐츠 정보 ##################################
                contents_idx_list = []
                if c_idx_list is not None: 
                    contents_idx_list.extend(c_idx_list.split(","))

                contents_ids = []
                for c_idx in contents_idx_list:
                    c_int = int(c_idx)
                    contentsId:str =  self.contentsService.findContentsByv1ContentsIdx(c_int)
                    if contentsId is not None:
                        contents_ids.append(contentsId)
                
                contentsSendHistoryVO.mergedSendIds = contents_ids

                memberVO = self.memberService.getMember(mber_id)                
                if(memberVO.v1INFO_RECV_CLSF == "E0001") : 
                    #이메일 id이랑, mergedid에 넣기 
                    contentsSendHistoryVO.emailSendIds = contents_ids
                elif(memberVO.v1INFO_RECV_CLSF == "E0002") : 
                    #카카오톡 id이랑, mergedid에 넣기 
                    contentsSendHistoryVO.kakaoSendIds = contents_ids
                elif(memberVO.v1INFO_RECV_CLSF == "E0003") : 
                    #텔레그램 id이랑, mergedid에 넣기 
                    contentsSendHistoryVO.telegramSendIds = contents_ids
                                
                result = BaseQueryService.insert_one(contentsSendHistoryVO)
                if result.inserted_id: 
                    print(f"{contentsSendHistoryVO.collectionName} : {contentsSendHistoryVO.mberId} {contentsSendHistoryVO.sendDt} : insert 되었습니다.")
                else:
                    print(f"{contentsSendHistoryVO.collectionName} : {contentsSendHistoryVO.mberId} {contentsSendHistoryVO.sendDt} : insert 실패하였습니다")
                        
                            
                
    def merge_and_deduplicate_keys(*key_lists):
        """
        여러 쉼표로 구분된 문자열 리스트를 병합하고 중복을 제거합니다.
        Args:
            *key_lists (str): 쉼표로 구분된 문자열 리스트들.

        Returns:
            List[str]: 중복이 제거되고 정렬된 키 리스트.
        """
        if key_lists is None:
            return 
        
        merged_keys = []
        for key_list in key_lists:
            merged_keys.extend(key_list.split(","))
        return sorted(set(merged_keys))

    def remove_all_occurrences(lst: list, value: str) -> list:
        """
        리스트에서 특정 값을 모두 제거합니다.
        
        Args:
            lst (list): 원본 리스트.
            value (str): 제거할 값.
        
        Returns:
            list: 특정 값이 제거된 리스트.
        """
        if lst is None:
            return 
        
        return [item for item in lst if item != value]

     
    keyword_dic = {
        "1" : "데이터",
        "2" : "AI",
        "3" : "플랫폼",
        "4" : "디지털",
        "5" : "반도체",
        "6" : "에너지",
        "7" : "정보보호",
        "8" : "전력",
    }      
    keyword_list=["데이터","AI","플랫폼","디지털","반도체","에너지","정보보호","전력"]          
