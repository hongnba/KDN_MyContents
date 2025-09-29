# sendHistory.py
from datetime import date, timedelta
from docker_talk_send.model.TelegramSendModel import TelegramSendModel
import ksubscribe_share.config as Conf
from ksubscribe_share.db.service.contentsCollectDailyHistoryService import ContentsCollectDailyHistoryService
from ksubscribe_share.db.service.memberService import MemberService
from ksubscribe_share.db.service.contentsCollectRequestService import ContentsCollectRequestService
from ksubscribe_share.db.service.serviceStatsService import ServiceStatsService
from ksubscribe_share.logger import Logger

logger = Logger()
docker_collect_logger = logger.setup_logger(logger.docker_talk_send_logger_name)

today = date.today() - timedelta(days=1)
telegram_today = today.strftime("%Y.%m.%d")

docker_collect_logger.info(f"-------------Docker_Send_History 시작 ----------------")

docker_collect_logger.info(f"[{today}] 통계 정보 전송 시작")

docker_collect_logger.info(f"텔레그램 초기화 시작")
send_telegram_manager = TelegramSendModel(token=Conf.TELEGRAM_SEND_TOKEN)
send_telegram_manager.initialize()
docker_collect_logger.info(f"텔레그램 초기화 여부 : [{send_telegram_manager.initialized}]")

# 1. 어제부터 현재까지의 수집 이력 정보 가져오기 
docker_collect_logger.info(f"어제부터 현재까지의 수집 이력 정보 가져오기")
contentsCollectDailyHistoryService = ContentsCollectDailyHistoryService()
daily_history_list = contentsCollectDailyHistoryService.search_collect_daily_history_from_period(start_date=today, period=1)
docker_collect_logger.info(f"어제부터 현재까지의 수집 이력 정보 Count : [{len(daily_history_list)}]")

total_count = 0
success_count = 0
fail_count = 0
collect_count = 0

if daily_history_list != None:
    for daily_history in daily_history_list:
        total_count += daily_history.totalCount
        success_count += daily_history.successCount
        fail_count += daily_history.failCount
        collect_count += daily_history.collectCount

docker_collect_logger.info(f"total_count : [{total_count}]")
docker_collect_logger.info(f"success_count : [{success_count}]")
docker_collect_logger.info(f"fail_count : [{fail_count}]")
docker_collect_logger.info(f"collect_count : [{collect_count}]")

# 2. 관리자 계정인 사람들의 tele_chat_id 가져오기
docker_collect_logger.info(f"관리자 계정인 사람들의 tele_chat_id 가져오기 시작")
memberService = MemberService()
members = memberService.getAdminMembersTeleChatIds()
docker_collect_logger.info(f"관리자 계정 개수 : [{len(members)}]")

# 3. 어제부터 현재까지 새롭게 회원가입한 사람의 숫자 가져오기 (joinDt 로 판단)
c = memberService.getSignedUpMemberFromPeriod(start_date=today, period=1)

join_n = 0
if c != None:
    join_n = len(c)

# 5. 어제부터 현재까지 사용자가 구독 추가 요청한 컨텐츠 숫자 가져오기
contentsCollectRequestService = ContentsCollectRequestService()
e = contentsCollectRequestService.getRequestsFromPeriod(start_date=today, period=1)

con_req_n = 0
if e != None:
    con_req_n = len(e)

# 6. MongoDB 통계 정보 가져오기 (클릭수, 로그인수, 회원수 등)
docker_collect_logger.info(f"20250422 MongoDB 기반 일일 통계 정보 조회 시작")
serviceStatsService = ServiceStatsService()
daily_stats = serviceStatsService.get_daily_service_stats(start_date=today, period=1)

click_count = daily_stats["click_count"]
login_count = daily_stats["login_count"]
kakao_login_count = daily_stats["kakao_login_count"]
member_total = daily_stats["total_members"]
member_subscribed = daily_stats["subscribed_members"]
contents_sent = daily_stats["sent_contents"]
contents_collected = daily_stats["collected_contents"]
collect_duration = daily_stats["collect_duration"]
raw_collect_duration = daily_stats["raw_collect_duration"]
send_duration = daily_stats["send_duration"]

# 7. 회차별 수집 시간 분석 추가
shift_counts = serviceStatsService.get_collect_counts_by_shift(start_date=today)


# 텔레그램 메시지 작성
feed = '한전KDN 콘텐츠 구독 서비스\n'
feed += f'{telegram_today} 일일 모니터링\n\n'
feed += '■ 회원 정보\n'
feed += f' - 전체 회원 수 : {member_total}명(전일대비 +{join_n}명)\n'
feed += f' - 구독자 수 : {member_subscribed}명\n\n'
feed += '■ 구독 기관 추가요청\n'
feed += f' - 총 {con_req_n}건\n\n'
feed += '■ 사용자 활동\n'
feed += f' - 전체 조회수 : {click_count}회\n'
feed += f' - 전체 로그인 횟수 : {login_count}회\n'
feed += f' - 카카오 로그인 횟수 : {kakao_login_count}회\n\n'
feed += '■ 수집/전송 현황\n'
feed += f' - 수집 콘텐츠 수 : {contents_collected}개\n'
feed += f' - 전송된 메시지 수 : {contents_sent}건\n\n'
feed += '■ 수집 소요시간\n'
for label, count, raw_sec, collect_sec in shift_counts:
    feed += f' - {label}: 수집 {count}건, 최초 {raw_sec/60:.1f}분, 본문 {collect_sec/60:.1f}분\n\n'
feed += '■ 전송 소요시간\n'
# feed += f' - 최초 수집 기준 : {raw_collect_duration/60:.1f}분\n'
# feed += f' - 본문 수집 기준 : {collect_duration/60:.1f}분\n'
feed += f' - 콘텐츠 전송 기준 : {send_duration/60:.1f}분\n'



if members != None:
    for member in members:
        try:
            docker_collect_logger.info(f'멤버 : {member.mberId} 에게 전송')
            send_response = send_telegram_manager.send_feed_message_to_member(receiver=member, feed=feed)
            docker_collect_logger.info(f'멤버 : [{member.mberId}] 텔레그램 전송 결과 : {send_response}')
        except Exception as ex:
            docker_collect_logger.info(f'Telegram Send Exception 발생 : {(str(ex))}')

docker_collect_logger.info(f"-------------Docker_Send_History 종료 ----------------")
