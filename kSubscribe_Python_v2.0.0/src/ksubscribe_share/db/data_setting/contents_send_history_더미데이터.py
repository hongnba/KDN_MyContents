import random
import sys
from datetime import datetime, timedelta, timezone

from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO
from ksubscribe_share.db.dbmodelV2.memberVO import MemberVO
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
from ksubscribe_share.db.dbmodelV2.contentsSendHistoryVO import contentsSendHistoryVO

from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO

from pydantic import BaseModel
from bson import ObjectId

import json
from typing import List
import time

import asyncio


def time_now():
    return datetime.now(timezone(timedelta(hours=9)))

class MoveContentsSendHistory:
    # 좋아요 싫어요에 대한 유저 id 추가
    def add_contentsSendHistoryV1(self):
        # 수집한 콘텐츠 가져오기
        contents: List[ContentsVO] = ContentsVO.find_all()
        members: List[MemberVO] = MemberVO.find_all()

        if len(contents) > 0 and len(members) > 0:
            for member in enumerate(members):
                send_history = contentsSendHistoryVO(
                    mberId=str(member[1].mberId),
                    sendDt=None,
                    kakaoSendIds=[],
                    telegramSendIds=[],
                    emailSendIds=[],
                    mergedSendIds=[],
                )
                
                # 1~5 사이의 랜덤 n 값 생성
                kakao_send_cnt = 8 # 카카오톡은 8개로 고정
                telegram_send_cnt = random.randint(0, 5)
                mail_send_cnt = random.randint(0, 5)

                # 랜덤으로 n개의 요소 추출
                kakao_random_contents_list = random.sample(contents, min(kakao_send_cnt, len(contents)))  # n이 리스트 길이를 초과하지 않도록
                telegram_random_contents_list = random.sample(contents, min(telegram_send_cnt, len(contents)))  # n이 리스트 길이를 초과하지 않도록
                mail_random_contents_list = random.sample(contents, min(mail_send_cnt, len(contents)))  # n이 리스트 길이를 초과하지 않도록
                
                for content in enumerate(kakao_random_contents_list):
                    send_history.kakaoSendIds.append(str(content[1]._id))
                    send_history.mergedSendIds.append(str(content[1]._id))
                    
                for content in enumerate(telegram_random_contents_list):
                    send_history.telegramSendIds.append(str(content[1]._id))
                    send_history.mergedSendIds.append(str(content[1]._id))
                    
                for content in enumerate(mail_random_contents_list):
                    send_history.emailSendIds.append(str(content[1]._id))
                    send_history.mergedSendIds.append(str(content[1]._id))
                    
                send_history.mergedSendIds = list(dict.fromkeys(send_history.mergedSendIds))
                
                send_history.sendDt = datetime.now()
                # send_history.sendDt = datetime.now() - timedelta(days=1)
                
                send_history.insert_one()


if __name__ == "__main__":
    contents = MoveContentsSendHistory()
    contents.add_contentsSendHistoryV1()
    a = 0
