import base64
from datetime import datetime, date
import json
from typing import Any, Dict, Optional
import zlib
import requests
import urllib
from urllib.parse import quote, urlencode

from docker_talk_send.model.SendResult import SendResult
from docker_talk_send.model.SendModel import SendModel
from ksubscribe_share.db.dbmodelV2.memberVO import MemberVO
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO

from Crypto.Cipher import AES
import base64
import ksubscribe_share.config as Conf
from ksubscribe_share.logger import Logger
import ksubscribe_share.config as Conf

class KakaoSendModel:
    def __init__(self, user_id: str, password: str, sender_key: str, sender_number: str):
        self.initialized = False
        self.send_type = "Kakao"
        
        # api 호출 url 들
        self.auth_token_url = "https://api.bizppurio.com/v1/token"
        self.message_url = "https://api.bizppurio.com/v3/message"
        self.template_url = "https://api.bizppurio.com/v3/kakao/template/list"
        self.button_url = "http://mycontents.kdn.com"
        
        self.user_id = user_id
        self.password = password
        self.sender_key = sender_key
        self.sender_number = sender_number
        
        self.base_url = Conf.CONTENTS_BASE_URL
        logger = Logger()
        self.docker_send_logger = logger.setup_logger(logger.docker_talk_send_logger_name)
        
        self.access_token = ""
        self.token_expired = ""
        
    def initialize(self):
        try:
            # 알리고 kakao api 는 토큰을 받아야 함.
            self.initialized = True
        except Exception as ex:
            print(ex)
            self.initialized = False
    
    def ALIMTALK_TEMPLATE(self, alimtalk_variables: dict):
        
        alimtalk_template = """
            한전 KDN 컨텐츠 구독 서비스\r\n
            \r\n
            #{회사명} 의 구독 컨텐츠 전송\r\n
            \r\n
            안녕하세요. #{고객명}님!\r\n
            #{회사명} 입니다.\r\n
            \r\n
            한전KDN 콘텐츠 구독 서비스 #{금일날짜} 콘텐츠를 송부드립니다. (총 #{전송개수}건) 요약된 콘텐츠입니다. 이외 콘텐츠는 포털에서 확인 바랍니다.\r\n
            \r\n
            ■ #{기관명1}\r\n
            ☞ #{컨텐츠1_제목}\r\n
            #{컨텐츠1_링크}\r\n
            \r\n
            ■ #{기관명2}\r\n
            ☞ #{컨텐츠2_제목}\r\n
            #{컨텐츠2_링크}\r\n
            \r\n
            ■ #{기관명3}\r\n
            ☞ #{컨텐츠3_제목}\r\n
            #{컨텐츠3_링크}\r\n
            \r\n
            ■ #{기관명4}\r\n
            ☞ #{컨텐츠4_제목}\r\n
            #{컨텐츠4_링크}\r\n
            \r\n
            ■ #{기관명5}\r\n
            ☞ #{컨텐츠5_제목}\r\n
            #{컨텐츠5_링크}\r\n
            \r\n
            ■ #{기관명6}\r\n
            ☞ #{컨텐츠6_제목}\r\n
            #{컨텐츠6_링크}\r\n
            \r\n
            ■ #{기관명7}\r\n
            ☞ #{컨텐츠7_제목}\r\n
            #{컨텐츠7_링크}\r\n
            \r\n
            ■ #{기관명8}\r\n
            ☞ #{컨텐츠8_제목}\r\n
            #{컨텐츠8_링크}\r\n
        """
        
        message = alimtalk_template.format(**alimtalk_variables)
        return message
        
    def ALIMTALK_TEMPLATE(self, organization_name: str, user_name: str, send_date: str, send_count: str,
                          org1_name: str, content1_title: str, content1_url: str,
                          org2_name: str, content2_title: str, content2_url: str,
                          org3_name: str, content3_title: str, content3_url: str,
                          org4_name: str, content4_title: str, content4_url: str,
                          org5_name: str, content5_title: str, content5_url: str,
                          org6_name: str, content6_title: str, content6_url: str,
                          org7_name: str, content7_title: str, content7_url: str,
                          org8_name: str, content8_title: str, content8_url: str):
        
        alimtalk_template = """
한전 KDN 컨텐츠 구독 서비스\r\n
\r\n
#{회사명} 의 구독 컨텐츠 전송\r\n
\r\n
안녕하세요. #{고객명}님!\r\n
#{회사명} 입니다.\r\n
\r\n
한전KDN 콘텐츠 구독 서비스 #{금일날짜} 콘텐츠를 송부드립니다. (총 #{전송개수}건) 요약된 콘텐츠입니다. 이외 콘텐츠는 포털에서 확인 바랍니다.\r\n
\r\n
■ #{기관명1}\r\n
☞ #{컨텐츠1_제목}\r\n
#{컨텐츠1_링크}\r\n
\r\n
■ #{기관명2}\r\n
☞ #{컨텐츠2_제목}\r\n
#{컨텐츠2_링크}\r\n
\r\n
■ #{기관명3}\r\n
☞ #{컨텐츠3_제목}\r\n
#{컨텐츠3_링크}\r\n
\r\n
■ #{기관명4}\r\n
☞ #{컨텐츠4_제목}\r\n
#{컨텐츠4_링크}\r\n
\r\n
■ #{기관명5}\r\n
☞ #{컨텐츠5_제목}\r\n
#{컨텐츠5_링크}\r\n
\r\n
■ #{기관명6}\r\n
☞ #{컨텐츠6_제목}\r\n
#{컨텐츠6_링크}\r\n
\r\n
■ #{기관명7}\r\n
☞ #{컨텐츠7_제목}\r\n
#{컨텐츠7_링크}\r\n
\r\n
■ #{기관명8}\r\n
☞ #{컨텐츠8_제목}\r\n
#{컨텐츠8_링크}\r\n
        """
        
        # 변수 값
        alimtalk_variables = {
            "회사명": organization_name,
            "고객명": user_name,
            "금일날짜": send_date,
            "전송개수": send_count,
            "기관명1": org1_name,
            "컨텐츠1_제목": content1_title,
            "컨텐츠1_링크": content1_url,
            "기관명2": org2_name,
            "컨텐츠2_제목": content2_title,
            "컨텐츠2_링크": content2_url,
            "기관명3": org3_name,
            "컨텐츠3_제목": content3_title,
            "컨텐츠3_링크": content3_url,
            "기관명4": org4_name,
            "컨텐츠4_제목": content4_title,
            "컨텐츠4_링크": content4_url,
            "기관명5": org5_name,
            "컨텐츠5_제목": content5_title,
            "컨텐츠5_링크": content5_url,
            "기관명6": org6_name,
            "컨텐츠6_제목": content6_title,
            "컨텐츠6_링크": content6_url,
            "기관명7": org7_name,
            "컨텐츠7_제목": content7_title,
            "컨텐츠7_링크": content7_url,
            "기관명8": org8_name,
            "컨텐츠8_제목": content8_title,
            "컨텐츠8_링크": content8_url,
        }
        
        message = alimtalk_template.format(**alimtalk_variables)
        return message
    
    def BIZPPURIO_ALIMTALK_TEMPLATE(self, alimtalk_variables: dict):
        
        alimtalk_template = """
K-MyContents 구독 서비스
안녕하세요. {이름} 님!
{날짜} 자 업데이트 된 추천 콘텐츠를 알려드립니다.

■ {기관1}
- {제목1}

■ {기관2}
- {제목2}

■ {기관3}
- {제목3}

■ {기관4}
- {제목4}

■ {기관5}
- {제목5}

■ {기관6}
- {제목6}

■ {기관7}
- {제목7}

■ {기관8}
- {제목8}

더 많은 콘텐츠는 포털에서 확인하세요!

※ 해당 구독 콘텐츠 전송 메시지는 고객님께서 신청하신 알림으로, 고객님이 MyContents 포털 내의 콘텐츠 구독 방법에서 '카카오톡' 을 선택하신 경우 발송됩니다.
        """
        
        message = alimtalk_template.format(**alimtalk_variables)
        return message
        
    # def BIZPPURIO_ALIMTALK_TEMPLATE(self, user_name: str, send_date: str,
    #                                 org1_name: str, content1_title: str,
    #                                 org2_name: str, content2_title: str,
    #                                 org3_name: str, content3_title: str,
    #                                 org4_name: str, content4_title: str,
    #                                 org5_name: str, content5_title: str,
    #                                 org6_name: str, content6_title: str,
    #                                 org7_name: str, content7_title: str,
    #                                 org8_name: str, content8_title: str):
        
    #     alimtalk_template = """
    #         K-MyContents 구독 서비스
    #         안녕하세요. #{이름} 님!
    #         #{날짜} 자 업데이트 된 추천 콘텐츠를 알려드립니다.

    #         ■ #{기관1}
    #         - #{제목1}

    #         ■ #{기관2}
    #         - #{제목2}

    #         ■ #{기관3}
    #         - #{제목3}

    #         ■ #{기관4}
    #         - #{제목4}

    #         ■ #{기관5}
    #         - #{제목5}

    #         ■ #{기관6}
    #         - #{제목6}

    #         ■ #{기관7}
    #         - #{제목7}

    #         ■ #{기관8}
    #         - #{제목8}

    #         더 많은 콘텐츠는 포털에서 확인하세요!

    #         ※ 해당 구독 콘텐츠 전송 메시지는 고객님께서 신청하신 알림으로, 고객님이 MyContents 포털 내의 콘텐츠 구독 방법에서 '카카오톡' 을 선택하신 경우 발송됩니다.
    #     """
        
    #     # 변수 값
    #     alimtalk_variables = {
    #         "이름": user_name,
    #         "날짜": send_date,
    #         "기관1": org1_name,
    #         "제목1": content1_title,
    #         "기관2": org2_name,
    #         "제목2": content2_title,
    #         "기관3": org3_name,
    #         "제목3": content3_title,
    #         "기관4": org4_name,
    #         "제목4": content4_title,
    #         "기관5": org5_name,
    #         "제목5": content5_title,
    #         "기관6": org6_name,
    #         "제목6": content6_title,
    #         "기관7": org7_name,
    #         "제목7": content7_title,
    #         "기관8": org8_name,
    #         "제목8": content8_title,
    #     }
        
    #     message = alimtalk_template.format(**alimtalk_variables)
    #     return message
    
    
    # request 에 대한 response 를 SendResult 로 리턴해주는 함수
    def return_response(self, receiver: MemberVO, response: dict[str, str], contents: list[ContentsVO]):
        self.docker_send_logger.info(f'return_response : {response}')
        if (str(response['code']) == "1000"):
            contentIds = [str(content._id) for content in contents]
            sendResult = SendResult(sendType=self.send_type, receiver=receiver, isSuccess=True, message=response, sendIds=contentIds)
            return sendResult
        
        else:
            sendResult = SendResult(sendType=self.send_type, receiver=receiver, isSuccess=False, message=response, sendIds=[])
            return sendResult
    
    # request 에 대한 response 를 SendResult 로 리턴해주는 함수
    def return_response_kecp(self, receiver: MemberVO, response: dict[str, str], contents: list[ContentsVO]):
        self.docker_send_logger.info(f'return_response_kecp : {response}')
        if (response['retCode'] == "OK"):
            contentIds = [str(content._id) for content in contents]
            sendResult = SendResult(sendType=self.send_type, receiver=receiver, isSuccess=True, message=response, sendIds=contentIds)
            return sendResult
        
        else:
            sendResult = SendResult(sendType=self.send_type, receiver=receiver, isSuccess=False, message=response, sendIds=[])
            return sendResult
    
    def return_customize_error_response(self, receiver: MemberVO, message: str):
        self.docker_send_logger.info(f'return_customize_error_response : {message}')
        response = {}
        response["ex"] = str(message)
        sendResult = SendResult(sendType=self.send_type, receiver=receiver, isSuccess=False, message=response, sendIds=[])
        return sendResult
    
    def return_exception_response(self, receiver: MemberVO, ex: Exception):
        self.docker_send_logger.info(f'return_exception_response : {str(ex)}')
        response = {}
        response["ex"] = str(ex)
        sendResult = SendResult(sendType=self.send_type, receiver=receiver, isSuccess=False, message=response, sendIds=[])
        return sendResult
    
    # 템플릿 리스트 요청 # 알리고 버전 추후 삭제
    def request_template_list(self, receiver: MemberVO):
        try:
            # initialize 체크
            if not self.initialized:
                sendResult = SendResult(sendType=self.send_type, receiver=receiver.mberEmail, isSuccess=False, message=f"Kakao API is not Initialized.")
                return sendResult
            
            sms_data={
                'apikey': self.api_key, #api key
                'userid': self.user_id, # 알리고 사이트 아이디
                'senderkey': self.sender_key, # 발신프로파일 키
                }
                    
            template_list_response = requests.post(self.templateUrl, data=sms_data)
            response = template_list_response.json()
            
            return self.return_response(receiver=receiver, response=response)
            
        except Exception as ex:
            sendResult = SendResult(sendType=self.send_type, receiver=receiver.mberEmail, isSuccess=False, message=ex)
            return sendResult
        
    # 알림톡 전송     # 알리고 버전 추후 삭제
    def request_alimtalk_send(self, receiver: MemberVO, contents: list[ContentsVO]):
        try:
            # initialize 체크
            if not self.initialized:
                sendResult = SendResult(sendType=self.send_type, receiver=receiver.mberEmail, isSuccess=False, message=f"Kakao API is not Initialized.")
                return sendResult
            
            current_date = datetime.now().strftime("%Y-%m-%d")
            alimtalk_code = "TX_0603"
            
            max_send_cnt = 8
            
            alimtalk_variables={
                "회사명": "한전 KDN",
                "고객명": receiver.mberName,
                "금일날짜": datetime.now().strftime("%Y-%m-%d"),
            }
            
            for index, content in enumerate(contents, start=1):
                alimtalk_variables[f"기관명{index}"] = content.contentsOrgName
                alimtalk_variables[f"컨텐츠{index}_제목"] = content.title
                alimtalk_variables[f"컨텐츠{index}_링크"] = content.link
                
                if (index == len(contents) - 1 or index > max_send_cnt):
                    if (index < max_send_cnt):
                        for i in range(index + 1, max_send_cnt + 1, 1):  # i = index; i < max_send_cnt + 1; i++
                            alimtalk_variables[f"기관명{i}"] = "없음"
                            alimtalk_variables[f"컨텐츠{i}_제목"] = "없음"
                            alimtalk_variables[f"컨텐츠{i}_링크"] = "없음"
            
            message = self.ALIMTALK_TEMPLATE(alimtalk_variables)
            
            sms_data={
                'apikey': self.api_key, #api key
                'userid': self.user_id, # 알리고 사이트 아이디
                'senderkey': self.sender_key, # 발신프로파일 키
                'tpl_code': alimtalk_code, # 템플릿 코드
                'sender' : self.sender_number, # 발신자 연락처,
                #'senddate': '19000131120130', # YYYYMMDDHHmmss
                'receiver_1': receiver.mberTelno, # 수신자 연락처
                #'recvname_1': '홍길동1', # 수신자 이름
                'subject_1': f'Kakao AlimTalk {current_date} - {receiver.mberId}', # 알림톡 제목 - 수신자에게는 표기X
                'message_1': message, # 알림톡 내용 - 등록한 템플릿이랑 개행문자 포함 동일하게 입력.
                # 'button_1': button_info, # 버튼 정보
                #'failover': 'Y or N', # 실패시 대체문자 전송 여부(템플릿 신청시 대체문자 발송으로 설정하였더라도 Y로 입력해야합니다.)
                #'fsubject_1': '대체문자 제목', # 실패시 대체문자 제목
                #'fmessage_1': '대체문자 내용', # 실패시 대체문자 내용
                'testMode': 'Y' # 테스트 모드 적용여부(기본N), 실제 발송 X
                }
            
            alimtalk_send_response = requests.post(self.alimtalk_send_url, data=sms_data)
            return self.return_response(receiver=receiver, response=alimtalk_send_response)
        
        except Exception as ex:
            sendResult = SendResult(sendType=self.send_type, receiver=receiver.mberEmail, isSuccess=False, message=ex)
            return sendResult
            
    # 친구톡 전송 # 알리고 버전 추후 삭제
    def request_friendtalk_send(self, receiver: MemberVO, message: str):
        try:
            # initialize 체크
            if not self.initialized:
                sendResult = SendResult(sendType=self.send_type, receiver=receiver.mberEmail, isSuccess=False, message=f"Kakao API is not Initialized.")
                return sendResult
            
            current_date = datetime.now().strftime("%Y-%m-%d")
        
            button_info = {'button': [{'name':'name', # 버튼명
                            'linkType':'WL', # DS, WL, AL, BK, MD
                            'linkTypeName' : '웹링크', # 배송조회, 웹링크, 앱링크, 봇키워드, 메시지전달 중에서 1개
                            #'linkM':'mobile link', # WL일 때 필수
                            #'linkP':'pc link', # WL일 때 필수
                            #'linkI': 'IOS app link', # AL일 때 필수
                            #'linkA': 'Android app link' # AL일 때 필수
                            }]}

            sms_data={
                'apikey': self.api_key, #api key
                'userid': self.user_id, # 알리고 사이트 아이디
                'senderkey': self.sender_key, # 발신프로파일 키
                'sender' : self.sender_number, # 발신자 연락처,
                #'senddate': '19000131120130', # YYYYMMDDHHmmss
                #'advert': 'Y or N', # 광고분류(기본Y)
                #'image_url': 'http://xxxx.com/xxx.jpg', # 첨부이미지에 삽입되는 링크
                'receiver_1': receiver.mberTelno, # 수신자 연락처
                #'recvname_1': '홍길동1', # 수신자 이름
                'subject_1': f'Kakao FriendTalk {current_date} - {receiver.mberId}', # 알림톡 제목 - 수신자에게는 표기X
                'message_1': message, # 친구톡 내용
                #'button_1': button_info, # 버튼 정보
                #'failover': 'Y or N', # 실패시 대체문자 전송 여부(템플릿 신청시 대체문자 발송으로 설정하였더라도 Y로 입력해야합니다.)
                #'fsubject_1': '대체문자 제목', # 실패시 대체문자 제목
                #'fmessage_1': '대체문자 내용', # 실패시 대체문자 내용
                'testMode': 'Y' # 테스트 모드 적용여부(기본N), 실제 발송 X
                }
            
            friendtalk_send_response = requests.post(self.alimtalkSendUrl, data=sms_data)
            return self.return_response(receiver=receiver, response=friendtalk_send_response)
            
        except Exception as ex:
            sendResult = SendResult(sendType=self.send_type, receiver=receiver.mberEmail, isSuccess=False, message=ex)
            return sendResult
    
    def generate_refkey(self, phone: str):
        timestamp = datetime.now().strftime("%y-%m-%d %H:%M:%S")  # yy-MM-dd HH:mm:ss 형식
        return f"{phone.replace('-', '')}-{timestamp}" # refKey 는 32자를 넘어서는 안된다고 함.
    
    def make_request(self, send_vo: SendModel) -> Dict[str, Optional[Dict[str, object]]]:
        results = {}

        try:
            request_body = {
                "account": self.user_id,
                "type": send_vo.send_type,
                "from": self.sender_number,
                "to": send_vo.mber_telno,
                "refkey": self.generate_refkey(send_vo.mber_telno)
            }

            # 예약 전송 확인
            if send_vo.reserved_send_yn == "Y":
                unix_time = int(datetime.combine(send_vo.reserved_dt, datetime.min.time()).timestamp())
                request_body["sendtime"] = unix_time

            # Content 구성
            content_body = {
                "message": send_vo.template_msg,
                "senderkey": self.sender_key,
                # "templatecode": send_vo.template_code,
                "button": [
                    {
                        "name": "채널 추가",
                        "type": "AC",
                    },
                    {
                        "name": "포털 바로가기",
                        "type": "WL",
                        "url_pc": self.base_url,
                        "url_mobile": self.base_url
                    }
                ]
            }

            # 친구톡인 경우
            if send_vo.send_type in ["ft", "fi"]:
                request_body["adflag"] = "Y"
                if send_vo.send_type == "fi":
                    image = {
                        "img_url": send_vo.img_url,
                        "imglink": self.base_url
                    }
                    content_body["image"] = image
                    
            # 알림톡인 경우
            if send_vo.send_type in ["at", "ai"]:
                content_body["templatecode"] = send_vo.template_code

            content = {send_vo.send_type: content_body}
            request_body["content"] = content

            results[send_vo.mber_telno] = request_body

        except Exception as ex:
            results[send_vo.mber_telno] = None
            print(str(ex))

        return results
    
    # Base64 암호화 함수
    def encrypt_base64(self, value):
        return base64.urlsafe_b64encode(value.encode()).decode()
    
    def encrypt_base64(self, value: bytearray):
        return base64.urlsafe_b64encode(value).decode()

    # Base64 복호화 함수
    def decrypt_base64(self, value):
        return base64.urlsafe_b64decode(value.encode()).decode()
    
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
    
    def pad(self, data: bytes) -> bytes:
        """
        PKCS7 Padding: 데이터 길이를 AES 블록 크기(16)로 맞춤.
        """
        block_size = AES.block_size
        pad_len = block_size - len(data) % block_size
        return data + bytes([pad_len] * pad_len)
    
    def make_url_from_contents_list(self, contents: list[ContentsVO]):
        # list 에서 _id 만 추출
        contents_id_list = [str(content._id) for content in contents]
        # list[str] 을 ',' 로 이어서 string 으로 변환
        joined_string = ",".join(contents_id_list)
        # print(f'joined_string {joined_string}')
        # json 으로 변환
        json_data = json.dumps(joined_string).encode('utf-8')
        # 데이터 압축
        compressed_data = zlib.compress(json_data)
        # 압축된 데이터를 Base64로 인코딩
        encoded_data = base64.urlsafe_b64encode(compressed_data).decode('utf-8')
        
        params = {}
        params["requests"] = encoded_data  # 특정 파라미터 암호화
        contents_url = f"{self.base_url}?{urlencode(params)}" # 최종 URL
        return contents_url
    
    def send_kakao(self,receiver: MemberVO, contents: list[ContentsVO]):
        if contents is None or len(contents) == 0:
            return

        if receiver is None or receiver.get_decrypt_mberTelno() is None:
            return

        if len(contents) > 8:
            contents = contents[:8]

        params : dict[str, str] = {}
        params["title"] = quote('K-CaaS')
        params["sendNo"] = quote(receiver.get_decrypt_mberTelno().replace('-', ''))
        # params["sendNo"] = quote('01053911388')
        params["callBackNo"] = quote('0619317114')
        params["systemKey"] = quote('212118-caas01')
        params["projectId"] = quote('KDN-3570-23-0001')
        params["tmplCode"] = quote('AT_20230830095523')
        params["paramNum"] = quote('33')
        params["param1"] = date.today().strftime("%Y-%m-%d")
        params["param2"] = len(contents)
        params["param3"] = quote(' 요약된 콘텐츠입니다. 이외 콘텐츠는 포털에서 확인 바랍니다.')
        
        lms = '한전KDN 콘텐츠 구독 서비스\n'
        lms += f'{params["param1"]}일 콘텐츠를 송부드립니다. 총 {params["param2"]}건 '
        lms += f'\n{params["param3"]}'

        for idx, content in enumerate(contents, start=1): # 인덱스를 1부터 시작
            # 1일 때 4 5 6, 2일 때 7 8 9, 3일 때 10 11 12 ...
            param_idx = 3 * idx + 1  # 시작 값 계산
            
            # 기관명과 카테고리명이 같으면 카테고리명 생략하기
            org_name = quote(f'■ {content.contentsOrgName}') if (content.categoryName == content.contentsOrgName) else quote(f'■ {content.categoryName}-{content.contentsOrgName}')
            org_name_lms = f'■ {content.contentsOrgName}' if (content.categoryName == content.contentsOrgName) else f'■ {content.contentsOrgName}'
            
            # 제목 길이가 길면 줄이기 (45자 제한, 한줄 때문 뿐만이 아니라 카톡 1000자 제한 때문에)
            contents_title = quote(f'- {content.title}') if len(content.title) <= 45 else quote(f'- {content.title[:45]}..')
            contents_title_lms = f'- {content.title}' if len(content.title) <= 45 else f'- {content.title[:45]}..'

            # 컨텐츠를 볼 수 있는 url 넣기.
            reordered_list = [content] + [item for item in contents if item is not content]
            contents_url = self.make_url_from_contents_list(reordered_list)

            params[f"param{param_idx}"] = org_name
            lms += f'{org_name_lms}\n'
            params[f"param{param_idx + 1}"] = contents_title
            lms += f'{contents_title_lms}\n'
            params[f"param{param_idx + 2}"] = contents_url
            lms += f'{contents_url}\n'
            
        ########### 전송 ###########
        # print(lms)
        params["content"] = quote(lms)
        query_string = urlencode(params)
        url = f'{Conf.KDN_KAKAO_SERVICE_URL}?{query_string}'
        # print(url)
        # params = f'?sendNo={sendNo}&callBackNo={callBackNo}&systemKey={systemKey}&projectId={projectId}&tmplCode={tmplCode}&paramNum={paramNum}&param1={param1}&param2={param2}&param3={param3}&param4={param4}&param5={param5}&param6={param6}&param7={param7}&param8={param8}&param9={param9}&param10={param10}&param11={param11}&param12={param12}&param13={param13}&param14={param14}&param15={param15}&param16={param16}&param17={param17}&param18={param18}&param19={param19}&param20={param20}&param21={param21}&param22={param22}&param23={param23}&param24={param24}&param25={param25}&param26={param26}&param27={param27}&param28={param28}&param29={param29}&param30={param30}&param31={param31}&param32={param32}&param33={param33}&title=K-CaaS&content={lms}'

        try:
            response = requests.get(url)
            handled_response = self.handle_response(response)
            # 응답 처리
            return self.return_response_kecp(receiver=receiver, response=handled_response, contents=contents)
        except Exception as ex:
            return self.return_exception_response(receiver=receiver, ex=ex)
            

    def handle_response(self, response: requests.models.Response):
        try:
            # Content-Type 확인
            content_type = response.headers.get("Content-Type", "")

            if "application/json" in content_type:
                # JSON 응답 처리
                return response.json()
            else:
                # JSON이 아닌 응답 처리
                return {
                    "status_code": response.status_code,
                    "message": response.text.strip()  # 응답 내용
                }
        except ValueError as e:
            # JSON 디코딩 오류 처리
            return {
                "status_code": response.status_code,
                "error_message": f"Failed to decode JSON: {str(e)}"
            }

    def parse_json_to_dict(self, json_string: str) -> Dict[str, Any]:
        """
        JSON 문자열을 Python 딕셔너리로 변환하는 함수
        """
        try:
            print(json_string)
            return json.loads(json_string)  # JSON 문자열을 딕셔너리로 변환
        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류: {e}")
            return {}  # 파싱 실패 시 빈 딕셔너리 반환

    def is_token_valid(self) -> bool:
        try:
            if not self.access_token or self.access_token.strip() == "":
                return False

            # 입력 문자열을 datetime 객체로 변환
            expiry_date = datetime.strptime(self.token_expired, "%Y%m%d%H%M%S")

            # 현재 시간 가져오기
            current_date = datetime.now()

            # 만료 여부 확인
            return current_date < expiry_date  # 현재 시간이 만료 시간 이전인지 확인
        except ValueError as e:
            print(f"Invalid date format: {e}")
            return False  # 날짜 파싱에 실패하면 만료된 것으로 간주

    def token_request(self, url: str, account: str, password: str) -> Dict[str, Any]:
        """
        REST API를 통해 인증 토큰을 요청하는 함수
        """
        try:
            # Base64로 계정:암호 인코딩
            credentials = f"{account}:{password}"
            encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
            
            print(encoded_credentials)

            # 요청 헤더 설정
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Basic {encoded_credentials}",
            }

            # 요청 바디 (빈 JSON 객체)
            json_body = {}

            # POST 요청 전송
            response = requests.post(url, json=json_body, headers=headers)

            # 응답 상태 확인
            return self.parse_json_to_dict(response.text)

        except requests.exceptions.RequestException as e:
            # 예외 정보를 반환
            return {"code": "500", "reason": str(e)}

    def refresh_auth_token(self):
        """
        인증 토큰을 새로고침하는 함수
        """
        # 요청 보내고 응답 받기
        response = self.token_request(self.auth_token_url, self.user_id, self.password)

        # 응답 처리
        print(f"토큰 요청 결과: {response}")

        # 필요한 데이터 추출
        self.access_token = response.get("accesstoken")
        token_type = response.get("type")
        self.token_expired = response.get("expired")

        # 데이터 활용 예시
        print(f"Access Token: {self.access_token}")
        print(f"Token Type: {token_type}")
        print(f"Token Expiry: {self.token_expired}")

    def post_request(self, url: str, token: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        REST API에 POST 요청을 보내는 함수
        """
        try:
            # 요청 헤더 설정
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }

            # JSON 변환
            json_body = json.dumps(params)

            # POST 요청 전송
            response = requests.post(url, data=json_body, headers=headers)

            # 응답 상태 확인
            if response.status_code == 200:
                return response.json()  # JSON 응답을 딕셔너리로 변환
            else:
                return response.json()  # 실패 응답도 그대로 반환

        except requests.exceptions.RequestException as e:
            print(f"Request Error: {e}")
            return {"code": "500", "reason": str(e)}


    def request_send_messages(self, send_vo: SendModel) -> Dict[str, Any]:
        """ 메시지 전송 요청 함수 """
        result = {}
        result_responses = {}
        result_map = {"Success": [], "Fail": []}
        send_all_success = True

        # 요청 객체가 None이면 예외 처리
        if send_vo is None:
            send_all_success = False
            
            return {
                "isSuccess": False,
                "message": "Bad Parameter : Param is Null",
                "sendIds": [],
                "sendType": "ai",
                "receiver": send_vo.mber_telno
            }

        # access_token이 없거나 만료되었으면 토큰 갱신
        if not self.is_token_valid():
            self.refresh_auth_token()

        # 토큰 갱신 후에도 유효하지 않다면 에러 반환
        if not self.is_token_valid():
            return {
                "isSuccess": False,
                "message": "AccessToken is not validated.",
                "sendIds": [],
                "sendType": "ai",
                "receiver": send_vo.mber_telno
            }

        # 메시지 API를 보내기 위한 요청 목록 생성
        requests = self.make_request(send_vo)

        print("*****")
        print("*****")
        print("*** 요청 만들기 완료 ***")
        print(requests)
        print("*****")
        print("*****")
        print("*****")

        # 메시지 API 요청 및 결과 처리
        for key, params in requests.items():
            # 요청 파라미터가 None이면 예외 처리
            if params is None:
                result_map["Fail"].append(key)
                continue

            # 메시지 API 요청 실행
            response = self.post_request(self.message_url, self.access_token, params)
            result_responses[key] = response  # 응답 저장

            # 응답 코드 확인
            if response.get("code") != "1000":
                print(f"요청 실패: {response}")
                result_map["Fail"].append(key)
                send_all_success = False
            else:
                print(f"요청 성공: {response}")
                result_map["Success"].append(key)

        result.update({
            "isRequestCompleted": True,
            "reason": "",
            "sendResponses": result_responses,
            "isAllSendSuccess": send_all_success,
        })

        return result


    def send_kakao_bizppurio(self, receiver: MemberVO, contents: list[ContentsVO]):
        # 비즈뿌리오 메시지 전송 요청 함수
        
        # 유저 정보에 필수 정보가 없으면 예외 처리
        if not hasattr(receiver, "mberName") or receiver.mberName == None:
            return SendResult(isSuccess=False, message="Bad Parameter : No Parameter mberName", sendIds=[], sendType="ai", receiver=receiver.mberTelno)
            
        # 유저 정보에 필수 정보가 없으면 예외 처리
        if not hasattr(receiver, "mberTelno" or receiver.mberTelno == None):
            return SendResult(isSuccess=False, message="Bad Parameter : No Parameter mberTelno", sendIds=[], sendType="ai", receiver=receiver.mberTelno)
                
        # 요청 객체가 None이면 예외 처리
        if contents is None or len(contents) == 0:
            return SendResult(isSuccess=False, message="Bad Parameter : No Contents", sendIds=[], sendType="ai", receiver=receiver.mberTelno)

        # 메시지 만들기    
        # 최대 콘텐츠 전송 개수
        max_send_cnt = 8
            
        alimtalk_variables : Dict[str, str] = {
            "이름": receiver.mberName,
            "날짜": datetime.now().strftime("%Y-%m-%d"),
        }
        
        send_contents = []

        # index 를 1부터 시작하게끔 설정해서 반복
        for index, content in enumerate(contents, start=1):
            self.docker_send_logger.info(f"index : {index}")
            # 최대 콘텐츠 전송 개수를 넘은 경우 break
            if (index == index > max_send_cnt):
                self.docker_send_logger.info(f"최대 콘텐츠 전송 개수를 넘은 경우 break")
                break
            
            alimtalk_variables[f"기관{index}"] = content.contentsOrgName
            alimtalk_variables[f"제목{index}"] = content.title
            send_contents.append(content)
            # 마지막 인덱스인 경우 (contents 의 개수가 1개인 경우에는 별도 처리)
            if (index == len(contents) - 1 or len(contents) == 1):
                self.docker_send_logger.info(f"마지막 인덱스인 경우")
                # 빈 값으로 채워 넣기
                for i in range(index + 1, max_send_cnt + 1, 1):  # i = index; i < max_send_cnt + 1; i++
                    self.docker_send_logger.info(f"i : {i}")
                    alimtalk_variables[f"기관{i}"] = "-"
                    alimtalk_variables[f"제목{i}"] = " "
                
        self.docker_send_logger.info(f"alimtalk_variables : {alimtalk_variables}")
        message = self.BIZPPURIO_ALIMTALK_TEMPLATE(alimtalk_variables)
        
        # access_token이 없거나 만료되었으면 토큰 갱신
        if not self.is_token_valid():
            self.refresh_auth_token()

        # 토큰 갱신 후에도 유효하지 않다면 에러 반환
        if not self.is_token_valid():
            return SendResult(isSuccess=False, message="AccessToken is not validated.", sendIds=[], sendType="ai", receiver=receiver.mberTelno)
            
        # 메시지 API를 보내기 위한 요청 목록 생성
        aiSendModel = SendModel()
        aiSendModel.mber_telno = receiver.get_decrypt_mberTelno()
        aiSendModel.send_type = "ai"
        aiSendModel.template_code = "bizp_2025021711385184552572887"
        aiSendModel.template_msg = message
        requests = self.make_request(aiSendModel)

        print("*****")
        print("*****")
        print("*** 요청 만들기 완료 ***")
        print(requests)
        print("*****")
        print("*****")
        print("*****")

        # 만든 Request 가 None 이면 예외 처리
        if requests[receiver.get_decrypt_mberTelno()] is None:
            return SendResult(isSuccess=False, message="Request is None.", sendIds=[], sendType="ai", receiver=receiver.mberTelno)

        # 메시지 API 요청 및 결과 처리
        try:
            response = self.post_request(self.message_url, self.access_token, requests[receiver.get_decrypt_mberTelno()])
            # handled_response = self.handle_response(response)
            # 응답 처리
            return self.return_response(receiver=receiver, response=response, contents=send_contents)
        except Exception as ex:
            return self.return_exception_response(receiver=receiver, ex=ex)


    

        
		

        