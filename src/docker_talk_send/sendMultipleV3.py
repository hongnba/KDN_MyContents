from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from datetime import datetime
import sys
import time
import telegram
from telegram.ext import CallbackContext

from docker_talk_send.model.EmailSendModelV2 import EmailSendModel
from docker_talk_send.model.TelegramSendModel import TelegramSendModel
from docker_talk_send.model.KakaoSendModelV3 import KakaoSendModel

from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO
from ksubscribe_share.db.dbmodelV2.memberVO import MemberVO
from ksubscribe_share.db.service.memberService import MemberService
from ksubscribe_share.db.service.baseQueryService import BaseQueryService
import ksubscribe_share.config as Conf
from ksubscribe_share.db.dbmodelV2.contentsSendHistoryVO import ContentsSendHistoryVO
from docker_talk_send.model.SendResult import SendResult
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.service.contentsService import ContentsService
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.logger import Logger
from ksubscribe_share.db.service.contentsSendHistoryService import ContentsSendHistoryService

logger = Logger()
docker_collect_logger = logger.setup_logger(logger.docker_talk_send_logger_name)

# 콘텐츠 제목에 키워드가 존재하는지 매칭하는 함수
def count_matching_words(target: str, word_list: list[str]) -> tuple[int, list[str]]:
    matched_words = [word for word in word_list if word in target]
    return len(matched_words), matched_words

# 추천 알고리즘 수정 요청 - 콘텐츠의 제목에 사용자가 구독한 키워드가 매칭 되는 것을 우선적으로 추천
# History
#  1. 콘텐츠의 분석 결과 키워드가 정확하게 추출되지 않음.
#  2. 정확하지 않은 키워드로 콘텐츠를 추천하다보니 사용자의 입장에서 추천이 이상하게 된다고 생각이 됨.
#  3. 추천 방식을 추출한 키워드가 아니라 제목에 키워드가 매칭되는지로 수정
# 우선순위
#  1. 내가 구독한 기관에서 발행한 콘텐츠 + 제목에 내가 구독한 키워드와 매칭됨
#  2. 내가 구독한 기관에서 발행한 콘텐츠
#  3. 제목에 내가 구독한 키워드와 매칭됨
#  4. 카카오톡 전송은 최대 8개지만, SendHistory 에는 20개 저장하도록 수정할 것.
def recommend_contents(mberId: str, contents: list[ContentsVO]):
    try:
        if (contents is None or len(contents) <= 0):
            return None, None
    
        memberService = MemberService()
        # contentsOrgService = ContentsOrgService()
        
        # 1. 유저정보 조회
        user: MemberVO = MemberService.getMember(memberService, mberId)
        
        # 추천 콘텐츠 목록
        recommended = []
        # 추천 알고리즘에 사용된 키워드 목록 
        used_keyword = []
        
        #  1번 우선 순위 목록 (내가 구독한 기관에서 발행한 콘텐츠 + 제목에 내가 구독한 키워드와 매칭됨)
        first_priority_list = []
        #  2번 우선 순위 목록 (내가 구독한 기관에서 발행한 콘텐츠)
        second_priority_list = []
        #  3번 우선 순위 목록 (제목에 내가 구독한 키워드와 매칭됨)
        third_priority_list = []
        
        # orgid 가 있으면 실행. 특정 Property 에 값이 없으면 MongoDB 에 저장하지 않는 경우가 있으므로 hasattr() 를 실행안하면 에러가 날 수 있음.
        # if hasattr(user, "orgId"):
        #     if (user.orgId != None and user.orgId != ''):
        #         # 2. 내 기관 정보 가져오기
        #         myOrg: ContentsOrgVO = ContentsOrgService.findOrg(contentsOrgService, user.orgId)
            
        #         # 기관 정보가 없으면 활용 안함.
        #         if myOrg and myOrg != None:
        #             org_member_keywords_dict  = get_org_member_subscribe_keywords(mberId, myOrg.orgId)
        
        my_subs_keyword: list[str] = []
        # 내가 구독한 키워드
        if hasattr(user, "keywordSubscribe"):
            my_subs_keyword = user.keywordSubscribe
        
        # 내가 구독한 기관 목록
        org_list = [subs_org.orgId for subs_org in user.contentsOrgSubscribe]
        
        # 모든 컨텐츠로부터 데이터 계산
        # 내가 구독한 기관에 대한 컨텐츠로만 계산하고 싶지만, 구독한 경우가 없을 것을 고려해서 전체 컨텐츠로 계산
        for content in contents:
            try:
                # 내가 구독한 기관에서 발행한 콘텐츠 여부
                is_match_org = False
                # 제목에 내가 구독한 키워드와 매칭 여부
                is_match_keyword = False
                
                # 내가 구독한 기관에 관련된 점수
                org_score = 0
                # 사용자가 구독한 키워드에 관련된 점수
                keyword_match_score = 0
                
                # 내가 구독한 기관이 발행한 컨텐츠인가?
                if (content.contentsOrgId in org_list):
                    org_score += 100 # 큰 점수를 줘서 구독한 기관의 키워드의 우선순위를 높힘.
                    is_match_org = True
                
                # predKeywords 선언 predKeywords 는 Dict[str, int] 임.
                # content_predKeywords = None
                # content_predKeywords_keys = []
                
                # if hasattr(content, "contentsMeta"):
                #     if hasattr(content.contentsMeta, "predKeywords"):
                #         content_predKeywords = content.contentsMeta.predKeywords
                #         content_predKeywords_keys = list(content_predKeywords.keys())
                
                # predKeywords 이 없을 경우 빈 값으로 적용
                # if (content_predKeywords is None):
                #     content_predKeywords = {}
                #     content_predKeywords_keys = []
                
                # title 이 있으면 실행. 특정 Property 에 값이 없으면 MongoDB 에 저장하지 않는 경우가 있으므로 hasattr() 를 실행안하면 에러가 날 수 있음.
                if hasattr(content, "title"):
                    # 콘텐츠의 제목에 키워드가 매칭되는지 확인
                    match_cnt, match_keywords = count_matching_words(content.title, my_subs_keyword)
                    if (match_cnt > 0):
                        # 사용된 키워드 정보 추가
                        used_keyword = list(set(used_keyword + match_keywords))
                        # 매칭된 키워드 점수 계산 (매칭된 키워드가 많을 수록 높은 점수)
                        keyword_match_score = match_cnt * 1000 # 큰 점수를 줘서 키워드 매칭의 우선순위를 높힘.
                        is_match_keyword = True
                
                total_score = org_score + keyword_match_score
                
                if (is_match_org and is_match_keyword):
                    first_priority_list.append({"id": str(content._id), "score": total_score, "value": content})
                elif (is_match_org):
                    second_priority_list.append({"id": str(content._id), "score": total_score, "value": content})
                elif (is_match_keyword):
                    third_priority_list.append({"id": str(content._id), "score": total_score, "value": content})
                
            except Exception as e:
                docker_collect_logger.info(f"Error: {e}")
                continue
        
        # 점수 기준 정렬
        first_priority_list.sort(key=lambda x: x["score"], reverse=True)
        second_priority_list.sort(key=lambda x: x["score"], reverse=True)
        third_priority_list.sort(key=lambda x: x["score"], reverse=True)
        
        recommended = first_priority_list + second_priority_list + third_priority_list

        docker_collect_logger.info(f"member : {mberId} | 총 recommended 개수 : {len(recommended)} | 1순위 : {len(first_priority_list)} | 2순위 : {len(second_priority_list)} | 3순위 : {len(third_priority_list)} | 구독한 기관 수 : {len(user.contentsOrgSubscribe)} | 구독한 키워드 수 : {len(my_subs_keyword)}")
        return recommended, used_keyword
    except Exception as ex:
        docker_collect_logger.info(f"콘텐츠 추천 알고리즘 실행 중 Exception 발생 : {str(ex)}")
        return contents, []

def send_history_update(send_history: ContentsSendHistoryVO, send_result: SendResult):
    if (send_result.sendType == "Telegram"):
        send_history.telegramSendDt = datetime.now()
        send_history.telegramSendYN = 'Y'
        send_history.telegramSendSuccessYN = "Y" if send_result.isSuccess else "N"
        send_history.telegramSendIds = send_result.sendIds
        send_history.mergedSendIds = list(set(send_history.mergedSendIds) | set(send_result.sendIds))
        send_history.telegramSendResponse = send_result.message
        
    elif (send_result.sendType == "Kakao"):
        send_history.kakaoSendDt = datetime.now()
        send_history.kakaoSendYN = 'Y'
        send_history.kakaoSendSuccessYN = "Y" if send_result.isSuccess else "N"
        send_history.kakaoSendIds = send_result.sendIds
        send_history.mergedSendIds = list(set(send_history.mergedSendIds) | set(send_result.sendIds))
        send_history.kakaoSendResponse = send_result.message
        
    elif (send_result.sendType == "Email"):
        send_history.emailSendDt = datetime.now()
        send_history.emailSendYN = 'Y'
        send_history.emailSendSuccessYN = "Y" if send_result.isSuccess else "N"
        send_history.emailSendIds = send_result.sendIds
        send_history.mergedSendIds = list(set(send_history.mergedSendIds) | set(send_result.sendIds))
        send_history.emailSendResponse = send_result.message
        
    return send_history

def start(update: telegram.Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    update.message.reply_text(f"Your Chat ID is: {chat_id}")
    print(f"Chat ID: {chat_id}")  # 서버 콘솔에 출력

def send_kakao_multiple(member_list: list[MemberVO], contents_dict: dict[str, tuple[list[object], list[str]]], exec_time: datetime):
    docker_collect_logger.info(f"전송할 총 유저 수 : {len(member_list)}")
    # 전송 결과 정보를 담을 리스트
    send_results: list[ContentsSendHistoryVO] = []
    # 모든 멤버를 반복 - 카카오톡 보내기
    for member in member_list:
        try:
            if not hasattr(member, "mberId"): # 멤버 정보가 없으면 pass
                continue
        
            # 멤버에게 보낼 contents 만들기
            recommand_contents, used_keyword = contents_dict[member.mberId]
            
            contents = [content["value"] for content in recommand_contents]
            
            docker_collect_logger.info(f'멤버 : [{member.mberId}] 컨텐츠 전송 시작')
            
            docker_collect_logger.info(f'멤버 : [{member.mberId}] 의 전송 이력 확인')
            
            send_history_service = ContentsSendHistoryService()
            
            # 금일 이미 존재하는 전송 이력
            previously_send_history: ContentsSendHistoryVO = send_history_service.find_send_history_by_user_and_date(member.mberId, exec_time)
            
            # 새롭게 저장할 전송 이력
            send_history = ContentsSendHistoryVO()
            
            # 기존에 존재하는 Send History 가 없을 경우 => 기본 객체 만들기
            if (previously_send_history == None):
                docker_collect_logger.info(f'멤버 : [{member.mberId}] 의 금일 기존 전송 이력 못찾음')
                send_history.mberId = member.mberId
                send_history.keywords = used_keyword
                send_history.telegramSendYN = 'N'
                send_history.kakaoSendYN = 'N'
                send_history.emailSendYN = 'N'
                send_history.telegramSendSuccessYN = 'N'
                send_history.kakaoSendSuccessYN = 'N'
                send_history.emailSendSuccessYN = 'N'
                send_history.telegramSendIds = []
                send_history.kakaoSendIds = []
                send_history.emailSendIds = []
                send_history.telegramSendResponse = {}
                send_history.kakaoSendResponse = {}
                send_history.emailSendResponse = {}
                send_history.sendDt = datetime.now()
            else:
                send_history = previously_send_history
                docker_collect_logger.info(f'멤버 : [{member.mberId}] 의 금일 기존 전송 이력 찾음 : {send_history}')
            
            # send_history.telegramSendYN = 'N'
            send_history.kakaoSendYN = 'N'
            # send_history.emailSendYN = 'N'
            # send_history.telegramSendSuccessYN = 'N'
            send_history.kakaoSendSuccessYN = 'N'
            # send_history.emailSendSuccessYN = 'N'
            # send_history.telegramSendIds = []
            send_history.kakaoSendIds = []
            # send_history.emailSendIds = []
            # send_history.telegramSendResponse = {}
            send_history.kakaoSendResponse = {}
            # send_history.emailSendResponse = {}
                    
            if member.kakaoReceiveYN == "Y" and send_kakao_manager.initialized:
                max_retries = 3
                for attempt in range(1, max_retries + 1):
                    try:
                        docker_collect_logger.info(f'멤버 : [{member.mberId}] 카카오 전송 여부 : O, 전송 중... 전송 시도 ({attempt}/{max_retries})')
                        send_kakao_result = send_kakao_manager.send_kakao_bizppurio(member, contents)
                        
                        if (send_kakao_result.isSuccess):
                            docker_collect_logger.info(f'멤버 : [{member.mberId}] 카카오 전송 결과 : {send_kakao_result.isSuccess} 전송 종료')
                            send_history = send_history_update(send_history=send_history, send_result=send_kakao_result)
                            break
                        else:
                            docker_collect_logger.info(f'멤버 : [{member.mberId}] 카카오 전송 결과 : {send_kakao_result.isSuccess}')
                            send_history = send_history_update(send_history=send_history, send_result=send_kakao_result)
                            time.sleep(1)  # 재시도 전 대기
                        
                    except Exception as ex:
                        # Exception 발생 시 수동으로 send_history 수정
                        send_history.kakaoSendYN = member.kakaoReceiveYN
                        send_history.kakaoSendSuccessYN = 'N'
                        send_history.kakaoSendResponse = (str(ex))
                        docker_collect_logger.info(f'Kakao Send Exception 발생 : {(str(ex))}')
                        time.sleep(1)  # 재시도 전 대기
            else:
                if (not send_kakao_manager.initialized):
                    send_history.kakaoSendResponse = "카카오 초기화 실패"
                docker_collect_logger.info(f'멤버 : [{member.mberId}] 카카오 전송 여부 : X ( 사용자 수신 여부 : {member.kakaoReceiveYN} | Manager 초기화 여부 : {send_kakao_manager.initialized})')
                send_history.kakaoSendYN = member.kakaoReceiveYN
                send_history.kakaoSendSuccessYN = 'N'
                
            docker_collect_logger.info(f'멤버 : [{member.mberId}] 컨텐츠 전송 종료\n\n')
            
            # 전송 여부 결과를 저장 (로그에서 통계 낼 때 사용)
            send_results.append(send_history)
            
            # 3 가지 중에 하나라도 전송한 사람에 대해서면 전송 결과를 저장
            if (member.kakaoReceiveYN == "Y"):
                # 이미 전송한 이력이 없을 경우 => 새로 insert
                if (previously_send_history == None):
                    send_history.regDt = datetime.now()
                    insert_res = BaseQueryService.insert_one(send_history)
                    docker_collect_logger.info(f'멤버 : [{member.mberId}] DB 저장 여부 : {insert_res}\n\n')
                # 이미 전송한 이력이 있을 경우 => 기존 데이터 Update
                else:
                    update_res = BaseQueryService.update_one(send_history)
                    docker_collect_logger.info(f'멤버 : [{member.mberId}] DB 업데이트 여부 : {update_res}\n\n')
        
        except Exception as ex:
            docker_collect_logger.info(f'send_kakao_multiple Exception 발생 : {(str(ex))}')
            
    return send_results


def send_telegram_multiple(member_list: list[MemberVO], contents_dict: dict[str, tuple[list[object], list[str]]], exec_time: datetime):
    docker_collect_logger.info(f"전송할 총 유저 수 : {len(member_list)}")
    # 전송 결과 정보를 담을 리스트
    send_results: list[ContentsSendHistoryVO] = []
    # 모든 멤버를 반복 - 텔레그램 보내기
    for member in member_list:
        try:
            if not hasattr(member, "mberId"): # 멤버 정보가 없으면 pass
                continue
        
            # 멤버에게 보낼 contents 만들기
            recommand_contents, used_keyword = contents_dict[member.mberId]
            
            contents = [content["value"] for content in recommand_contents]
            
            docker_collect_logger.info(f'멤버 : [{member.mberId}] 컨텐츠 전송 시작')
            
            docker_collect_logger.info(f'멤버 : [{member.mberId}] 의 전송 이력 확인')
            
            send_history_service = ContentsSendHistoryService()
            
            # 금일 이미 존재하는 전송 이력
            previously_send_history: ContentsSendHistoryVO = send_history_service.find_send_history_by_user_and_date(member.mberId, exec_time)
            
            # 새롭게 저장할 전송 이력
            send_history = ContentsSendHistoryVO()
            
            # 기존에 존재하는 Send History 가 없을 경우 => 기본 객체 만들기
            if (previously_send_history == None):
                docker_collect_logger.info(f'멤버 : [{member.mberId}] 의 금일 기존 전송 이력 못찾음')
                send_history.mberId = member.mberId
                send_history.keywords = used_keyword
                send_history.telegramSendYN = 'N'
                send_history.kakaoSendYN = 'N'
                send_history.emailSendYN = 'N'
                send_history.telegramSendSuccessYN = 'N'
                send_history.kakaoSendSuccessYN = 'N'
                send_history.emailSendSuccessYN = 'N'
                send_history.telegramSendIds = []
                send_history.kakaoSendIds = []
                send_history.emailSendIds = []
                send_history.telegramSendResponse = {}
                send_history.kakaoSendResponse = {}
                send_history.emailSendResponse = {}
                send_history.sendDt = datetime.now()
            else:
                send_history = previously_send_history
                docker_collect_logger.info(f'멤버 : [{member.mberId}] 의 금일 기존 전송 이력 찾음 : {send_history}')
            
            send_history.telegramSendYN = 'N'
            # send_history.kakaoSendYN = 'N'
            # send_history.emailSendYN = 'N'
            send_history.telegramSendSuccessYN = 'N'
            # send_history.kakaoSendSuccessYN = 'N'
            # send_history.emailSendSuccessYN = 'N'
            send_history.telegramSendIds = []
            # send_history.kakaoSendIds = []
            # send_history.emailSendIds = []
            send_history.telegramSendResponse = {}
            # send_history.kakaoSendResponse = {}
            # send_history.emailSendResponse = {}
            
            if member.teleReceiveYN == "Y" and send_telegram_manager.initialized:
                max_retries = 3
                for attempt in range(1, max_retries + 1):
                    try:
                        docker_collect_logger.info(f'멤버 : [{member.mberId}] 텔레그램 전송 여부 : O, 전송 중... 전송 시도 ({attempt}/{max_retries})')
                        send_telegram_result = send_telegram_manager.send_total(member, contents)
                        if (send_telegram_result.isSuccess):
                            docker_collect_logger.info(f'멤버 : [{member.mberId}] 텔레그램 전송 결과 : {send_telegram_result.isSuccess} 전송 종료')    
                            send_history = send_history_update(send_history=send_history, send_result=send_telegram_result)
                            break
                        else:
                            docker_collect_logger.info(f'멤버 : [{member.mberId}] 텔레그램 전송 결과 : {send_telegram_result.isSuccess}')
                            send_history = send_history_update(send_history=send_history, send_result=send_telegram_result)
                            time.sleep(1)  # 재시도 전 대기
                        
                    except Exception as ex:
                        # Exception 발생 시 수동으로 send_history 수정
                        send_history.telegramSendYN = member.teleReceiveYN
                        send_history.telegramSendSuccessYN = 'N'
                        send_history.telegramSendResponse = (str(ex))
                        docker_collect_logger.info(f'Telegram Send Exception 발생 : {(str(ex))}')
                        time.sleep(1)  # 재시도 전 대기
                        
            else:
                if (not send_telegram_manager.initialized):
                    send_history.telegramSendResponse = "텔레그램 초기화 실패"
                docker_collect_logger.info(f'멤버 : [{member.mberId}] 텔레그램 전송 여부 : X ( 사용자 수신 여부 : {member.teleReceiveYN} | Manager 초기화 여부 : {send_telegram_manager.initialized})')
                send_history.telegramSendYN = member.teleReceiveYN
                send_history.telegramSendSuccessYN = 'N'
            
            docker_collect_logger.info(f'멤버 : [{member.mberId}] 컨텐츠 전송 종료\n\n')
            
            # 전송 여부 결과를 저장 (로그에서 통계 낼 때 사용)
            send_results.append(send_history)
            
            # 3 가지 중에 하나라도 전송한 사람에 대해서면 전송 결과를 저장
            if (member.teleReceiveYN == "Y"):
                # 이미 전송한 이력이 없을 경우 => 새로 insert
                if (previously_send_history == None):
                    send_history.regDt = datetime.now()
                    insert_res = BaseQueryService.insert_one(send_history)
                    docker_collect_logger.info(f'멤버 : [{member.mberId}] DB 저장 여부 : {insert_res}\n\n')
                # 이미 전송한 이력이 있을 경우 => 기존 데이터 Update
                else:
                    update_res = BaseQueryService.update_one(send_history)
                    docker_collect_logger.info(f'멤버 : [{member.mberId}] DB 업데이트 여부 : {update_res}\n\n')
        except Exception as ex:
            docker_collect_logger.info(f'send_telegram_multiple Exception 발생 : {(str(ex))}')
    
    return send_results

def send_email_multiple(member_list: list[MemberVO], contents_dict: dict[str, tuple[list[object], list[str]]], exec_time: datetime):
    docker_collect_logger.info(f"전송할 총 유저 수 : {len(member_list)}")
    # 전송 결과 정보를 담을 리스트
    send_results: list[ContentsSendHistoryVO] = []
    # 모든 멤버를 반복 - 이메일 보내기
    for member in member_list:
        try:
            if not hasattr(member, "mberId"): # 멤버 정보가 없으면 pass
                continue
        
            # 멤버에게 보낼 contents 만들기
            recommand_contents, used_keyword = contents_dict[member.mberId]
            
            contents = [content["value"] for content in recommand_contents]
            
            docker_collect_logger.info(f'멤버 : [{member.mberId}] 컨텐츠 전송 시작')
            
            docker_collect_logger.info(f'멤버 : [{member.mberId}] 의 전송 이력 확인')
            
            send_history_service = ContentsSendHistoryService()
            
            # 금일 이미 존재하는 전송 이력
            previously_send_history: ContentsSendHistoryVO = send_history_service.find_send_history_by_user_and_date(member.mberId, exec_time)
            
            # 새롭게 저장할 전송 이력
            send_history = ContentsSendHistoryVO()
            
            # 기존에 존재하는 Send History 가 없을 경우 => 기본 객체 만들기
            if (previously_send_history == None):
                docker_collect_logger.info(f'멤버 : [{member.mberId}] 의 금일 기존 전송 이력 못찾음')
                send_history.mberId = member.mberId
                send_history.keywords = used_keyword
                send_history.telegramSendYN = 'N'
                send_history.kakaoSendYN = 'N'
                send_history.emailSendYN = 'N'
                send_history.telegramSendSuccessYN = 'N'
                send_history.kakaoSendSuccessYN = 'N'
                send_history.emailSendSuccessYN = 'N'
                send_history.telegramSendIds = []
                send_history.kakaoSendIds = []
                send_history.emailSendIds = []
                send_history.telegramSendResponse = {}
                send_history.kakaoSendResponse = {}
                send_history.emailSendResponse = {}
                send_history.sendDt = datetime.now()
            else:
                send_history = previously_send_history
                docker_collect_logger.info(f'멤버 : [{member.mberId}] 의 금일 기존 전송 이력 찾음 : {send_history}')
            
            # send_history.telegramSendYN = 'N'
            # send_history.kakaoSendYN = 'N'
            send_history.emailSendYN = 'N'
            # send_history.telegramSendSuccessYN = 'N'
            # send_history.kakaoSendSuccessYN = 'N'
            send_history.emailSendSuccessYN = 'N'
            # send_history.telegramSendIds = []
            # send_history.kakaoSendIds = []
            send_history.emailSendIds = []
            # send_history.telegramSendResponse = {}
            # send_history.kakaoSendResponse = {}
            send_history.emailSendResponse = {}
            
            if member.emailReceiveYN == "Y" and send_mail_manager.initialized:
                docker_collect_logger.info(f"이메일 : {member.get_decrypt_email()}")
                max_retries = 3
                for attempt in range(1, max_retries + 1):
                    try:
                        docker_collect_logger.info(f'멤버 : [{member.mberId}] 메일 전송 여부 : O, 전송 중... 전송 시도 ({attempt}/{max_retries})')
                        send_mail_result = send_mail_manager.send(member, f"한전KDN 콘텐츠 구독 서비스 {today}", contents)
                        if (send_mail_result.isSuccess):
                            docker_collect_logger.info(f'멤버 : [{member.mberId}] 메일 전송 결과 : {send_mail_result.isSuccess} 전송 종료')
                            send_history = send_history_update(send_history=send_history, send_result=send_mail_result)
                            break
                        else:
                            docker_collect_logger.info(f'멤버 : [{member.mberId}] 메일 전송 결과 : {send_mail_result.isSuccess} 전송 종료')
                            send_history = send_history_update(send_history=send_history, send_result=send_mail_result)
                            time.sleep(1)  # 재시도 전 대기
                        
                    except Exception as ex:
                        # Exception 발생 시 수동으로 send_history 수정
                        send_history.emailSendYN = member.emailReceiveYN
                        send_history.emailSendSuccessYN = 'N'
                        send_history.emailSendResponse = (str(ex))
                        docker_collect_logger.info(f'Email Send Exception 발생 : {(str(ex))}')
                        time.sleep(1)  # 재시도 전 대기
            else:
                if (not send_mail_manager.initialized):
                    send_history.emailSendResponse = "Email 초기화 실패"
                docker_collect_logger.info(f'멤버 : [{member.mberId}] 메일 전송 여부 : X ( 사용자 수신 여부 : {member.emailReceiveYN} | Manager 초기화 여부 : {send_mail_manager.initialized})')
                send_history.emailSendYN = member.emailReceiveYN
                send_history.emailSendSuccessYN = 'N'
            
            docker_collect_logger.info(f'멤버 : [{member.mberId}] 컨텐츠 전송 종료\n\n')
            
            # 전송 여부 결과를 저장 (로그에서 통계 낼 때 사용)
            send_results.append(send_history)
            
            # 3 가지 중에 하나라도 전송한 사람에 대해서면 전송 결과를 저장
            if (member.emailReceiveYN == "Y"):
                # 이미 전송한 이력이 없을 경우 => 새로 insert
                if (previously_send_history == None):
                    send_history.regDt = datetime.now()
                    insert_res = BaseQueryService.insert_one(send_history)
                    docker_collect_logger.info(f'멤버 : [{member.mberId}] DB 저장 여부 : {insert_res}\n\n')
                # 이미 전송한 이력이 있을 경우 => 기존 데이터 Update
                else:
                    update_res = BaseQueryService.update_one(send_history)
                    docker_collect_logger.info(f'멤버 : [{member.mberId}] DB 업데이트 여부 : {update_res}\n\n')
        
        except Exception as ex:
                docker_collect_logger.info(f'send_email_multiple Exception 발생 : {(str(ex))}')
                
    return send_results
                
# 테스트 중
def send_email_multiple_with_multithread(member_list: list[MemberVO], contents: list[ContentsVO]):
    with ThreadPoolExecutor(max_workers=10) as executor:
        BATCH_SIZE = 100
        batch = member_list[i:i + BATCH_SIZE]  # 100개씩 나눠서 처리
        batch_number = i // BATCH_SIZE + 1  # 배치 번호
        for i in range(0, len(batch), BATCH_SIZE):
            exec_time = datetime.now()
            executor.submit(send_email_multiple, member_list, contents, exec_time)
                

def kakao_manager_initialize(max_retries=5, delay=1):
    
    # Kakao 알림톡 보내는 Class 선언 및 초기화
    send_kakao_manager = KakaoSendModel(user_id=Conf.KAKAO_SEND_USER, 
                                        password=Conf.KAKAO_SEND_PW, 
                                        sender_key=Conf.KAKAO_SEND_SENDER_KEY, 
                                        sender_number=Conf.KAKAO_SEND_SENDER_NUMBER)
    
    for attempt in range(1, max_retries + 1):
        docker_collect_logger.info(f"카카오톡 접속 시도 중 ... ({attempt}/{max_retries})")
        send_kakao_manager.initialize()
        if (send_kakao_manager.initialized):
            docker_collect_logger.info(f"카카오 Manager Initialize 여부 : {send_kakao_manager.initialized}")
            break
        else:
            docker_collect_logger.info(f"카카오 Manager Initialize 여부 : {send_kakao_manager.initialized}")
            time.sleep(delay)  # 재시도 전 대기
            
    docker_collect_logger.info(f"카카오 Manager Initialize 여부 (최종) : {send_kakao_manager.initialized}")
    return send_kakao_manager
    
def email_manager_initialize(max_retries=5, delay=1):
    # Mail, Telegram, Kakao 알림톡 보내는 Class 선언 및 초기화
    send_mail_manager = EmailSendModel(mail=Conf.MAIL_SEND_ID, token=Conf.MAIL_SEND_TOKEN)
    
    for attempt in range(1, max_retries + 1):
        # Mail, Telegram, Kakao 알림톡 보내는 Class 선언 및 초기화
        docker_collect_logger.info(f"GMail 접속 시도 중 ... ({attempt}/{max_retries})")
        send_mail_manager.initialize()
        if (send_mail_manager.initialized):
            docker_collect_logger.info(f"이메일 Manager Initialize 여부 : {send_mail_manager.initialized}")
            break
        else:
            docker_collect_logger.info(f"이메일 Manager Initialize 여부 : {send_mail_manager.initialized}")
            time.sleep(delay)  # 재시도 전 대기
            
    docker_collect_logger.info(f"이메일 Manager Initialize 여부 (최종) : {send_mail_manager.initialized}")
    
    return send_mail_manager

def telegram_manager_initialize(max_retries=5, delay=1):
    # Mail, Telegram, Kakao 알림톡 보내는 Class 선언 및 초기화
    send_telegram_manager = TelegramSendModel(token=Conf.TELEGRAM_SEND_TOKEN)
    
    for attempt in range(1, max_retries + 1):
        docker_collect_logger.info(f"Telegram 접속 시도 중 ... ({attempt}/{max_retries})")
        send_telegram_manager.initialize()
        if (send_telegram_manager.initialized):
            docker_collect_logger.info(f"텔레그램 Manager Initialize 여부 : {send_telegram_manager.initialized}")
            break
        else:
            docker_collect_logger.info(f"텔레그램 Manager Initialize 여부 : {send_telegram_manager.initialized}")
            time.sleep(delay)  # 재시도 전 대기
            
    docker_collect_logger.info(f"텔레그램 Manager Initialize 여부 (최종) : {send_telegram_manager.initialized}")
    
    return send_telegram_manager

# 금일 날짜 만들기
today = date.today().strftime("%Y-%m-%d")
telegram_today = date.today().strftime("%Y.%m.%d")

docker_collect_logger.info(f"[{today}] 컨텐츠 전송 시작")

# Mail, Telegram, Kakao 알림톡 보내는 Class 선언 및 초기화 (재시도 횟수 추가)
send_kakao_manager = kakao_manager_initialize(5, 1)
send_mail_manager = email_manager_initialize(5, 1)
send_telegram_manager = telegram_manager_initialize(5, 1)

docker_collect_logger.info(f"[{today}] 전송할 컨텐츠 검색 ...")
# 2. 오늘 수집된 컨텐츠 가져오기
contentsService = ContentsService()
today_contents: list[ContentsVO] = contentsService.findTodayContents(Conf.CONTENTS_SEARCH_PAST_DAY)

if (today_contents == None or len(today_contents) <= 0):
    docker_collect_logger.info(f'전송할 컨텐츠가 없습니다. 프로그램을 종료합니다.')
    sys.exit(0)  # 정상 종료
else:
    docker_collect_logger.info(f'전송할 컨텐츠 검색 결과 : {len(today_contents)}')

docker_collect_logger.info(f"[{today}] 컨텐츠 전송할 유저 검색 ...")

# 모든 사용자 정보 가져오기
members = BaseQueryService.find_all(MemberVO())
member_list: list[MemberVO] = members[0]

if (member_list == None or len(member_list) <= 0):
    docker_collect_logger.info(f'전송할 총 유저가 없습니다. 프로그램을 종료합니다.')
    sys.exit(0)  # 정상 종료
else:
    docker_collect_logger.info(f"전송할 총 유저 수 : {len(member_list)}")

exec_time = datetime.now()

# 모든 멤버에 대한 추천 콘텐츠 만들기
user_recommend_contents_dict: dict[str, tuple[list[object], list[str]]] = {}

for member in member_list:
    try:
        if not hasattr(member, "mberId"): # 멤버 정보가 없으면 pass
            continue
    
        # 멤버에게 보낼 contents 만들기
        user_recommend_contents_dict[member.mberId] = recommend_contents(member.mberId, today_contents)
        
    except Exception as ex:
        docker_collect_logger.info(f"멤버별 추천 콘텐츠 생성 중 Exception 발생 (member : {member.mberId}) : {str(ex)}")
        if hasattr(member, "mberId"): # 멤버 정보가 있으면 빈 값으로 추가
            user_recommend_contents_dict[member.mberId] = ([], [])
            
# no_send_users_cnt = sum(1 for v in user_recommend_contents_dict.values() if not v[0] and not v[1])
# send_users_cnt = sum(1 for v in user_recommend_contents_dict.values() if v[0] or v[1])
# docker_collect_logger.info("no_send_users_cnt : " + str(no_send_users_cnt) + "  |  " + "send_users_cnt : " + str(send_users_cnt))

# name_counts = Counter(user.mberId for user in member_list)
# mem_list = [name for name, count in name_counts.items() if count > 1]

# 모든 멤버를 반복 - 카카오톡 먼저 보내기
kakao_send_results: list[ContentsSendHistoryVO] = send_kakao_multiple(member_list, user_recommend_contents_dict, exec_time)

exec_time = datetime.now()
# 모든 멤버를 반복 - 텔레그램 보내기
telegram_send_results: list[ContentsSendHistoryVO] = send_telegram_multiple(member_list, user_recommend_contents_dict, exec_time)

exec_time = datetime.now()
# 모든 멤버를 반복 - 이메일 보내기
email_send_results: list[ContentsSendHistoryVO] = send_email_multiple(member_list, user_recommend_contents_dict, exec_time)

docker_collect_logger.info(f"[{today}] 컨텐츠 전송 종료")

docker_collect_logger.info(f"===== [{today}] 컨텐츠 전송 이력 종합 =====")

docker_collect_logger.info(f"===== 카카오톡 전송 이력 =====")
docker_collect_logger.info(f"총 멤버 수 : {len(member_list)}")
docker_collect_logger.info(f"총 전송 이력 개수 : {len(kakao_send_results)}")

# kakao_no_receive_member_count = sum(1 for member in member_list if member.kakaoReceiveYN == 'N')
docker_collect_logger.info(f"카카오톡 수신 거부 멤버 수: {sum(1 for member in member_list if member.kakaoReceiveYN == 'N')}")

# kakao_receive_member_count = sum(1 for member in member_list if member.kakaoReceiveYN == 'Y')
docker_collect_logger.info(f"카카오톡 수신 여부 멤버 수: {sum(1 for member in member_list if member.kakaoReceiveYN == 'Y')}")

# kakao_send_success_member_count = sum(1 for kakao_send_result in kakao_send_results if kakao_send_result.kakaoSendSuccessYN == 'Y')
docker_collect_logger.info(f"카카오톡 전송 성공 멤버 수: {sum(1 for kakao_send_result in kakao_send_results if kakao_send_result.kakaoSendYN == 'Y' and kakao_send_result.kakaoSendSuccessYN == 'Y')}")

kakao_send_fail_members = [kakao_send_result.mberId for kakao_send_result in kakao_send_results if kakao_send_result.kakaoSendYN == 'Y' and kakao_send_result.kakaoSendSuccessYN == 'N']
docker_collect_logger.info(f"카카오톡 전송 실패 멤버 수: {len(kakao_send_fail_members)}")
docker_collect_logger.info(f"카카오톡 전송 실패 멤버 목록: {', '.join(kakao_send_fail_members)}")
docker_collect_logger.info(f"===== 카카오톡 전송 이력 종료 =====\n\n")

docker_collect_logger.info(f"===== 텔레그램 전송 이력 =====")
docker_collect_logger.info(f"총 멤버 수 : {len(member_list)}")
docker_collect_logger.info(f"총 전송 이력 개수 : {len(telegram_send_results)}")

# telegram_no_receive_member_count = sum(1 for member in member_list if member.teleReceiveYN == 'N')
docker_collect_logger.info(f"텔레그램 수신 거부 멤버 수: {sum(1 for member in member_list if member.teleReceiveYN == 'N')}")

# telegram_receive_member_count = sum(1 for member in member_list if member.teleReceiveYN == 'Y')
docker_collect_logger.info(f"텔레그램 수신 여부 멤버 수: {sum(1 for member in member_list if member.teleReceiveYN == 'Y')}")

# telegram_send_success_member_count = sum(1 for telegram_send_result in telegram_send_results if telegram_send_result.telegramSendSuccessYN == 'Y')
docker_collect_logger.info(f"텔레그램 전송 성공 멤버 수: {sum(1 for telegram_send_result in telegram_send_results if telegram_send_result.telegramSendYN == 'Y' and telegram_send_result.telegramSendSuccessYN == 'Y')}")

telegram_send_fail_members = [telegram_send_result.mberId for telegram_send_result in telegram_send_results if telegram_send_result.telegramSendYN == 'Y' and telegram_send_result.telegramSendSuccessYN == 'N']
docker_collect_logger.info(f"텔레그램 전송 실패 멤버 수: {len(telegram_send_fail_members)}")
docker_collect_logger.info(f"텔레그램 전송 실패 멤버 목록: {', '.join(telegram_send_fail_members)}")
docker_collect_logger.info(f"===== 텔레그램 전송 이력 종료=====\n\n")

docker_collect_logger.info(f"===== 이메일 전송 이력 =====")
docker_collect_logger.info(f"총 멤버 수 : {len(member_list)}")
docker_collect_logger.info(f"총 전송 이력 개수 : {len(email_send_results)}")

# email_no_receive_member_count = sum(1 for member in member_list if member.emailReceiveYN == 'N')
docker_collect_logger.info(f"이메일 수신 거부 멤버 수: {sum(1 for member in member_list if member.emailReceiveYN == 'N')}")

# email_receive_member_count = sum(1 for member in member_list if member.emailReceiveYN == 'Y')
docker_collect_logger.info(f"이메일 수신 여부 멤버 수: {sum(1 for member in member_list if member.emailReceiveYN == 'Y')}")

# email_send_success_member_count = sum(1 for email_send_result in email_send_results if email_send_result.emailSendSuccessYN == 'Y')
docker_collect_logger.info(f"이메일 전송 성공 멤버 수: {sum(1 for email_send_result in email_send_results if email_send_result.emailSendYN == 'Y' and email_send_result.emailSendSuccessYN == 'Y')}")

email_send_fail_members = [email_send_result.mberId for email_send_result in email_send_results if email_send_result.emailSendYN == 'Y' and email_send_result.emailSendSuccessYN == 'N']
docker_collect_logger.info(f"이메일 전송 실패 멤버 수: {len(email_send_fail_members)}")
docker_collect_logger.info(f"이메일 전송 실패 멤버 목록: {', '.join(email_send_fail_members)}")
docker_collect_logger.info(f"===== 이메일 전송 이력 종료=====")

docker_collect_logger.info(f"[{today}] 컨텐츠 전송 종료")