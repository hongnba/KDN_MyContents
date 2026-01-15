from datetime import date
from typing import Any, Dict
from docker_talk_send.model.KakaoSendModelV2 import KakaoSendModel

import ksubscribe_share.config as Conf
from ksubscribe_share.logger import Logger
from docker_talk_send.model.SendModel import SendModel

logger = Logger()
docker_collect_logger = logger.setup_logger("docker_talk_send_test")

# 금일 날짜 만들기
today = date.today().strftime("%Y-%m-%d")
telegram_today = date.today().strftime("%Y.%m.%d")


docker_collect_logger.info(f"[{today}] 컨텐츠 전송 시작")

send_kakao_manager = KakaoSendModel(user_id=Conf.KAKAO_SEND_USER, 
                                    password=Conf.KAKAO_SEND_PW, 
                                    ref_key=Conf.KAKAO_SEND_REF_KEY, 
                                    sender_key=Conf.KAKAO_SEND_SENDER_KEY, 
                                    sender_number=Conf.KAKAO_SEND_SENDER_NUMBER)

send_kakao_manager.initialize()
docker_collect_logger.info(f"카카오 Manager Initialize 여부 : {send_kakao_manager.initialized}")

# fiSendModel = SendModel()
# fiSendModel.img_url = "https://mud-kage.kakao.com/dn/FtcdW/btsL5Au9kJG/eZ8FWWinBQ9pdaYPKAcx30/img_l.jpg"
# fiSendModel.mber_telno = "01053911388"
# fiSendModel.send_type = "fi"
# fiSendModel.template_msg = "친구톡 이미지 전송 테스트 메시지"
# fiSendModel.reserved_send_yn = "N"

# docker_collect_logger.info(f"카카오 Manager 친구톡 이미지 전송 시작")
# fi_response = Dict[str, Any]
# fi_response = send_kakao_manager.request_send_messages(fiSendModel)
# docker_collect_logger.info(f"카카오 Manager 친구톡 이미지 전송 완료 // 결과 : {fi_response}")

# ftSendModel = SendModel()
# fiSendModel.mber_telno = "01053911388"
# fiSendModel.send_type = "ft"
# fiSendModel.template_msg = "친구톡 텍스트 전송 테스트 메시지"
# fiSendModel.reserved_send_yn = "N"

# ft_response = Dict[str, Any]
# docker_collect_logger.info(f"카카오 Manager 친구톡 텍스트 전송 시작")
# ft_response = send_kakao_manager.request_send_messages(ftSendModel)
# docker_collect_logger.info(f"카카오 Manager 친구톡 텍스트 전송 완료 // 결과 : {fi_response}")

aiSendModel = SendModel()
aiSendModel.mber_telno = "01053911388"
aiSendModel.send_type = "ai"
aiSendModel.template_code = "bizp_2025012417225392092583562"
aiSendModel.template_msg = """
K-MyContents 구독 서비스
안녕하세요. 김승필 님!
2025-02-14 자 업데이트 된 추천 콘텐츠를 알려드립니다.

■ 한전 KDN
 - 테스트 메일 제목

■ 한전 KDN
 - 테스트 메일 제목2

■ 한국원자력발전소
 - 메일 제목 테스트 1

■ #{기관4}
 - #{제목4}

■ #{기관5}
 - #{제목5}

■ #{기관6}
 - #{제목6}

■ #{기관7}
 - #{제목7}

■ #{기관8}
 - #{제목8}

더 많은 콘텐츠는 포털에서 확인하세요!

※ 해당 구독 콘텐츠 전송 메시지는 고객님께서 신청하신 알림으로, 고객님이 MyContents 포털 내의 콘텐츠 구독 방법에서 '카카오톡' 을 선택하신 경우 발송됩니다.

"""

ai_response = Dict[str, Any]
docker_collect_logger.info(f"카카오 Manager 알림톡 텍스트 전송 시작")
ai_response = send_kakao_manager.request_send_messages(aiSendModel)
docker_collect_logger.info(f"카카오 Manager 친구톡 텍스트 전송 완료 // 결과 : {ai_response}")