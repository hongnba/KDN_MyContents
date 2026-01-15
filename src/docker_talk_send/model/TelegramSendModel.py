
import asyncio
import base64
from collections import defaultdict
from datetime import date
import json
from urllib.parse import urlencode
import zlib
import telegram

from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO
from docker_talk_send.model.SendResult import SendResult
from ksubscribe_share.db.dbmodelV2.memberVO import MemberVO
from ksubscribe_share.logger import Logger
import ksubscribe_share.config as Conf

class TelegramSendModel:
    def __init__(self, token):
        self.token = token
        self.initialized = False
        self.send_type = "Telegram"
        self.base_url = Conf.CONTENTS_BASE_URL
        logger = Logger()
        self.docker_collect_logger = logger.setup_logger(logger.docker_talk_send_logger_name)
        
    def initialize(self):
        try:
            self.bot = telegram.Bot(token=self.token)
            # 봇 정보 가져오기
            # 비동기 함수 실행을 동기적으로 처리
            bot_info = asyncio.get_event_loop().run_until_complete(self.bot.get_me())
            print("봇이 정상적으로 생성되었습니다!")
            print(f"봇 이름: {bot_info.first_name}")
            print(f"봇 사용자명: @{bot_info.username}")
            print(f"봇 ID: {bot_info.id}")
            self.initialized = True
        except telegram.error.TelegramError as e:
            print("봇 생성 실패:", e)
        except Exception as ex:
            print(ex)
            self.initialized = False
    
    # request 에 대한 response 를 SendResult 로 리턴해주는 함수
    def return_response(self, receiver: MemberVO, response: dict[str, str], contents: list[ContentsVO]):
        self.docker_collect_logger.info(f'return_response : {response}')
        if not response:
            contentIds = [str(content._id) for content in contents]
            sendResult = SendResult(sendType=self.send_type, receiver=receiver, isSuccess=True, message=response, sendIds=contentIds)
            return sendResult
        
        else:
            sendResult = SendResult(sendType=self.send_type, receiver=receiver, isSuccess=False, message=response, sendIds=[])
            return sendResult
    
    def return_customize_error_response(self, receiver: MemberVO, message: str):
        response = {}
        response["ex"] = str(message)
        self.docker_collect_logger.info(f'return_customize_error_response : {message}')
        sendResult = SendResult(sendType=self.send_type, receiver=receiver, isSuccess=False, message=response, sendIds=[])
        return sendResult
    
    def return_exception_response(self, receiver: MemberVO, ex: Exception):
        response = {}
        response["ex"] = str(ex)
        self.docker_collect_logger.info(f'return_exception_response : {str(ex)}')
        sendResult = SendResult(sendType=self.send_type, receiver=receiver, isSuccess=False, message=response, sendIds=[])
        return sendResult
    
    async def send_message(self, chat_id, feed):
        await self.bot.send_message(
            chat_id=chat_id,
            text=feed,
            disable_web_page_preview=True,
            parse_mode='html'
        )
    
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
    
    def send_total(self, receiver: MemberVO, contents: list[ContentsVO]):
        try:
            # initialize 체크
            if not self.initialized:
                return self.return_customize_error_response(receiver=receiver, message=f"텔레그램 봇 [{self.token}] 이 유효하지 않습니다.")

            if contents is None or len(contents) == 0:
                return self.return_customize_error_response(receiver=receiver, message=f"전송할 컨텐츠가 없습니다.")

            if receiver == None or receiver.teleChatId == None or receiver.teleChatId == "":
                return self.return_customize_error_response(receiver=receiver, message=f"사용자의 텔레그램 정보가 없습니다.")
            
            tele_today = date.today().strftime("%Y.%m.%d")
            max_count = 20
            content_list : list[ContentsVO] = []
            
            # 제목 작성
            feed = ""
            feed += '한전KDN 콘텐츠 구독 서비스\n'
            
            # contents 개수가 많은 경우 제한하기
            if (len(contents) > max_count):
                    content_list = contents[:max_count]
                    feed += f'{tele_today} 맞춤 콘텐츠 (총 {len(content_list)}건)\n'
                    feed += '요약된 콘텐츠입니다. 이외 콘텐츠는 포털에서 확인 바랍니다.\n\n'
            else: # 아닌 경우 그냥 그대로 사용
                content_list = contents
                feed += f'{tele_today} 맞춤 콘텐츠 (총 {len(content_list)}건)\n\n'
            
            # 1. 컨텐츠 점수 높은 상위 20 개만 전송
            for content in content_list:
                # 기관명과 카테고리명 작성
                if content.categoryName == content.contentsOrgName:
                    feed += f'<b>■ {content.contentsOrgName}</b>\n'
                else:
                    feed += f'<b>■ {content.categoryName}-{content.contentsOrgName}</b>\n'
                
                # 컨텐츠에서 '사전 정의된 키워드'를 사용자가 '구독한 키워드'에 포함되어 있는지 확인
                filter_set = set()
                if hasattr(receiver, "keywordSubscribe"): # 구독한 키워드 정보가 없으면 pass
                    filter_set = set(receiver.keywordSubscribe)  # set으로 변환
                    
                filtered_items = []
                if hasattr(content, "contentsMeta"): # not 제거할 것.
                    if content.contentsMeta != None and hasattr(content.contentsMeta, "predKeywords"):
                        filtered_items = [item for item in (content.contentsMeta.predKeywords or {}) if item in filter_set]
                
                feed += f'매칭된 키워드 : '
                # 해당 되는 키워드가 없으면
                if not filtered_items:
                    feed += f'없음. '
                
                else:
                    # 포함되어 있는 것들만 메시지에 추가하기
                    for item in filtered_items:
                        feed += f'#{item} '
                feed += '\n'
                    
                # 컨텐츠 제목 넣기
                feed += f'- 제목 : <b>{content.title}</b>\n'
                
                # 컨텐츠를 볼 수 있는 url 넣기.
                reordered_list = [content] + [item for item in content_list if item is not content]
                contents_url = self.make_url_from_contents_list(reordered_list)
                feed += '\n'
                # feed += f'☞ <a href="{contents_url}">[링크로 이동하려면 클릭]</a>\n\n' # 우선 필요 없을듯함.
                    
            feed += f'<a href="{self.base_url}">자세한 내용은 포털에서 확인하세요</a>'
                        
            if len(content_list) > 0:
                loop = asyncio.get_event_loop()
                if loop.is_closed():  # 이벤트 루프가 닫혀 있다면 새로 생성
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                response = loop.run_until_complete(self.send_message(receiver.teleChatId, feed))
                # 동기 함수에서 호출
                # response = asyncio.run(self.send_message(receiver.teleChatId, feed))
                return self.return_response(receiver=receiver, response=response, contents=content_list)
                
            return self.return_customize_error_response(receiver=receiver, message=f"전송할 컨텐츠가 없습니다.")            
            
        except Exception as ex:
            return self.return_exception_response(receiver=receiver, ex=ex)
        
    def send_devide_org(self, receiver: MemberVO, title: str, contents: list[ContentsVO]):
        sendResult = SendResult(sendType=self.send_type, receiver=receiver.teleChatId, isSuccess=True, message=f"")
        
        try:
            # initialize 체크
            if not self.initialized:
                sendResult = SendResult(sendType="Telegram", receiver=receiver, isSuccess=False, message=f"텔레그램 봇 [{self.token}] 이 유효하지 않습니다.")
                return sendResult

            if contents is None or len(contents) == 0:
                sendResult = SendResult(sendType="Telegram", receiver=receiver, isSuccess=False, message=f"전송할 컨텐츠가 없습니다.")
                return

            if receiver == None or receiver.teleChatId == None or receiver.teleChatId == "":
                sendResult = SendResult(sendType="Telegram", receiver=receiver, isSuccess=False, message=f"사용자의 텔레그램 정보가 없습니다.")
                return
            
            tele_today = date.today().strftime("%Y.%m.%d")
            max_count = 20
            
            # contents list 그룹화 작업
            grouped_dict = defaultdict(list)

            for content in contents:
                grouped_dict[content.contentsOrgName].append(content)

            page_idx = 1
            total_page = (len(grouped_dict)) # 총 페이지 생성
            
            # 2. 기관 마다 별도의 feed 로 전송함. ex) 10 개 기관인 경우 10번에 나눠서 전송
            for key, content_list in grouped_dict.items():
                # 제목 작성
                feed = ""
                feed += '한전KDN 콘텐츠 구독 서비스\n'
                
                # 한 기관당 최대 20개만 보내도록 slice
                if (len(content_list) > 20):
                    content_list = content_list[:max_count]
                    feed += f'{tele_today} 맞춤 콘텐츠 (총 {len(content_list)}건)({page_idx}/{total_page})\n'
                    feed += '요약된 콘텐츠입니다. 이외 콘텐츠는 포털에서 확인 바랍니다.\n\n'
                else:
                    feed += f'{tele_today} 맞춤 콘텐츠 (총 {len(content_list)}건)({page_idx}/{total_page})\n\n'
                
                # 컨텐츠 반복해서 내용 채우기
                for content in content_list:
                    # 기관명과 카테고리명 작성
                    if content.categoryName == content.contentsOrgName:
                        feed += f'<b>■ {content.contentsOrgName}</b>\n'
                    else:
                        feed += f'<b>■ {content.categoryName}-{content.contentsOrgName}</b>\n'
                    
                    # 컨텐츠에서 '사전 정의된 키워드'를 사용자가 '구독한 키워드'에 포함되어 있는지 확인
                    filter_set = set()
                    if hasattr(receiver, "keywordSubscribe"): # 구독한 키워드 정보가 없으면 pass
                        filter_set = set(receiver.keywordSubscribe)  # set으로 변환
                    filtered_items = [item for item in content.contentsMeta.predKeywords if item in filter_set]
                    
                    feed += f'매칭된 키워드 : '
                    # 해당 되는 키워드가 없으면
                    if not filtered_items:
                        # 우선은 아무것도 작성하지 않음.
                        feed += f'없음. '
                    
                    else:
                        # 포함되어 있는 것들만 메시지에 추가하기
                        for item in filtered_items:
                            feed += f'#{item} '
                    feed += '\n'
                        
                    # 컨텐츠 제목 넣기
                    feed += f'- 제목 : <b>{content.title}</b>\n'
                    
                    # 컨텐츠를 볼 수 있는 url 넣기.
                    reordered_list = [content] + [item for item in content_list if item is not content]
                    contents_url = self.make_url_from_contents_list(reordered_list)
                    feed += f'☞ <a href="{contents_url}">[링크로 이동하려면 클릭]</a>\n\n'
                    
                feed += f'<a href="{self.base_url}">자세한 내용은 포털에서 확인하세요</a>'
                        
                if len(content_list) > 0:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():  # 이벤트 루프가 닫혀 있다면 새로 생성
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                    response = loop.run_until_complete(self.send_message(receiver.teleChatId, feed))
                    # 동기 함수에서 호출
                    # response = asyncio.run(self.send_message(receiver.teleChatId, feed))
                    # self.bot.sendMessage(chat_id=receiver.teleChatId, text=feed, disable_web_page_preview=True, parse_mode = 'html')
                    sendResult = SendResult(sendType=self.send_type, receiver=receiver.teleChatId, isSuccess=True, message=f"Send Success ({page_idx}/{total_page})")
                    sendResult.message += "Send Success ({page_idx}/{total_page})"
                # 페이지 수 증가
                page_idx += 1
                
            return sendResult
            
        except Exception as ex:
            sendResult.isSuccess = False
            sendResult.message += str(ex)
            # sendResult = SendResult(sendType=self.send_type, receiver=receiver, isSuccess=False, message=ex)
            return sendResult

    def send_feed_message_to_member(self, receiver: MemberVO, feed: str):
        try:
            # initialize 체크
            if not self.initialized:
                response = {}
                response["ex"] = str("텔레그램 봇 [{self.token}] 이 유효하지 않습니다.")
                self.docker_collect_logger.info(str("텔레그램 봇 [{self.token}] 이 유효하지 않습니다."))
                return response

            if receiver == None or receiver.teleChatId == None or receiver.teleChatId == "":
                response = {}
                response["ex"] = str(f"[{receiver.mberId}] 사용자의 텔레그램 정보가 없습니다.")
                self.docker_collect_logger.info(str(f"[{receiver.mberId}] 사용자의 텔레그램 정보가 없습니다."))
                return response
        
            loop = asyncio.get_event_loop()
            if loop.is_closed():  # 이벤트 루프가 닫혀 있다면 새로 생성
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            response = loop.run_until_complete(self.send_message(receiver.teleChatId, feed))
            # 동기 함수에서 호출
            # response = asyncio.run(self.send_message(receiver.teleChatId, feed))
            self.docker_collect_logger.info(f'telegram send response : {response}')
            return response
            
        except Exception as ex:
            response = {}
            response["ex"] = str(ex)
            self.docker_collect_logger.info(f'send_feed_message_to_member Exception : {str(ex)}')
            return response
        

    def send_feed_message(self, telechatId: str, feed: str):
        try:
            # initialize 체크
            if not self.initialized:
                response = {}
                response["ex"] = str("텔레그램 봇 [{self.token}] 이 유효하지 않습니다.")
                self.docker_collect_logger.info(str("텔레그램 봇 [{self.token}] 이 유효하지 않습니다."))
                return response

            if telechatId == None or telechatId == None or telechatId == "":
                response = {}
                return response
        
            loop = asyncio.get_event_loop()
            if loop.is_closed():  # 이벤트 루프가 닫혀 있다면 새로 생성
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            response = loop.run_until_complete(self.send_message(telechatId, feed))
            # 동기 함수에서 호출
            # response = asyncio.run(self.send_message(receiver.teleChatId, feed))
            self.docker_collect_logger.info(f'telegram send response : {response}')
            return response
            
        except Exception as ex:
            response = {}
            response["ex"] = str(ex)
            return response
    def send_feed_message_in_thread(self, telechatId: str, feed: str):
        try:
            # initialize 체크
            if not self.initialized:
                response = {}
                response["ex"] = str("텔레그램 봇 [{self.token}] 이 유효하지 않습니다.")
                self.docker_collect_logger.info(str("텔레그램 봇 [{self.token}] 이 유효하지 않습니다."))
                return response

            if telechatId == None or telechatId == None or telechatId == "":
                response = {}
                return response
        
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try: 
                response = loop.run_until_complete(self.send_message(telechatId, feed))
            # 동기 함수에서 호출
            # response = asyncio.run(self.send_message(receiver.teleChatId, feed))
            except Exception as ex:
                response = {}
                response["ex"] = str(ex) 
            finally:
                loop.close()
            self.docker_collect_logger.info(f'telegram send response : {response}')
            return response
            
        except Exception as ex:
            response = {}
            response["ex"] = str(ex)
            return response