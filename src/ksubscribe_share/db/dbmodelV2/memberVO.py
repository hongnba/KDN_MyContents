from bson import ObjectId
from pymongo import MongoClient
import datetime
from typing import List

from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.dbmodelV2.baseDocument import BaseMongoDocument, BaseModel
from ksubscribe_share.db.dbmodel.newsMeta import NewsMeta
from ksubscribe_share.db.dbmodel.newsContents import NewsContents
from ksubscribe_share.db.dbmodelV2.errorInfo import ErrorInfo
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO
from ksubscribe_share.db.dbmodelV2.dbEnums import SignMethodEnum
from typing import TypeVar, Type, Dict
T = TypeVar("T", bound="BaseModel")  # BaseModel에 바인딩된 타입 변수

from Crypto.Cipher import AES
import base64
import ksubscribe_share.config as Conf

# 사용자 계정 정보 클래스 백업 : V2.0.0 에서 만들었던 클래스가 MongoDB 에서 Python 객체로 변환이 안되는 현상이 있음.
# - 접속 IP, 접속일시 정보도 모두 기록


class OrgIdAndCateId(BaseModel):
    def __init__(
        self,
        orgId: str = None,
        cateId: str = None,
        regDt: datetime = None,
        regId: str = None,
        editDt: datetime = None,
        editId: str = None,        
    ):
        self.orgId = orgId
        self.cateId = cateId
        self.regDt = regDt
        self.regId = regId
        self.editDt = editDt
        self.editId = editId        
  

class ContentsOrgID(BaseModel):

    def __init__(
        self,
        orgId: str = None,
        orgName: str = None,
        regDt: datetime = None,
        regId: str = None,
        editDt: datetime = None,
        editId: str = None,        
        categoryList: List[OrgIdAndCateId] = None
    ):

        self.orgId = orgId
        self.orgName = orgName
        self.regDt = regDt
        self.regId = regId
        self.editDt = editDt
        self.editId = editId                
        self.categoryList = categoryList if categoryList is not None else []


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
            OrgIdAndCateId.from_mongo(category)  # OrgCategory의 from_mongo 호출
            for category in mongo_data.get("categoryList", [])
        ]

        return instance


class MemberVO(BaseMongoDocument):

    collectionName = "member_account"
    
    def __init__(
        self,
        hashSeq: str = None,
        mberId: str = None,
        mberPw: str = None,
        mberType: str = None,
        mberAuthority: str = None,
        mberName: str = None,
        mberTelno: str = None,
        mberEmail: str = None,
        orgId: str = None,
        orgName: str = None,
        orgEmail: str = None,
        orgDeptNm: str = None,
        mberSttus: str = None,
        aprvDt:datetime = None,
        denyReason:str = None,
        dormanYn: str = None,
        emailReceiveYN: str = None,
        kakaoReceiveYN: str = None,
        teleReceiveYN: str = None,
        teleUserNm: str = None,
        teleChannelNm: str = None,
        teleChatId: str = None,
        perInfo: str = None,
        memberInfoDeleteYN: str = None,  # 회원정보 삭제 유무. 회원탈태 하면 Y로 설정하고, 5년동안 보존하고 있다가 삭제
        birthYear: int = None,  # 출생년년도
        occupation: str = None,  # 직군
        gender: str = None,  # 성별
        keywordSubscribe: List[str] = None,  # 키워드이름
        contentsOrgSubscribe: List[ContentsOrgID] = None,    #기관정보를 모두 넣지 않고 필요한 것 만 넣는 것으로 함 
        lastSignInDt: datetime = None,
        pwdChangeDt: datetime = None,  # 비밀번호 변경일시
        pwdChangeCount: int = None,  # 비밀번호 변경횟수
        joinDt: datetime = None,
        editDt: datetime = None,
        _id: ObjectId = None,
        kakaoId: str = None,
        naverId: str = None,
        googleId: str = None,
        socialRegister : int = None,     
        v1Seq :str = None,
        v1INFO_RECV_CLSF:str = None   #E0001(메일), E0002(카카오톡), E0003(텔레그램)
    ):

        super().__init__(_id)  # BaseDocument의 생성자를 호출

        # 필드 초기화
        self.hashSeq = hashSeq
        self.mberId = mberId
        self.mberPw = mberPw
        self.mberType = mberType
        self.mberAuthority = mberAuthority
        self.mberName = mberName
        self.mberTelno = mberTelno
        self.mberEmail = mberEmail
        self.orgId = orgId
        self.orgName = orgName
        self.orgEmail = orgEmail
        self.orgDeptNm = orgDeptNm
        self.mberSttus = mberSttus
        self.aprvDt = aprvDt
        self.denyReason = denyReason
        self.dormanYn = dormanYn
        self.emailReceiveYN = emailReceiveYN
        self.kakaoReceiveYN = kakaoReceiveYN
        self.teleReceiveYN = teleReceiveYN
        self.teleUserNm = teleUserNm
        self.teleChannelNm = teleChannelNm
        self.teleChatId = teleChatId
        self.perInfo = perInfo
        self.memberInfoDeleteYN = memberInfoDeleteYN
        self.birthYear = birthYear
        self.occupation = occupation
        self.gender = gender
        self.keywordSubscribe = keywordSubscribe if keywordSubscribe is not None else []
        self.contentsOrgSubscribe = (
            contentsOrgSubscribe if contentsOrgSubscribe is not None else []
        )
        self.lastSignInDt = lastSignInDt
        self.pwdChangeDt = pwdChangeDt
        self.pwdChangeCount = pwdChangeCount
        self.joinDt = joinDt
        self.editDt = editDt
        self.kakaoId = kakaoId
        self.naverId = naverId
        self.googleId = googleId
        self.socialRegister = socialRegister
        self.v1Seq = v1Seq
        self.v1INFO_RECV_CLSF = v1INFO_RECV_CLSF
        
    def to_mongo(self):
        """클래스를 MongoDB 문서 형식으로 변환"""
        # 상위 클래스의 to_mongo 호출
        mongo_data = super().to_mongo()

        # 사용자 정의 객체를 변환
        if self.contentsOrgSubscribe:
            mongo_data["contentsOrgSubscribe"] = [item.to_mongo() for item in self.contentsOrgSubscribe]

        return mongo_data
    
    @classmethod
    def from_mongo(cls: Type[T], mongo_data: Dict) -> T:
        """
        MongoDB 문서 데이터를 Python 객체로 변환
        """
        # 상위 클래스의 from_mongo 호출
        instance = super().from_mongo(mongo_data)

        # 요청 카테고리 변환
        instance.contentsOrgSubscribe = [
            ContentsOrgID.from_mongo(category)  # OrgCategory의 from_mongo 호출
            for category in mongo_data.get("contentsOrgSubscribe", [])
        ]

        return instance
    
    def get_decrypt_email(self):
        return self.decrypt(self.mberEmail)
    
    def get_decrypt_mberTelno(self):
        return self.decrypt(self.mberTelno)
    
    def get_key_bytes(self, key: str) -> bytes:
        """
        MariaDB와 동일한 키 처리 방식.
        키가 짧으면 0x00으로 패딩, 길면 16바이트로 자름.
        """
        AES_KEY_LENGTH = 16  # AES-128에서 사용하는 키 길이
        key_bytes = key.encode('utf-8')

        if len(key_bytes) == AES_KEY_LENGTH:
            return key_bytes
        elif len(key_bytes) < AES_KEY_LENGTH:
            return key_bytes.ljust(AES_KEY_LENGTH, b'\x00')  # 오른쪽에 0x00으로 패딩
        else:
            return key_bytes[:AES_KEY_LENGTH]  # 16바이트로 자름

    def encrypt(self, value: str) -> str:
        """
        AES 암호화 (ECB 모드, PKCS5Padding과 동일한 PKCS7 사용).
        결과를 HEX 문자열로 반환.
        """
        try:
            key = self.get_key_bytes(Conf.SECRET_KEY)
            cipher = AES.new(key, AES.MODE_ECB)  # ECB 모드 사용
            padded_value = self.pad(value.encode('utf-8'))  # PKCS7 Padding
            encrypted_bytes = cipher.encrypt(padded_value)
            return encrypted_bytes.hex().upper()  # HEX 대문자로 반환
        except Exception as e:
            raise RuntimeError(f"Error while encrypting: {str(e)}")

    def decrypt(self, encrypted_value: str) -> str:
        """
        AES 복호화 (ECB 모드, PKCS5Padding과 동일한 PKCS7 사용).
        """
        try:
            key = self.get_key_bytes(Conf.SECRET_KEY)
            cipher = AES.new(key, AES.MODE_ECB)  # ECB 모드 사용
            encrypted_bytes = bytes.fromhex(encrypted_value)  # HEX를 바이트 배열로 변환
            decrypted_bytes = cipher.decrypt(encrypted_bytes)
            return self.unpad(decrypted_bytes).decode('utf-8')  # 패딩 제거 후 UTF-8 디코딩
        except Exception as e:
            raise RuntimeError(f"Error while decrypting: {str(e)}")

    def pad(self, data: bytes) -> bytes:
        """
        PKCS7 Padding: 데이터 길이를 AES 블록 크기(16)로 맞춤.
        """
        block_size = AES.block_size
        pad_len = block_size - len(data) % block_size
        return data + bytes([pad_len] * pad_len)

    def unpad(self, data: bytes) -> bytes:
        """
        PKCS7 Padding 제거.
        """
        pad_len = data[-1]
        return data[:-pad_len]
