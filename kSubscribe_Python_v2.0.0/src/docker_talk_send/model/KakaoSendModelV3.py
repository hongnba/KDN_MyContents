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
        self.kakao_direct_login_url = Conf.KAKAO_DIRECT_LOGIN_URL
        self.kakao_inapp_browser_url = Conf.KAKAO_INAPP_BROWSER_URL
        
        self.user_id = user_id
        self.password = password
        self.sender_key = sender_key
        self.sender_number = sender_number
        
        logger = Logger()
        self.docker_collect_logger = logger.setup_logger(logger.docker_talk_send_logger_name)
        
        self.access_token = ""
        self.token_expired = ""
        
    def initialize(self):
        try:
            # 비즈뿌리오 kakao api 는 토큰을 받아야 함.
            self.refresh_auth_token()

            # 토큰 갱신 후에도 유효하지 않다면 에러 반환
            if not self.is_token_valid():
                self.initialized = False
            else:
                self.initialized = True
        except Exception as ex:
            print(ex)
            self.initialized = False
    
    def BIZPPURIO_ALIMTALK_TEMPLATE_Backup(self, alimtalk_variables: dict):
        
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
       
    def BIZPPURIO_ALIMTALK_TEMPLATE(self, alimtalk_variables: dict):
        
        alimtalk_template = """
K-MyContents 구독 서비스
안녕하세요. {이름} 님!
{날짜} 자 업데이트 된 추천 콘텐츠를 알려드립니다.

{기관1}
{제목1}

{기관2}
{제목2}

{기관3}
{제목3}

{기관4}
{제목4}

{기관5}
{제목5}

{기관6}
{제목6}

{기관7}
{제목7}

{기관8}
{제목8}

더 많은 콘텐츠는 포털에서 확인하세요!

※ 해당 구독 콘텐츠 전송 메시지는 고객님께서 신청하신 알림으로, 고객님이 MyContents 포털 내의 콘텐츠 구독 방법에서 '카카오톡' 을 선택하신 경우 발송됩니다.
        """
        
        message = alimtalk_template.format(**alimtalk_variables)
        return message
    
    def BIZPPURIO_ALIMTALK_TEMPLATE_1(self, alimtalk_variables: dict):
        
        alimtalk_template = """
K-MyContents 구독 서비스
안녕하세요. {이름} 님!
{날짜} 자 업데이트 된 추천 콘텐츠를 알려드립니다.

{기관1}
{제목1}

더 많은 콘텐츠는 포털에서 확인하세요!

※ 해당 구독 콘텐츠 전송 메시지는 고객님께서 신청하신 알림으로, 고객님이 MyContents 포털 내의 콘텐츠 구독 방법에서 '카카오톡' 을 선택하신 경우 발송됩니다.
        """
        
        message = alimtalk_template.format(**alimtalk_variables)
        return message

    def BIZPPURIO_ALIMTALK_TEMPLATE_2(self, alimtalk_variables: dict):
        
        alimtalk_template = """
K-MyContents 구독 서비스
안녕하세요. {이름} 님!
{날짜} 자 업데이트 된 추천 콘텐츠를 알려드립니다.

{기관1}
{제목1}

{기관2}
{제목2}

더 많은 콘텐츠는 포털에서 확인하세요!

※ 해당 구독 콘텐츠 전송 메시지는 고객님께서 신청하신 알림으로, 고객님이 MyContents 포털 내의 콘텐츠 구독 방법에서 '카카오톡' 을 선택하신 경우 발송됩니다.
        """
        
        message = alimtalk_template.format(**alimtalk_variables)
        return message

    def BIZPPURIO_ALIMTALK_TEMPLATE_3(self, alimtalk_variables: dict):
        
        alimtalk_template = """
K-MyContents 구독 서비스
안녕하세요. {이름} 님!
{날짜} 자 업데이트 된 추천 콘텐츠를 알려드립니다.

{기관1}
{제목1}

{기관2}
{제목2}

{기관3}
{제목3}

더 많은 콘텐츠는 포털에서 확인하세요!

※ 해당 구독 콘텐츠 전송 메시지는 고객님께서 신청하신 알림으로, 고객님이 MyContents 포털 내의 콘텐츠 구독 방법에서 '카카오톡' 을 선택하신 경우 발송됩니다.
        """
        
        message = alimtalk_template.format(**alimtalk_variables)
        return message
    
    def BIZPPURIO_ALIMTALK_TEMPLATE_4(self, alimtalk_variables: dict):
        
        alimtalk_template = """
K-MyContents 구독 서비스
안녕하세요. {이름} 님!
{날짜} 자 업데이트 된 추천 콘텐츠를 알려드립니다.

{기관1}
{제목1}

{기관2}
{제목2}

{기관3}
{제목3}

{기관4}
{제목4}

더 많은 콘텐츠는 포털에서 확인하세요!

※ 해당 구독 콘텐츠 전송 메시지는 고객님께서 신청하신 알림으로, 고객님이 MyContents 포털 내의 콘텐츠 구독 방법에서 '카카오톡' 을 선택하신 경우 발송됩니다.
        """
        
        message = alimtalk_template.format(**alimtalk_variables)
        return message
    
    def BIZPPURIO_ALIMTALK_TEMPLATE_5(self, alimtalk_variables: dict):
        
        alimtalk_template = """
K-MyContents 구독 서비스
안녕하세요. {이름} 님!
{날짜} 자 업데이트 된 추천 콘텐츠를 알려드립니다.

{기관1}
{제목1}

{기관2}
{제목2}

{기관3}
{제목3}

{기관4}
{제목4}

{기관5}
{제목5}

더 많은 콘텐츠는 포털에서 확인하세요!

※ 해당 구독 콘텐츠 전송 메시지는 고객님께서 신청하신 알림으로, 고객님이 MyContents 포털 내의 콘텐츠 구독 방법에서 '카카오톡' 을 선택하신 경우 발송됩니다.
        """
        
        message = alimtalk_template.format(**alimtalk_variables)
        return message

    def BIZPPURIO_ALIMTALK_TEMPLATE_6(self, alimtalk_variables: dict):
        
        alimtalk_template = """
K-MyContents 구독 서비스
안녕하세요. {이름} 님!
{날짜} 자 업데이트 된 추천 콘텐츠를 알려드립니다.

{기관1}
{제목1}

{기관2}
{제목2}

{기관3}
{제목3}

{기관4}
{제목4}

{기관5}
{제목5}

{기관6}
{제목6}

더 많은 콘텐츠는 포털에서 확인하세요!

※ 해당 구독 콘텐츠 전송 메시지는 고객님께서 신청하신 알림으로, 고객님이 MyContents 포털 내의 콘텐츠 구독 방법에서 '카카오톡' 을 선택하신 경우 발송됩니다.
        """
        
        message = alimtalk_template.format(**alimtalk_variables)
        return message

    def BIZPPURIO_ALIMTALK_TEMPLATE_7(self, alimtalk_variables: dict):
        
        alimtalk_template = """
K-MyContents 구독 서비스
안녕하세요. {이름} 님!
{날짜} 자 업데이트 된 추천 콘텐츠를 알려드립니다.

{기관1}
{제목1}

{기관2}
{제목2}

{기관3}
{제목3}

{기관4}
{제목4}

{기관5}
{제목5}

{기관6}
{제목6}

{기관7}
{제목7}

더 많은 콘텐츠는 포털에서 확인하세요!

※ 해당 구독 콘텐츠 전송 메시지는 고객님께서 신청하신 알림으로, 고객님이 MyContents 포털 내의 콘텐츠 구독 방법에서 '카카오톡' 을 선택하신 경우 발송됩니다.
        """
        
        message = alimtalk_template.format(**alimtalk_variables)
        return message
    
    def BIZPPURIO_ALIMTALK_TEMPLATE_8(self, alimtalk_variables: dict):
        
        alimtalk_template = """
K-MyContents 구독 서비스
안녕하세요. {이름} 님!
{날짜} 자 업데이트 된 추천 콘텐츠를 알려드립니다.

{기관1}
{제목1}

{기관2}
{제목2}

{기관3}
{제목3}

{기관4}
{제목4}

{기관5}
{제목5}

{기관6}
{제목6}

{기관7}
{제목7}

{기관8}
{제목8}

더 많은 콘텐츠는 포털에서 확인하세요!

※ 해당 구독 콘텐츠 전송 메시지는 고객님께서 신청하신 알림으로, 고객님이 MyContents 포털 내의 콘텐츠 구독 방법에서 '카카오톡' 을 선택하신 경우 발송됩니다.
        """
        
        message = alimtalk_template.format(**alimtalk_variables)
        return message

    # request 에 대한 response 를 SendResult 로 리턴해주는 함수
    def return_response(self, receiver: MemberVO, response: dict[str, str], contents: list[ContentsVO]):
        self.docker_collect_logger.info(f'return_response : {response}')
        if (str(response['code']) == "1000"):
            contentIds = [str(content._id) for content in contents]
            sendResult = SendResult(sendType=self.send_type, receiver=receiver, isSuccess=True, message=response, sendIds=contentIds)
            return sendResult
        
        else:
            sendResult = SendResult(sendType=self.send_type, receiver=receiver, isSuccess=False, message=response, sendIds=[])
            return sendResult
    
    def return_customize_error_response(self, receiver: MemberVO, message: str):
        self.docker_collect_logger.info(f'return_customize_error_response : {message}')
        response = {}
        response["ex"] = str(message)
        sendResult = SendResult(sendType=self.send_type, receiver=receiver, isSuccess=False, message=response, sendIds=[])
        return sendResult
    
    def return_exception_response(self, receiver: MemberVO, ex: Exception):
        self.docker_collect_logger.info(f'return_exception_response : {str(ex)}')
        response = {}
        response["ex"] = str(ex)
        sendResult = SendResult(sendType=self.send_type, receiver=receiver, isSuccess=False, message=response, sendIds=[])
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
                        "url_pc": send_vo.button_url,
                        "url_mobile": send_vo.button_url
                    }
                ]
            }

            # 친구톡인 경우
            if send_vo.send_type in ["ft", "fi"]:
                request_body["adflag"] = "Y"
                if send_vo.send_type == "fi":
                    image = {
                        "img_url": send_vo.img_url,
                        "imglink": send_vo.button_url
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
            return response.json()  # JSON 응답을 딕셔너리로 변환

        except requests.exceptions.RequestException as e:
            print(f"Request Error: {e}")
            return {"code": "500", "reason": str(e)}

    def send_kakao_bizppurio(self, receiver: MemberVO, contents: list[ContentsVO]):
        try:
            # 비즈뿌리오 메시지 전송 요청 함수
            
            # 유저 정보에 필수 정보가 없으면 예외 처리
            if not hasattr(receiver, "mberName") or receiver.mberName == None:
                return SendResult(isSuccess=False, message="Bad Parameter : No Parameter mberName", sendIds=[], sendType=self.send_type, receiver=receiver.mberTelno)
                
            # 유저 정보에 필수 정보가 없으면 예외 처리
            if not hasattr(receiver, "mberTelno" or receiver.mberTelno == None):
                return SendResult(isSuccess=False, message="Bad Parameter : No Parameter mberTelno", sendIds=[], sendType=self.send_type, receiver=receiver.mberTelno)
                    
            # 요청 객체가 None이면 예외 처리
            if contents is None or len(contents) == 0:
                return SendResult(isSuccess=False, message="Bad Parameter : No Contents", sendIds=[], sendType=self.send_type, receiver=receiver.mberTelno)

            # 메시지 만들기    
            # 최대 콘텐츠 전송 개수
            # 요구 사항 : 카카오톡은 최대 8개의 콘텐츠를 보내고, sendHistory 에는 최대 20 개 까지의 콘텐츠를 저장함.
            max_count = 20
        
            if len(contents) > max_count:
                contents = contents[:max_count]
            
            max_send_cnt = 8
            send_contents = []
                
            alimtalk_variables : Dict[str, str] = {
                "이름": receiver.mberName,
                "날짜": datetime.now().strftime("%Y-%m-%d"),
            }

            # index 를 1부터 시작하게끔 설정해서 반복
            for index, content in enumerate(contents, start=1):
                # 최대 콘텐츠 전송 개수를 넘은 경우 break
                if (index == index > max_send_cnt):
                    break
                
                alimtalk_variables[f"기관{index}"] = f"■ {content.contentsOrgName}"
                alimtalk_variables[f"제목{index}"] = f"- {content.title}"
                
                send_contents.append(content)
                
                # 마지막 인덱스인 경우와 콘텐츠의 개수가 1개인 경우에 대한 처리
                if (index == len(contents) - 1 or len(contents) == 1):
                    # 빈 값으로 채워 넣기
                    for i in range(index + 1, max_send_cnt + 1, 1):  # i = index; i < max_send_cnt + 1; i++
                        alimtalk_variables[f"기관{i}"] = ""
                        alimtalk_variables[f"제목{i}"] = ""
                    
            # message = self.BIZPPURIO_ALIMTALK_TEMPLATE(alimtalk_variables)
            
            # alimtalk_variables[f"기관{index}"] = f"■ {content.contentsOrgName}"
            # alimtalk_variables[f"제목{index}"] = f" - {content.title}"
            # # send_contents.append(content)
            # # 마지막 인덱스인 경우와 콘텐츠의 개수가 1개인 경우에 대한 처리
            # if (index == len(contents) - 1 or len(contents) == 1):
            #     # 빈 값으로 채워 넣기
            #     for i in range(index + 1, max_send_cnt + 1, 1):  # i = index; i < max_send_cnt + 1; i++
            #             alimtalk_variables[f"기관{i}"] = ""
            #             alimtalk_variables[f"제목{i}"] = ""

            message = ""

            if (len(send_contents) == 1):
                message = self.BIZPPURIO_ALIMTALK_TEMPLATE_1(alimtalk_variables)
            elif (len(send_contents) == 2):
                message = self.BIZPPURIO_ALIMTALK_TEMPLATE_2(alimtalk_variables)
            elif (len(send_contents) == 3):
                message = self.BIZPPURIO_ALIMTALK_TEMPLATE_3(alimtalk_variables)
            elif (len(send_contents) == 4):
                message = self.BIZPPURIO_ALIMTALK_TEMPLATE_4(alimtalk_variables)
            elif (len(send_contents) == 5):
                message = self.BIZPPURIO_ALIMTALK_TEMPLATE_5(alimtalk_variables)
            elif (len(send_contents) == 6):
                message = self.BIZPPURIO_ALIMTALK_TEMPLATE_6(alimtalk_variables)
            elif (len(send_contents) == 7):
                message = self.BIZPPURIO_ALIMTALK_TEMPLATE_7(alimtalk_variables)
            elif (len(send_contents) >= 8):
                message = self.BIZPPURIO_ALIMTALK_TEMPLATE_8(alimtalk_variables)

            # 요청 객체가 None이면 예외 처리
            if message is None or message == "":
                return SendResult(isSuccess=False, message="Bad Parameter : No Template Message", sendIds=[], sendType=self.send_type, receiver=receiver.mberTelno)

            # access_token이 없거나 만료되었으면 토큰 갱신
            if not self.is_token_valid():
                self.refresh_auth_token()

            # 토큰 갱신 후에도 유효하지 않다면 에러 반환
            if not self.is_token_valid():
                return SendResult(isSuccess=False, message="AccessToken is not validated.", sendIds=[], sendType=self.send_type, receiver=receiver.mberTelno)
            
                
            # 메시지 API를 보내기 위한 요청 목록 생성
            aiSendModel = SendModel()
            aiSendModel.mber_telno = receiver.get_decrypt_mberTelno()
            aiSendModel.send_type = "ai"
            
            if not hasattr(receiver, "kakaoId" or receiver.mberTelno == None):
                aiSendModel.template_code = "dailytalk_kakao_inapp_browser"
                aiSendModel.button_url = self.kakao_inapp_browser_url
            else:
                aiSendModel.template_code = "dailytalk_kakao_direct_login"
                aiSendModel.button_url = self.kakao_direct_login_url
            
            aiSendModel.template_msg = message
            
            # 비즈뿌리오 API 요청 만들기
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
                return SendResult(isSuccess=False, message="Request is None.", sendIds=[], sendType=self.send_type, receiver=receiver.mberTelno)

            # 메시지 API 요청 및 결과 처리
            response = self.post_request(self.message_url, self.access_token, requests[receiver.get_decrypt_mberTelno()])

            # 응답 처리
            return self.return_response(receiver=receiver, response=response, contents=contents)
        except Exception as ex:
            return self.return_exception_response(receiver=receiver, ex=ex)


    

        
		

        