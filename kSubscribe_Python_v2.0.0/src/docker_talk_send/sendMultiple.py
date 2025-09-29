from collections import Counter
from datetime import date
from datetime import datetime
import sys
import telegram
from telegram.ext import Updater, CommandHandler, CallbackContext

from docker_talk_send.model.EmailSendModel import EmailSendModel
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

logger = Logger()
docker_collect_logger = logger.setup_logger(logger.docker_talk_send_logger_name)

def recommend_contents_v2(mberId: str, contents: list[ContentsVO]):
    if (contents is None or len(contents) <= 0):
        return None, None
    
    memberService = MemberService()
    contentsOrgService = ContentsOrgService()
    
    # 1. 유저정보 조회
    user: MemberVO = MemberService.getMember(memberService, mberId)
    
    # 추천 목록
    recommended = []
    used_keyword = []
    # 같은 기관 사용자가 구독한 키워드 Dict 초기화
    org_member_keywords_dict: dict[str, int] = {}
    
    # orgid 가 있으면 실행. 특정 Property 에 값이 없으면 MongoDB 에 저장하지 않는 경우가 있으므로 hasattr() 를 실행안하면 에러가 날 수 있음.
    if hasattr(user, "orgId"):
        if (user.orgId != None):
            # 2. 내 기관 정보 가져오기
            myOrg: ContentsOrgVO = ContentsOrgService.findOrg(contentsOrgService, user.orgId)
        
            # 기관 정보가 없으면 활용 안함.
            if myOrg and myOrg != None:
                org_member_keywords_dict  = get_org_member_subscribe_keywords(mberId, myOrg.orgId)
    
    my_subs_keyword: list[str] = []
    # 내가 구독한 키워드
    if hasattr(user, "keywordSubscribe"): # not 제거할 것.
        my_subs_keyword = user.keywordSubscribe
    
    # 사용된 keyword 정보 만들기
    used_keyword = list(set(org_member_keywords_dict.keys()) | set(my_subs_keyword))
    
    # 내가 구독한 기관 목록
    org_list = [subs_org.orgId for subs_org in user.contentsOrgSubscribe]
    
    # 가중치
    user_weight = 1
    group_weight = 0.3
    
    # 모든 컨텐츠로부터 데이터 계산
    # 내가 구독한 기관에 대한 컨텐츠로만 계산하고 싶지만, 구독한 경우가 없을 것을 고려해서 전체 컨텐츠로 계산
    for content in contents:
        try:
            org_score = 0
            user_score = 0
            group_score = 0
            
            # 내가 구독한 기관이 발행한 컨텐츠인가?
            if (content.contentsOrgId in org_list):
                org_score += 1000 # 큰 점수를 줘서 구독한 기관의 키워드의 우선순위를 높힘.
            
            # predKeywords 는 Dict[str, int] 임.
            content_predKeywords = None
            
            if hasattr(content, "contentsMeta"): # not 제거할 것.
                if hasattr(content.contentsMeta, "predKeywords"):
                    content_predKeywords = content.contentsMeta.predKeywords
            
            if (content_predKeywords is None):
                content_predKeywords = {}
            
            # 본인 키워드 점수 계산 (키워드의 점수 고려)
            for keyword, score in content_predKeywords.items():
                if keyword in my_subs_keyword:
                    user_score += 5
                    user_score += score # 키워드 우선 순위에 대한 가중치
            
            # 집단 키워드 점수 계산 (키워드의 점수 고려)
            if org_member_keywords_dict:
                for keyword, score in content_predKeywords.items():
                    if keyword in org_member_keywords_dict:
                        group_score += org_member_keywords_dict[keyword] * 0.5
                        
            # 최종 점수 계산 (정규화 적용)
            total_score = org_score + user_score * user_weight + group_score * group_weight
            recommended.append({"id": str(content._id), "score": total_score, "value": content})
            
        except Exception as e:
            print(f"Error: {e}")
            continue
    
    # 점수 기준 정렬
    recommended.sort(key=lambda x: x["score"], reverse=True)
    return recommended, used_keyword

# 내가 속한 기관 멤버들이 구독한 키워드에 대한 Dict
def get_org_member_subscribe_keywords(mberId: str, orgId: str):
    pipeline = [
                {"$match": {"$and": [{"orgId": orgId}, {"mberId": {"$ne": mberId}}]}},
                {"$project": {"_id": 0, "mberId": 1, "keywordSubscribe": 1}},  # 필요한 필드만 선택
                ]
    
    coll = MongoManager().getCollection("member_account")
    org_members = coll.aggregate(pipeline).to_list()
    
    counter = Counter()  # 문자열 카운트를 위한 Counter 객체
    
    # 같은 기관의 멤버들이 구독한 기관에 대한 keyword 를 누적해서 dictionary [전기 : 10, 에너지 : 8 ...] 으로 만들기
    for item in org_members:
        member = MemberVO.from_mongo(item)
        if (hasattr(member, 'keywordSubscribe')):
            for subs_keyword in member.keywordSubscribe:
                counter.update([subs_keyword])  # list 로 안묶으면 한글자씩 counter 됨
                
    result_keyword_count_dict = dict(counter)
    # 1. 빈 문자열 키 제거
    cleaned_data = {key: value for key, value in result_keyword_count_dict.items() if key != '' and key != None}
    
    # 2. 값 기준으로 정렬 (내림차순)
    sorted_items = sorted(cleaned_data.items(), key=lambda item: item[1], reverse=True)
    
    # 3. 요청한 개수만큼 자르기
    top_items = sorted_items[:5]
    
    # 4. 딕셔너리로 변환하여 반환
    result_keyword_count_dict = dict(top_items)
    
    for key, value in result_keyword_count_dict.items():
        print(f"Key: {key}, Value: {value}")
        
    return result_keyword_count_dict

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


# bot = telegram.Bot(token='6533262494:AAHap9Qi69gXV-u1F0JxQ6Sye-MdQxmOh0c')
    
# BotFather에서 받은 토큰
# TOKEN = "8124555913:AAH08CAIqF2XvQEuPCKn20Pkm9KEBuHjVSM"

# # # 메시지 전송 API 호출
# url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
# response = requests.get(url)
# data = response.json()

# # Chat ID 출력
# if data["ok"]:
#     for result in data["result"]:
#         print("Chat ID:", result["message"]["chat"]["id"])
# else:
#     print("Error:", data)
    
# dispatcher = updater.dispatcher

# # /start 명령어 처리
# dispatcher.add_handler(CommandHandler("start", start))

# # 봇 실행
# updater.start_polling()
# updater.idle()

# 금일 날짜 만들기
today = date.today().strftime("%Y-%m-%d")
telegram_today = date.today().strftime("%Y.%m.%d")

docker_collect_logger.info(f"[{today}] 컨텐츠 전송 시작")

# Mail, Telegram, Kakao 알림톡 보내는 Class 선언 및 초기화
send_mail_manager = EmailSendModel(mail=Conf.MAIL_SEND_ID, token=Conf.MAIL_SEND_TOKEN)
send_mail_manager.initialize()

docker_collect_logger.info(f"이메일 Manager Initialize 여부 : {send_mail_manager.initialized}")

send_telegram_manager = TelegramSendModel(token=Conf.TELEGRAM_SEND_TOKEN)
send_telegram_manager.initialize()

docker_collect_logger.info(f"텔레그램 Manager Initialize 여부 : {send_telegram_manager.initialized}")

send_kakao_manager = KakaoSendModel(user_id=Conf.KAKAO_SEND_USER, 
                                    password=Conf.KAKAO_SEND_PW, 
                                    sender_key=Conf.KAKAO_SEND_SENDER_KEY, 
                                    sender_number=Conf.KAKAO_SEND_SENDER_NUMBER)
send_kakao_manager.initialize()
docker_collect_logger.info(f"카카오 Manager Initialize 여부 : {send_kakao_manager.initialized}")

docker_collect_logger.info(f"[{today}] 전송할 컨텐츠 검색 ...")
# 2. 오늘 수집된 컨텐츠 가져오기
contentsService = ContentsService()
today_contents: list[ContentsVO] = contentsService.findTodayContents(Conf.CONTENTS_SEARCH_PAST_DAY)

docker_collect_logger.info(f'전송할 컨텐츠 검색 결과 : {len(today_contents)}')

if (today_contents == None or len(today_contents) <= 0):
    docker_collect_logger.info(f'전송할 컨텐츠가 없습니다. 프로그램을 종료합니다.')
    sys.exit(0)  # 정상 종료

docker_collect_logger.info(f"[{today}] 컨텐츠 전송할 유저 검색 ...")

# 모든 사용자 정보 가져오기
members = BaseQueryService.find_all(MemberVO())
member_list = members[0]

docker_collect_logger.info(f"전송할 총 유저 수 : {len(member_list)}")

# 모든 멤버를 반복
for index, member in enumerate(member_list):
    if not hasattr(member, "mberId"): # 멤버 정보가 없으면 pass
        continue
    
    recommand_contents, used_keyword = recommend_contents_v2(member.mberId, today_contents)
    contents = [content["value"] for content in recommand_contents]
    # 멤버에게 보낼 contents 만들기
    # contents = ContentsVO.find_all()
    
    # send_telegram_result = send_telegram_manager.send(member, f"한전KDN 콘텐츠 구독 서비스 {today}", contents)
    
    docker_collect_logger.info(f'멤버 : [{member.mberId}] 컨텐츠 전송 시작')
    
    send_history = ContentsSendHistoryVO()
    send_history.mberId = member.mberId
    send_history.keywords = used_keyword
    send_history.telegramSendYN = 'N'
    send_history.emailSendYN = 'N'
    send_history.kakaoSendYN = 'N'
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
    
    if member.teleReceiveYN == "Y" and send_telegram_manager.initialized:
        try:
            docker_collect_logger.info(f'멤버 : [{member.mberId}] 텔레그램 전송 여부 : O, 전송 시작')
            send_telegram_result = send_telegram_manager.send_total(member, contents)
            send_history = send_history_update(send_history=send_history, send_result=send_telegram_result)
            docker_collect_logger.info(f'멤버 : [{member.mberId}] 텔레그램 전송 결과 : {send_telegram_result.isSuccess} 전송 종료')
        except Exception as ex:
            send_history.telegramSendSuccessYN = 'N'
            docker_collect_logger.info(f'Telegram Send Exception 발생 : {(str(ex))}')
    else:
        docker_collect_logger.info(f'멤버 : [{member.mberId}] 텔레그램 전송 여부 : X')
        send_history.telegramSendYN = 'N'
        
    if member.kakaoReceiveYN == "Y" and send_kakao_manager.initialized:
        try:
            docker_collect_logger.info(f'멤버 : [{member.mberId}] 카카오 전송 여부 : O, 전송 시작')
            send_kakao_result = send_kakao_manager.send_kakao_bizppurio(member, contents)
            docker_collect_logger.info(f'멤버 : [{member.mberId}] 카카오 전송 결과 : {send_kakao_result.isSuccess} 전송 종료')
            send_history = send_history_update(send_history=send_history, send_result=send_kakao_result)
        except Exception as ex:
            send_history.kakaoSendSuccessYN = 'N'
            docker_collect_logger.info(f'Kakao Send Exception 발생 : {(str(ex))}')
    else:
        docker_collect_logger.info(f'멤버 : [{member.mberId}] 카카오 전송 여부 : X')
        send_history.kakaoSendYN = 'N'
        
    if member.emailReceiveYN == "Y" and send_mail_manager.initialized:
        try:
            docker_collect_logger.info(f"이메일 : {member.get_decrypt_email()}")
            docker_collect_logger.info(f'멤버 : [{member.mberId}] 메일 전송 여부 : O, 전송 시작')
            send_mail_result = send_mail_manager.send(member, f"한전KDN 콘텐츠 구독 서비스 {today}", contents)
            docker_collect_logger.info(f'멤버 : [{member.mberId}] 메일 전송 결과 : {send_mail_result.isSuccess} 전송 종료')
            send_history = send_history_update(send_history=send_history, send_result=send_mail_result)
            
        except Exception as ex:
            send_history.emailSendSuccessYN = 'N'
            docker_collect_logger.info(f'Email Send Exception 발생 : {(str(ex))}')
    else:
        if (not send_mail_manager.initialized):
            send_history.emailSendResponse = "Email 초기화 실패"
        docker_collect_logger.info(f'멤버 : [{member.mberId}] 메일 전송 여부 : X')
        send_history.emailSendYN = 'N'
    
    docker_collect_logger.info(f'멤버 : [{member.mberId}] 컨텐츠 전송 종료\n\n')
    send_history.regDt = datetime.now()
    
    # 3 가지 중에 하나라도 전송한 사람에 대해서면 전송 결과를 저장
    if (member.teleReceiveYN == "Y" or member.kakaoReceiveYN == "Y" or member.emailReceiveYN == "Y"):
        insert_res = BaseQueryService.insert_one(send_history)


    
    
    
    



