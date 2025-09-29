from datetime import date, datetime, timezone
import sys
import ksubscribe_share.config as Conf
from docker_talk_send.model.EmailSendModel import EmailSendModel
from docker_talk_send.recommend import recommend_contents, send_history_update
from ksubscribe_share.db.dbmodelV2.contentsSendHistoryVO import ContentsSendHistoryVO
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO
from ksubscribe_share.db.dbmodelV2.memberVO import MemberVO
from ksubscribe_share.db.service.baseQueryService import BaseQueryService
from ksubscribe_share.db.service.contentsService import ContentsService

# 금일 날짜 만들기
today = date.today().strftime("%Y-%m-%d")
telegram_today = date.today().strftime("%Y.%m.%d")

print(f"[{today}] 컨텐츠 전송 시작 - [Email]")

# Mail, Telegram, Kakao 알림톡 보내는 Class 선언 및 초기화
send_mail_manager = EmailSendModel(mail=Conf.MAIL_SEND_ID, token=Conf.MAIL_SEND_TOKEN)
send_mail_manager.initialize()

print(f"이메일 Manager Initialize 여부 : {send_mail_manager.initialized}")

print(f"[{today}] 전송할 컨텐츠 검색 ...")
# 2. 오늘 수집된 컨텐츠 가져오기
contentsService = ContentsService()
today_contents: list[ContentsVO] = contentsService.findTodayContents(Conf.CONTENTS_SEARCH_PAST_DAY)

if (today_contents == None or len(today_contents) <= 0):
    print(f'전송할 컨텐츠가 없습니다. 프로그램을 종료합니다.')
    sys.exit(0)  # 정상 종료

print(f"[{today}] 컨텐츠 전송할 유저 검색 ...")

# 모든 사용자 정보 가져오기
members = BaseQueryService.find_all(MemberVO())
member_list = members[0]

print(f"전송할 총 유저 수 : {len(member_list)}")

# 모든 멤버를 반복
for index, member in enumerate(member_list):
    if not hasattr(member, "mberId"): # 멤버 정보가 없으면 pass
        continue
    
    recommand_contents, used_keyword = recommend_contents(member.mberId, today_contents)
    contents = [content["value"] for content in recommand_contents]
    
    print(f'멤버 : [{member.mberId}] 컨텐츠 전송 시작')
    
    send_history = ContentsSendHistoryVO()
    send_history.mberId = member.mberId
    send_history.keywords = used_keyword
    # send_history.telegramSendYN = False
    # send_history.kakaoSendYN = False
    send_history.emailSendYN = False
    # send_history.telegramSendSuccessYN = False
    # send_history.kakaoSendSuccessYN = False
    send_history.emailSendSuccessYN = False
    # send_history.telegramSendIds = []
    # send_history.kakaoSendIds = []
    send_history.emailSendIds = []
    # send_history.telegramSendResponse = {}
    # send_history.kakaoSendResponse = {}
    send_history.emailSendResponse = {}
    send_history.sendDt = datetime.utcnow(timezone.utc)
        
    if member.emailReceiveYN == "Y" and send_mail_manager.initialized:
        print(f'멤버 : [{member.mberId}] 메일 전송 여부 : O, 전송 시작')
        send_mail_result = send_mail_manager.send(member, f"한전KDN 콘텐츠 구독 서비스 {today}", contents)
        print(f'멤버 : [{member.mberId}] 메일 전송 결과 : {send_mail_result.isSuccess} 전송 종료')
        send_history = send_history_update(send_history=send_history, send_result=send_mail_result)
    else:
        if (not send_mail_manager.initialized):
            send_history.emailSendResponse = "Email 초기화 실패"
        print(f'멤버 : [{member.mberId}] 메일 전송 여부 : X')
        send_history.emailSendYN = False
    
    print(f'멤버 : [{member.mberId}] 컨텐츠 전송 종료\n\n')
    send_history.regDt = datetime.now()
    
    # 3 가지 중에 하나라도 전송한 사람에 대해서면 전송 결과를 저장
    if (member.emailReceiveYN == "Y"):
        insert_res = BaseQueryService.insert_one(send_history)