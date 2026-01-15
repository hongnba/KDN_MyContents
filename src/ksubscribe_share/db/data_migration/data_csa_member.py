import os
import mariadb
from typing import List
from ksubscribe_share.db.dbmodelV2.memberVO import MemberVO
from ksubscribe_share.db.dbmodelV2.predefineKeywordVO import PredefineKeywordVO
from ksubscribe_share.db.mongoManager import MongoClient, MongoManager
from ksubscribe_share.db.data_migration.mariadb_manager import MariaDBManager
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.memberService import MemberService
from ksubscribe_share.db.service.predefineKeywordService import PredefineKeywordService
from ksubscribe_share.db.service.memberActionService import MemberActionService
from ksubscribe_share.db.service.baseQueryService import BaseQueryService
from ksubscribe_share.db.dbmodelV2.dbEnums import SignMethodEnum

#csa_member(maria) ---> member_account(mongo) 테이블 
#col_user_subs_master --> member_account(mongo) 테이블에 반영 

class data_csa_member():

    commonService = CommCodeService()
    memberService = MemberService()
    predefineKeywordService = PredefineKeywordService()
    memberActionService = MemberActionService()
    
    def __init__(self):
        pass
    
    def checkNotExistUserInMongo(self): 

        with MariaDBManager().get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("select * from csa_member")        
            result = cursor.fetchall()
        
        count = 0 
        for doc in result:
            SEQ = doc[0]
            HASH_SEQ = doc[1]
            MBER_ID = doc[2]
            
            existVO:MemberVO  = MemberService.getMember(MBER_ID)
            
            if existVO is None:
                
                print(f"{MBER_ID} : 계정이 Mongodb에 존재하지 않습니다. 조치하시기 바랍니다. ")
                continue
            
            # MBER_PW = doc[3]
            # MBER_TYPE = doc[4]
            # ORG_NM = doc[5]
            # ORG_DEPT_NM = doc[6]
            # MBER_STTUS = doc[7]
            # APRV_DT = doc[8]
            # DORMAN_YN = doc[9]
            # MBER_NM = doc[10]
            # MBER_TELNO = doc[11]
            # MBER_EMAIL_ADRES = doc[12]
            # TELE_USER_NM = doc[13]
            # TELE_CHANNEL_NM = doc[14]
            # PER_INFO = doc[15]
            # TELE_CHAT_ID = doc[16]
            # INFO_RECV_CLSF = doc[17]
            # REC_LOG_DT = doc[18]
            # PW_CHG_DT = doc[19]
            # PW_ERR_CNT = doc[20]
            # INTR_KEYWORD1 = doc[21]
            # INTR_KEYWORD2 = doc[22]
            # INTR_KEYWORD3 = doc[23]
            # MEM_INFO_DEL_YN = doc[24]
            # AUTHORITY = doc[25]
            # JOIN_DT = doc[26]
            # EDIT_DT = doc[27]
            # DENYREAS = doc[28]
            # AGE_RANGE = doc[29]
            # OCCUPATION = doc[30]
            # GENDER = doc[31] 
            
            # # 필드 초기화
            # member = MemberVO()
            # member.hashSeq = HASH_SEQ
            # member.mberId = MBER_ID
            # member.mberPw = MBER_PW
            # member.mberType = MBER_TYPE
            # member.mberAuthority = AUTHORITY
            # member.mberName = MBER_NM
            # member.mberTelno = MBER_TELNO
            # member.mberEmail = MBER_EMAIL_ADRES
            # member.orgName = ORG_NM            
            # member.orgId = self.commonService.get_orgId_byOrgName(member.orgName)
            # member.orgEmail = ""
            # member.orgDeptNm = ORG_DEPT_NM
            # member.mberSttus = MBER_STTUS
            # member.aprvDt = APRV_DT 
            # member.denyReason = DENYREAS 
            # member.dormanYn = DORMAN_YN
            
            # if INFO_RECV_CLSF.strip() == "E0001":                             
            #     member.emailReceiveYN = "Y"
            #     member.kakaoReceiveYN = "N"
            #     member.teleReceiveYN = "N"
            # elif INFO_RECV_CLSF.strip() == "E0002":                             
            #     member.emailReceiveYN = "N"
            #     member.kakaoReceiveYN = "Y"
            #     member.teleReceiveYN = "N"
            # elif INFO_RECV_CLSF.strip() == "E0003":                             
            #     member.emailReceiveYN = "N"
            #     member.kakaoReceiveYN = "N"
            #     member.teleReceiveYN = "Y"
            # else: 
            #     member.emailReceiveYN = "N"
            #     member.kakaoReceiveYN = "N"
            #     member.teleReceiveYN = "N"

            # member.teleUserNm = TELE_USER_NM
            # member.teleChannelNm = TELE_CHANNEL_NM
            # member.teleChatId = TELE_CHAT_ID
            # member.perInfo = PER_INFO
            # member.memberInfoDeleteYN = MEM_INFO_DEL_YN
            
            # if AGE_RANGE:
            #     try:
            #         AGE_RANGE_INT = int(AGE_RANGE.strip())
            #         member.birthYear = AGE_RANGE_INT
            #     except Exception as e:
            #         pass
            # member.occupation = OCCUPATION
            # member.gender = GENDER
            # member.lastSignInDt = REC_LOG_DT
            # member.pwdChangeDt = PW_CHG_DT
            # # Python의 int로 변환
            # if PW_ERR_CNT is not None:
            #     pwdChangeCount = int(PW_ERR_CNT)  # DECIMAL -> int 변환            
            # member.pwdChangeCount = pwdChangeCount
            # member.joinDt = JOIN_DT
            # member.editDt = EDIT_DT
            # # member.kakaoId = ""
            # # member.naverId = ""
            # # member.googleId = ""
            # member.socialRegister = 0 #SignMethodEnum.NORMAL #일반로그인        
            # member.v1Seq = SEQ  
            # member.v1INFO_RECV_CLSF = INFO_RECV_CLSF
            
            # if member.keywordSubscribe is None:
            #     member.keywordSubscribe = []  # 리스트 초기화
                
            # if INTR_KEYWORD1 is not None and INTR_KEYWORD1 != "":                
            #     member.keywordSubscribe.append(INTR_KEYWORD1)
            # if INTR_KEYWORD2 is not None and INTR_KEYWORD2 != "":                
            #     member.keywordSubscribe.append(INTR_KEYWORD2)
            # if INTR_KEYWORD3 is not None and INTR_KEYWORD3 != "":                
            #     member.keywordSubscribe.append(INTR_KEYWORD3)
                         
                          
            # result = BaseQueryService.insert_one(member)
            # if result.inserted_id: 
            #     print(f"{member.collectionName} : {member.mberId} : insert 되었습니다.")
            # else:
            #     print(f"{member.collectionName} : {member.mberId} : insert 실패하였습니다")
                
            #count += 1
            
        #print(f"{member.collectionName} : {count} 건이 insert 되었습니다.")
        
        
        
        pass
    
    def moveToMongo(self):

        with MariaDBManager().get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("select * from csa_member")        
            result = cursor.fetchall()
        
        count = 0 
        for doc in result:
            SEQ = doc[0]
            HASH_SEQ = doc[1]
            MBER_ID = doc[2]
            MBER_PW = doc[3]
            MBER_TYPE = doc[4]
            ORG_NM = doc[5]
            ORG_DEPT_NM = doc[6]
            MBER_STTUS = doc[7]
            APRV_DT = doc[8]
            DORMAN_YN = doc[9]
            MBER_NM = doc[10]
            MBER_TELNO = doc[11]
            MBER_EMAIL_ADRES = doc[12]
            TELE_USER_NM = doc[13]
            TELE_CHANNEL_NM = doc[14]
            PER_INFO = doc[15]
            TELE_CHAT_ID = doc[16]
            INFO_RECV_CLSF = doc[17]
            REC_LOG_DT = doc[18]
            PW_CHG_DT = doc[19]
            PW_ERR_CNT = doc[20]
            INTR_KEYWORD1 = doc[21]
            INTR_KEYWORD2 = doc[22]
            INTR_KEYWORD3 = doc[23]
            MEM_INFO_DEL_YN = doc[24]
            AUTHORITY = doc[25]
            JOIN_DT = doc[26]
            EDIT_DT = doc[27]
            DENYREAS = doc[28]
            AGE_RANGE = doc[29]
            OCCUPATION = doc[30]
            GENDER = doc[31] 
            
            # 필드 초기화
            member = MemberVO()
            member.hashSeq = HASH_SEQ
            member.mberId = MBER_ID
            member.mberPw = MBER_PW
            member.mberType = MBER_TYPE
            member.mberAuthority = AUTHORITY
            member.mberName = MBER_NM
            member.mberTelno = MBER_TELNO
            member.mberEmail = MBER_EMAIL_ADRES
            member.orgName = ORG_NM            
            member.orgId = self.commonService.get_orgId_byOrgName(member.orgName)
            member.orgEmail = ""
            member.orgDeptNm = ORG_DEPT_NM
            member.mberSttus = MBER_STTUS
            member.aprvDt = APRV_DT 
            member.denyReason = DENYREAS 
            member.dormanYn = DORMAN_YN
            
            if INFO_RECV_CLSF.strip() == "E0001":                             
                member.emailReceiveYN = "Y"
                member.kakaoReceiveYN = "N"
                member.teleReceiveYN = "N"
            elif INFO_RECV_CLSF.strip() == "E0002":                             
                member.emailReceiveYN = "N"
                member.kakaoReceiveYN = "Y"
                member.teleReceiveYN = "N"
            elif INFO_RECV_CLSF.strip() == "E0003":                             
                member.emailReceiveYN = "N"
                member.kakaoReceiveYN = "N"
                member.teleReceiveYN = "Y"
            else: 
                member.emailReceiveYN = "N"
                member.kakaoReceiveYN = "N"
                member.teleReceiveYN = "N"

            member.teleUserNm = TELE_USER_NM
            member.teleChannelNm = TELE_CHANNEL_NM
            member.teleChatId = TELE_CHAT_ID
            member.perInfo = PER_INFO
            member.memberInfoDeleteYN = MEM_INFO_DEL_YN
            
            if AGE_RANGE:
                try:
                    AGE_RANGE_INT = int(AGE_RANGE.strip())
                    member.birthYear = AGE_RANGE_INT
                except Exception as e:
                    pass
            member.occupation = OCCUPATION
            member.gender = GENDER
            member.lastSignInDt = REC_LOG_DT
            member.pwdChangeDt = PW_CHG_DT
            # Python의 int로 변환
            if PW_ERR_CNT is not None:
                pwdChangeCount = int(PW_ERR_CNT)  # DECIMAL -> int 변환            
            member.pwdChangeCount = pwdChangeCount
            member.joinDt = JOIN_DT
            member.editDt = EDIT_DT
            # member.kakaoId = ""
            # member.naverId = ""
            # member.googleId = ""
            member.socialRegister = 0 #SignMethodEnum.NORMAL #일반로그인        
            member.v1Seq = SEQ  
            member.v1INFO_RECV_CLSF = INFO_RECV_CLSF
            
            if member.keywordSubscribe is None:
                member.keywordSubscribe = []  # 리스트 초기화
                
            if INTR_KEYWORD1 is not None and INTR_KEYWORD1 != "":                
                member.keywordSubscribe.append(INTR_KEYWORD1)
            if INTR_KEYWORD2 is not None and INTR_KEYWORD2 != "":                
                member.keywordSubscribe.append(INTR_KEYWORD2)
            if INTR_KEYWORD3 is not None and INTR_KEYWORD3 != "":                
                member.keywordSubscribe.append(INTR_KEYWORD3)
                          
            result = BaseQueryService.insert_one(member)
            if result.inserted_id: 
                print(f"{member.collectionName} : {member.mberId} : insert 되었습니다.")
            else:
                print(f"{member.collectionName} : {member.mberId} : insert 실패하였습니다")
                
            count += 1
            
        print(f"{member.collectionName} : {count} 건이 insert 되었습니다.")
        



    def receiveYNToMongo(self):

        with MariaDBManager().get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("select * from csa_member")        
            result = cursor.fetchall()
        
        count = 0 
        for doc in result:
            SEQ = doc[0]
            MBER_ID = doc[2]
            INFO_RECV_CLSF = doc[17]
            
            # 필드 초기화
            member = MemberVO()
            member.mberId = MBER_ID
            
            if INFO_RECV_CLSF.strip() == "E0001":                             
                member.emailReceiveYN = "Y"
                member.kakaoReceiveYN = "N"
                member.teleReceiveYN = "N"
            elif INFO_RECV_CLSF.strip() == "E0002":                             
                member.emailReceiveYN = "N"
                member.kakaoReceiveYN = "Y"
                member.teleReceiveYN = "N"
            elif INFO_RECV_CLSF.strip() == "E0003":                             
                member.emailReceiveYN = "N"
                member.kakaoReceiveYN = "N"
                member.teleReceiveYN = "Y"
            else: 
                member.emailReceiveYN = "N"
                member.kakaoReceiveYN = "N"
                member.teleReceiveYN = "N"

                          
            result = self.memberService.update_receiveYN(member.mberId, member.emailReceiveYN, member.kakaoReceiveYN,member.teleReceiveYN)
                
            count += 1
            
        print(f"{member.collectionName} : {count} 건이 update 되었습니다.")
        

                
                        
            
            

