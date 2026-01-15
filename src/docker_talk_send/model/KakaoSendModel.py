from datetime import datetime
import requests

from docker_talk_send.model.SendResult import SendResult
from ksubscribe_share.db.dbmodelV2.memberVO import MemberVO
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO


class KakaoSendModel:
    def __init__(self, api_key: str, sender_key: str, user_id: str, plus_id: str, sender_number: str):
        self.initialized = False
        self.send_type = "Kakao"
        
        # api 호출 url 들
        self.authUrl = "https://kakaoapi.aligo.in/akv10/profile/auth/" # 요청을 던지는 URL, 현재는 카카오채널 인증
        self.categoryUrl = "https://kakaoapi.aligo.in/akv10/category/" # 요청을 던지는 URL, 카카오채널 카테고리 조회
        self.profileAddUrl = "https://kakaoapi.aligo.in/akv10/profile/add/" # 요청을 던지는 URL, 친구등록 심사요청
        self.templateAddUrl = "https://kakaoapi.aligo.in/akv10/template/add/" # 요청을 던지는 URL, 템플릿 생성
        self.templateListUrl = "https://kakaoapi.aligo.in/akv10/template/list/" # 요청을 던지는 URL, 등록된 템플릿 리스트
        self.alimtalkSendUrl = "https://kakaoapi.aligo.in/akv10/alimtalk/send/" # 요청을 던지는 URL, 알림톡 전송
        self.friendSendUrl = "https://kakaoapi.aligo.in/akv10/friend/send/" # 요청을 던지는 URL, 친구톡 전송
        
        self.api_key = api_key
        self.sender_key = sender_key
        self.user_id = user_id
        self.plus_id = plus_id
        self.sender_number = sender_number # 알리고에 등록된 번호만 send 할 수 있음.
        
        # self.apiKey = "s9otab042ooluwh1q6icg6f7uuqybegv"
        # self.senderKey = "606c5fb72ec7cf6562366937c71e44c6c5c6f7b7"
        # self.userid = "mycontents"
        # self.plusid = "@mycontents"
        # self.sender = "01044683990" # 알리고에 등록된 번호만 send 할 수 있음.
        
    def initialize(self):
        try:
            # 알리고 kakao api 는 별도의 initialize 가 필요 없는 것 같음.. 추후 생길 시 구현할 예정.
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
    
    # request 에 대한 response 를 SendResult 로 리턴해주는 함수
    def return_response(self, receiver: MemberVO, response: dict):
        if (response['code'] is not "0"):
            sendResult = SendResult(sendType=self.send_type, receiver=receiver, isSuccess=True, message=response)
            return sendResult
        
        else:
            sendResult = SendResult(sendType=self.send_type, receiver=receiver, isSuccess=False, message=response)
            return sendResult
    
    # 템플릿 리스트 요청
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
                    
            template_list_response = requests.post(self.templateListUrl, data=sms_data)
            response = template_list_response.json()
            
            return self.return_response(receiver=receiver, response=response)
            
        except Exception as ex:
            sendResult = SendResult(sendType=self.send_type, receiver=receiver.mberEmail, isSuccess=False, message=ex)
            return sendResult
        
    # 알림톡 전송    
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
            
            alimtalk_send_response = requests.post(self.alimtalkSendUrl, data=sms_data)
            return self.return_response(receiver=receiver, response=alimtalk_send_response)
        
        except Exception as ex:
            sendResult = SendResult(sendType=self.send_type, receiver=receiver.mberEmail, isSuccess=False, message=ex)
            return sendResult
            
        
    
    # 친구톡 전송
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
    