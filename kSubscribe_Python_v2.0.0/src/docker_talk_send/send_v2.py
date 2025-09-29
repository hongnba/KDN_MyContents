# -*- coding: utf-8 -*-

from datetime import date
import datetime
from openpyxl import Workbook
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import pandas as pd

import pymysql

import telegram

import urllib.request

import time

import subprocess

import warnings

from sqlalchemy import create_engine

warnings.filterwarnings("ignore")

today = date.today().strftime("%Y-%m-%d")
tele_today = date.today().strftime("%Y.%m.%d")
print('도커 컨테이너 send.py 진입')

def get_days(yyyy, mm, dd):
    days = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
    return days[datetime.date(yyyy, mm, dd).weekday()]

# df 만들고 수신자 넣어서 함수 호출
def send_email(df, recipient):

    # 메일 보내기
    # 세션생성, 로그인
    s = smtplib.SMTP('smtp.gmail.com', 587) # 서버랑 포트 정보
    s.ehlo() # SMTP 프로토콜의 명령어 중 하나로, Extended Hello를 의미, 클라이언트가 SMTP 서버에 연결된 후 가장 먼저 호출하는 명령어
    s.starttls() # TLS 암호화 시작
    s.login('3waysoft.com@gmail.com', '3waysoftmihwa&') # 서버 로그인
    
    # 제목, 본문 작성
    msg = MIMEMultipart()
    msg['Subject'] = f'[한전KDN] {today} 구독 콘텐츠 송부 - 총 {len(df)}건'
    # '({today}) (전송모듈테스트)전력유관기관 및 주요기관 동향 - 총 {len(df)}건 알림'
    part2 = MIMEText(html, 'html')
    
    msg.attach(part2)
    # msg.attach(html)
    # msg['From'] = '한전KDN 데이터 신사업 정보 제공 서비스'
    msg['From'] = '한전KDN 콘텐츠 구독 서비스'
    
    msg['NonTo'] = 'hh3990@naver.com, hh44683990@gmail.com'
    # msg['NonTo'] = 'jaehyuk_choi2@kdn.com, hh3990@naver.com'
         
    # 메일 전송
    print(f'df길이 : {len(df)}')
    # print(df)
    if len(df) > 0:
        print('0보다 큽니다')
        s.sendmail("kepcokdnkcs@gmail.com", recipient, msg.as_string())
        s.quit()
    else: 
        print('0보다 크지 않습니다!')
        s.sendmail("kepcokdnkcs@gmail.com", msg['NonTo'].split(','), msg.as_string())
        s.quit()
    return

def send_telegram(df, chat_id):
    try:
        if len(df) == 0:
            return
        cut_flag = False
        if len(df) > 20:
            print('20개까지 자르기')
            df = df.head(20)
            print(df)
            cut_flag = True
        bot = telegram.Bot(token='6533262494:AAHap9Qi69gXV-u1F0JxQ6Sye-MdQxmOh0c')
        feed = f''
        catg_name = ''
        org_name = ''
        cate_name = ''
        page_idx = 1
        total_page = (len(df)//29)+1
        feed += '한전KDN 콘텐츠 구독 서비스\n'
        feed += f'{tele_today} 맞춤 콘텐츠 (총 {len(df)}건)({page_idx}/{total_page})\n'
        if cut_flag: 
            feed += '요약된 콘텐츠입니다. 이외 콘텐츠는 포털에서 확인 바랍니다.\n\n'
        current_catg = ''
        current_org = ''
        for idx, row in df.iterrows():
            # 기관 자체가 카탈로그인 경우
            if row["카탈로그명"] == row["기관명"]:
                # 새로 들어오는 기관명이 현재 저장된 기관명과 다른 경우에만 적어주기
                if row["기관명"] != current_org:
                    feed += f'<b>■ {row["기관명"]}</b>\n'
                    if row["요청 키워드1"] is not None and row["요청 키워드1"] != '':
                        feed += f'#{row["요청 키워드1"]} '
                    if row["요청 키워드2"] is not None and row["요청 키워드2"] != '':
                        feed += f'#{row["요청 키워드2"]} '
                    if row["요청 키워드3"] is not None and row["요청 키워드3"] != '':
                        feed += f'#{row["요청 키워드3"]}'
                    feed += '\n'
                    # # 카탈로그명, 기관명 다시 세팅
                    # current_catg = row["카탈로그명"]
                    # current_org = row["기관명"]
            # 다수 기관 카탈로그인 경우
            else:
                # 카탈로그명이 다르거나 기관명이 다르거나 하나라도 다른 경우에만 적어주기
                if (row["카탈로그명"] != current_catg) or (row["기관명"] != current_org):
                    print('하나라도 다릅니다.')
                    print(current_catg, current_org)
                    print(row["카탈로그명"], row["기관명"])
                    feed += f'<b>■ {row["카탈로그명"]}-{row["기관명"]}</b>\n'
                    if row["요청 키워드1"] is not None and row["요청 키워드1"] != '':
                        feed += f'#{row["요청 키워드1"]} '
                    if row["요청 키워드2"] is not None and row["요청 키워드2"] != '':
                        feed += f'#{row["요청 키워드2"]} '
                    if row["요청 키워드3"] is not None and row["요청 키워드3"] != '':
                        feed += f'#{row["요청 키워드3"]}'
                    feed += '\n'
                    # # 카탈로그명, 기관명 다시 세팅
                    # current_catg = row["카탈로그명"]
                    # current_org = row["기관명"]
            # 카탈로그명, 기관명 다시 세팅
            current_catg = row["카탈로그명"]
            current_org = row["기관명"]
            title = row["TITLE"].replace('[', '(')
            title = title.replace(']', ')')
            if row["MATCH_KEYWORD1"] != 'ALL':
                keyword_idx = title.find(row["MATCH_KEYWORD1"])
                pre = title[:keyword_idx]
                post = title[keyword_idx+len(row["MATCH_KEYWORD1"]):]
                keyword_line = f'<b>{row["MATCH_KEYWORD1"]}</b>'
                title = pre + keyword_line + post
            # feed += f'-[{title}]({row["관련 URL"]})\n'
            feed += f'- {title}\n'
            # feed += f'- http://133.186.216.57:8080/K-CaaS/g.do?s={row["SHORT_URL"]}\n'
            feed += f'- https://mycontents.kdn.com/c/g.do?s={row["SHORT_URL"]}&n={row["HASH_SEQ"]}\n'
            print(len(feed))
            feed += '\n'
            # 0~29까지 총 30개. 30개 단위로 끊기.
            if (idx!=0) and (idx%29 == 0):
                # bot.sendMessage(chat_id=chat_id, text=feed, parse_mode = 'Markdown', disable_web_page_preview=True)
                try:
                    bot.sendMessage(chat_id=chat_id, text=feed, disable_web_page_preview=True, parse_mode = 'html')
                except Exception as e:
                    print(e)
                page_idx += 1
                feed = ''
                feed += '한전KDN 콘텐츠 구독 서비스\n'
                feed += f'{tele_today} 맞춤 콘텐츠 (총 {len(df)}건)({page_idx}/{total_page})\n\n'
        if feed != '':
            # bot.sendMessage(chat_id=chat_id, text=feed, parse_mode = 'Markdown', disable_web_page_preview=True)
            try:
                bot.sendMessage(chat_id=chat_id, text=feed, disable_web_page_preview=True, parse_mode = 'html')
            except Exception as e:
                    print(e)
    except Exception as e:
        print(e)

def send_kakao(df, telno):
    if len(df) == 0:
        return

    param3 = ''
    if len(df) > 8:
        print('8개까지 자르기')
        df = df.head(8)
        print(df)
        param3 = urllib.parse.quote(' 요약된 콘텐츠입니다. 이외 콘텐츠는 포털에서 확인 바랍니다.')

    telno = telno.replace('-', '')
    print('################## sendNo : ', telno)

    
    # params
    sendNo = urllib.parse.quote(telno)
    callBackNo = urllib.parse.quote('0619317114')
    systemKey = urllib.parse.quote('222046-caas01')
    projectId = urllib.parse.quote('KDN-3570-23-0001')
    tmplCode = urllib.parse.quote('AT_20230830095523')
    # paramNum 꼭 33개 안 채워도 되는지 확인하기. 9건이라면 param31, 32, 33 필요 없으니. -> paramNum은 33으로 paramn은 다 안 채워도 됨.
    paramNum = urllib.parse.quote('33')

    page_idx = 1
    if len(df)%8 == 0:
        total_page = len(df)//8
    else:
        total_page = (len(df)//8)+1
    

    param1 = today # 2023-09-05
    param2 = len(df) # 총 27건

    if total_page == 1:
        # param3 = '' 
        # 240418 어차피 이제 무조건 1페이지. 요약입니다 내용 추가.
        # param3 = '요약된 콘텐츠입니다. 이외 콘텐츠는 포털에서 확인 바랍니다.'
        pass
    else:
        param3 = f'({page_idx}/{total_page})' # (1/3)
        param3 = ''
    param4 = ''
    param5 = ''
    param6 = ''
    param7 = ''
    param8 = ''
    param9 = ''
    param10 = ''
    param11 = ''
    param12 = ''
    param13 = ''
    param14 = ''
    param15 = ''
    param16 = ''
    param17 = ''
    param18 = ''
    param19 = ''
    param20 = ''
    param21 = ''
    param22 = ''
    param23 = ''
    param24 = ''
    param25 = ''
    param26 = ''
    param27 = ''
    param28 = ''
    param29 = ''
    param30 = ''
    param31 = ''
    param32 = ''
    param33 = ''
    # lms = '한전KDN 콘텐츠 구독 서비스\n'
    # lms += f'{today}일 콘텐츠를 송부드립니다. 총 {len(df)}건 ({page_idx}/{total_page})\n'
    # 0 1 2 3 4 5 6 7 8 9 / 10 11 12 13 14 15 16 17 18 19 / 20 21 22 23 24 25 26 27 28 29 / 30 31 32 33 34 35 36 37 38 39 40 / 41
    # 0 1 2 3 4 5 6 7 / 8 9 10 11 12 13 14 15 / 16 17 18 19 20 21 22 23 / 
    # 0 8 16 % 8 == 0
    # 1 9 17 % 8 == 1
    # 2 10 18 % 8 == 2
    # 3 11 19 % 8 == 3
    cnt = 0

    for idx, row in df.iterrows():
        # 기관명 
        if  {row["카탈로그명"]} == {row["기관명"]}:
            org_name = urllib.parse.quote(f'■ {row["기관명"]}')
            org_name_lms = f'■ {row["기관명"]}'
        else:
            org_name = urllib.parse.quote(f'■ {row["카탈로그명"]}-{row["기관명"]}')
            org_name_lms = f'■ {row["기관명"]}'
        # 제목
        print('###########제목 길이#############')
        print(len(row["TITLE"]))
        print(row["TITLE"])
        if len(row["TITLE"]) <= 45:
            contents_title = urllib.parse.quote(f'- {row["TITLE"]}')
            contents_title_lms = f'- {row["TITLE"]}'
        else:
            contents_title = urllib.parse.quote(f'- {row["TITLE"][:45]}..') # 한줄 때문 뿐만이 아니라 카톡 1000자 제한 때문에 
            contents_title_lms = f'- {row["TITLE"][:45]}..'
        # URL
        contents_url = urllib.parse.quote(f'https://mycontents.kdn.com/c/g.do?s={row["SHORT_URL"]}&n={row["HASH_SEQ"]}')
        contents_url_lms = f'https://mycontents.kdn.com/c/g.do?s={row["SHORT_URL"]}&n={row["HASH_SEQ"]}'

        if idx%8 == 0:
            # 매 10건 마다 url, lms 초기화
            url = 'http://10.100.21.128:17878/sendKakao'
            lms = '한전KDN 콘텐츠 구독 서비스\n'
            lms += f'{today}일 콘텐츠를 송부드립니다. 총 {len(df)}건 '
            # 다음 페이지 넘어갈 경우
            if idx != 0:
                page_idx += 1
                param3 = urllib.parse.quote(f'({page_idx}/{total_page})')
                param3 = ''
            lms += f'({page_idx}/{total_page})\n'
            param4 = org_name
            lms += f'{org_name_lms}\n'
            param5 = contents_title
            lms += f'{contents_title_lms}\n'
            param6 = contents_url
            lms += f'{contents_url_lms}\n'
        elif idx%8 == 1:
            lms += '\n'
            param7 = org_name
            lms += f'{org_name_lms}\n'
            param8 = contents_title
            lms += f'{contents_title_lms}\n'
            param9 = contents_url
            lms += f'{contents_url_lms}\n'
        elif idx%8 == 2:
            lms += '\n'
            param10 = org_name
            lms += f'{org_name_lms}\n'
            param11 = contents_title
            lms += f'{contents_title_lms}\n'
            param12 = contents_url
            lms += f'{contents_url_lms}\n'
        elif idx%8 == 3:
            lms += '\n'
            param13 = org_name
            lms += f'{org_name_lms}\n'
            param14 = contents_title
            lms += f'{contents_title_lms}\n'
            param15 = contents_url
            lms += f'{contents_url_lms}\n'
        elif idx%8 == 4:
            lms += '\n'
            param16 = org_name
            lms += f'{org_name_lms}\n'
            param17 = contents_title
            lms += f'{contents_title_lms}\n'
            param18 = contents_url
            lms += f'{contents_url_lms}\n'
        elif idx%8 == 5:
            lms += '\n'
            param19 = org_name
            lms += f'{org_name_lms}\n'
            param20 = contents_title
            lms += f'{contents_title_lms}\n'
            param21 = contents_url
            lms += f'{contents_url_lms}\n'
        elif idx%8 == 6:
            lms += '\n'
            param22 = org_name
            lms += f'{org_name_lms}\n'
            param23 = contents_title
            lms += f'{contents_title_lms}\n'
            param24 = contents_url
            lms += f'{contents_url_lms}\n'
        elif idx%8 == 7:
            lms += '\n'
            param25 = org_name
            lms += f'{org_name_lms}\n'
            param26 = contents_title
            lms += f'{contents_title_lms}\n'
            param27 = contents_url
            lms += f'{contents_url_lms}\n'

            # 240420 여기를 없애야겠네. 전송은 밑에서 한번만.
            # ########### 전송 ###########
            # lms = urllib.parse.quote(lms)
            # params = f'?sendNo={sendNo}&callBackNo={callBackNo}&systemKey={systemKey}&projectId={projectId}&tmplCode={tmplCode}&paramNum={paramNum}&param1={param1}&param2={param2}&param3={param3}&param4={param4}&param5={param5}&param6={param6}&param7={param7}&param8={param8}&param9={param9}&param10={param10}&param11={param11}&param12={param12}&param13={param13}&param14={param14}&param15={param15}&param16={param16}&param17={param17}&param18={param18}&param19={param19}&param20={param20}&param21={param21}&param22={param22}&param23={param23}&param24={param24}&param25={param25}&param26={param26}&param27={param27}&param28={param28}&param29={param29}&param30={param30}&param31={param31}&param32={param32}&param33={param33}&title=K-CaaS&content={lms}'
            # # &param12={param12}&param13={param13}&param14={param14}&param15={param15}&param16={param16}&param17={param17}&param18={param18}&param19={param19}&param20={param20}&param21={param21}&param22={param22}&param23={param23}&param24={param24}&param25={param25}&param26={param26}&param27={param27}&param28={param28}&param29={param29}&param30={param30}&param31={param31}&param32={param32}&param33={param33}'
            # url += params
            # # print(url)
            # try:
            #     request = urllib.request.Request(url)
            #     response = urllib.request.urlopen(request)
            # except Exception as e:
            #     print('error발생')
            #     print(e)
            # rescode = response.getcode()
            # print('response : ', response)
            # print('rescode : ', rescode)
            # print('response.read().decode("utf-8")')
            # print(response.read().decode("utf-8"))
            # # 전송 후 초기화
            # param4 = ''
            # param5 = ''
            # param6 = ''
            # param7 = ''
            # param8 = ''
            # param9 = ''
            # param10 = ''
            # param11 = ''
            # param12 = ''
            # param13 = ''
            # param14 = ''
            # param15 = ''
            # param16 = ''
            # param17 = ''
            # param18 = ''
            # param19 = ''
            # param20 = ''
            # param21 = ''
            # param22 = ''
            # param23 = ''
            # param24 = ''
            # param25 = ''
            # param26 = ''
            # param27 = ''
            # param28 = ''
            # param29 = ''
            # param30 = ''
            # param31 = ''
            # param32 = ''
            # param33 = ''
            # print('############################################################')
            # print('&&&&&&&&&&&&&&&&&&&&&& CNT &&&&&&&&&&&&&&&&&&&&', cnt)
            # cnt += 1
            # time.sleep(5)
        # elif idx%8 == 8:
        #     lms += '\n'
        #     param28 = org_name
        #     lms += f'{org_name_lms}\n'
        #     param29 = contents_title
        #     lms += f'{contents_title_lms}\n'
        #     param30 = contents_url
        #     lms += f'{contents_url_lms}\n'
        # elif idx%8 == 9:
        #     lms += '\n'
        #     param31 = org_name
        #     lms += f'{org_name_lms}\n'
        #     param32 = contents_title
        #     lms += f'{contents_title_lms}\n'
        #     param33 = contents_url
        #     lms += f'{contents_url_lms}\n'
        #     ########### 전송 ###########
        #     lms = urllib.parse.quote(lms)
        #     params = f'?sendNo={sendNo}&callBackNo={callBackNo}&systemKey={systemKey}&projectId={projectId}&tmplCode={tmplCode}&paramNum={paramNum}&param1={param1}&param2={param2}&param3={param3}&param4={param4}&param5={param5}&param6={param6}&param7={param7}&param8={param8}&param9={param9}&param10={param10}&param11={param11}&param12={param12}&param13={param13}&param14={param14}&param15={param15}&param16={param16}&param17={param17}&param18={param18}&param19={param19}&param20={param20}&param21={param21}&param22={param22}&param23={param23}&param24={param24}&param25={param25}&param26={param26}&param27={param27}&param28={param28}&param29={param29}&param30={param30}&param31={param31}&param32={param32}&param33={param33}&title=K-CaaS&content={lms}'
        #     # &param12={param12}&param13={param13}&param14={param14}&param15={param15}&param16={param16}&param17={param17}&param18={param18}&param19={param19}&param20={param20}&param21={param21}&param22={param22}&param23={param23}&param24={param24}&param25={param25}&param26={param26}&param27={param27}&param28={param28}&param29={param29}&param30={param30}&param31={param31}&param32={param32}&param33={param33}'
        #     url += params
        #     # print(url)
        #     try:
        #         request = urllib.request.Request(url)
        #         response = urllib.request.urlopen(request)
        #     except Exception as e:
        #         print('error발생')
        #         print(e)
        #     rescode = response.getcode()
        #     print('response : ', response)
        #     print('rescode : ', rescode)
        #     print('response.read().decode("utf-8")')
        #     print(response.read().decode("utf-8"))
        #     # 전송 후 초기화
        #     param4 = ''
        #     param5 = ''
        #     param6 = ''
        #     param7 = ''
        #     param8 = ''
        #     param9 = ''
        #     param10 = ''
        #     param11 = ''
        #     param12 = ''
        #     param13 = ''
        #     param14 = ''
        #     param15 = ''
        #     param16 = ''
        #     param17 = ''
        #     param18 = ''
        #     param19 = ''
        #     param20 = ''
        #     param21 = ''
        #     param22 = ''
        #     param23 = ''
        #     param24 = ''
        #     param25 = ''
        #     param26 = ''
        #     param27 = ''
        #     param28 = ''
        #     param29 = ''
        #     param30 = ''
        #     param31 = ''
        #     param32 = ''
        #     param33 = ''
        #     print('############################################################')
        #     print('&&&&&&&&&&&&&&&&&&&&&& CNT &&&&&&&&&&&&&&&&&&&&', cnt)
        #     cnt += 1
        #     time.sleep(2)

    # 240420. 전송은 여기서 한번만
    ########### 전송 ###########
    lms = urllib.parse.quote(lms)
    print('@@@@@@@@@@@@마지막 전송@@@@@@@@@@@@')
    params = f'?sendNo={sendNo}&callBackNo={callBackNo}&systemKey={systemKey}&projectId={projectId}&tmplCode={tmplCode}&paramNum={paramNum}&param1={param1}&param2={param2}&param3={param3}&param4={param4}&param5={param5}&param6={param6}&param7={param7}&param8={param8}&param9={param9}&param10={param10}&param11={param11}&param12={param12}&param13={param13}&param14={param14}&param15={param15}&param16={param16}&param17={param17}&param18={param18}&param19={param19}&param20={param20}&param21={param21}&param22={param22}&param23={param23}&param24={param24}&param25={param25}&param26={param26}&param27={param27}&param28={param28}&param29={param29}&param30={param30}&param31={param31}&param32={param32}&param33={param33}&title=K-CaaS&content={lms}'
    # &param12={param12}&param13={param13}&param14={param14}&param15={param15}&param16={param16}&param17={param17}&param18={param18}&param19={param19}&param20={param20}&param21={param21}&param22={param22}&param23={param23}&param24={param24}&param25={param25}&param26={param26}&param27={param27}&param28={param28}&param29={param29}&param30={param30}&param31={param31}&param32={param32}&param33={param33}'
    url += params
    # print(url)
    print('&&&&&&&&&&&&&&&&&&&&&& CNT &&&&&&&&&&&&&&&&&&&&', cnt)
    cnt += 1

    try:
        request = urllib.request.Request(url)
        response = urllib.request.urlopen(request)
    except Exception as e:
        print('error발생')
        print(e)
    rescode = response.getcode()

    print('response : ', response)
    print('rescode : ', rescode)
    print('response.read().decode("utf-8")')
    print(response.read().decode("utf-8"))

today = date.today().strftime("%Y-%m-%d")

# conn = pymysql.connect(host='133.186.209.85', user='212118', password='dpsjwl3570!', db='potal', charset='utf8', cursorclass=pymysql.cursors.DictCursor)
conn = pymysql.connect(host='10.99.2.37', port=54321, user='cds', password='01WhDpsjwl3570%', db='cds', charset='utf8', cursorclass=pymysql.cursors.DictCursor)
cur = conn.cursor()

# 사용자 정보 조회
# 구독 정보가 있는, 승인된 회원만, 휴면상태 아닌 계정만
# sql = "SELECT a.*, INFO_RECV_CLSF, b.seq, b.hash_seq,\
#         case when INFO_RECV_CLSF = 'E0001' then AES_DECRYPT(UNHEX(MBER_EMAIL_ADRES), 'kepco123456') \
#             when INFO_RECV_CLSF  = 'E0002' then AES_DECRYPT(UNHEX(MBER_TELNO), 'kepco123456') \
#              when INFO_RECV_CLSF  = 'E0003' then TELE_CHAT_ID end as 'infoRecv'\
#         FROM (select distinct MBER_ID from col_user_subs_master) A, CSA_MEMBER B\
#         where A.MBER_ID = B.MBER_ID\
#         and B.MBER_STTUS = 1\
#         and B.DORMAN_YN = 'N'"
# 키워드기반 구독신청 테이블에 있는 것도 가져오게 수정
sql = "SELECT a.*, INFO_RECV_CLSF, b.seq, b.hash_seq,\
        CASE \
            WHEN INFO_RECV_CLSF = 'E0001' THEN AES_DECRYPT(UNHEX(MBER_EMAIL_ADRES), 'kepco123456') \
            WHEN INFO_RECV_CLSF = 'E0002' THEN AES_DECRYPT(UNHEX(MBER_TELNO), 'kepco123456') \
            WHEN INFO_RECV_CLSF = 'E0003' THEN TELE_CHAT_ID \
        END AS 'infoRecv'\
        FROM (SELECT DISTINCT MBER_ID FROM col_user_subs_master\
            UNION\
            SELECT DISTINCT MBER_ID FROM csa_user_keyword_subs_master\
        ) a\
        JOIN CSA_MEMBER b ON a.MBER_ID = b.MBER_ID\
        WHERE b.MBER_STTUS = 1\
        AND b.DORMAN_YN = 'N'"

cur.execute(sql)
members = cur.fetchall()
# print(f'사용자 정보 : {members}')

# 추출된 사용자 정보 리스트를 for 루프 등 돌면서 사용자 별 구독카탈로그 정보 조회
for idx, member in enumerate(members):
    print(member["MBER_ID"])
    print(member["infoRecv"])
    # 전송 콘텐츠 담을 df. 사용자별
    df = pd.DataFrame()
    sql = f"SELECT B.CATG_ID, B.CATG_NM, B.CATG_CI_PATH, B.KDCC_CI_URL, B.CATG_CI_WIDTH, B.CATG_CI_HEIGHT, B.CATG_CI_SMALL_YN\
        FROM (select distinct CATG_ID from col_user_subs_master where MBER_ID ='{member['MBER_ID']}') A,\
        CSA_CATALOG_MASTER b\
        where a.catg_id = b.catg_id"
    cur.execute(sql)
    catalogs = cur.fetchall()
    # print(catalogs)
    # 추출된 카탈로그 ID 별 ORG_ID, CATE_ID 조회(org_detail)
    for catalog in catalogs:
        # print(catalog["CATG_ID"])
        sql = f"SELECT C.CODENM as 'orgNm', \
                D.CODENM as 'cateNm',\
                b.ORG_CI_PATH  as 'orgCiPath',\
                b.KDCC_CI_URL,\
                b.ORG_CI_WIDTH,\
                b.ORG_CI_HEIGHT,\
                b.ORG_CI_SMALL_YN,\
                a.*\
            FROM col_user_subs_master A, \
                csa_organization_master b,\
                (select * from cmmncode where CODEID = 'COM00A') C,\
                (select * from cmmncode where CODEID = 'COM00B') D\
            where CATG_ID  = '{catalog['CATG_ID']}' and MBER_ID = '{member['MBER_ID']}' \
                and a.ORG_ID = C.CODE \
                and a.org_id = b.ORG_ID\
            and a.CATE_ID = D.CODE"
        cur.execute(sql)
        organizations = cur.fetchall()
        
        # 단일카탈로그인지 조회
        sql = f"SELECT CATG_ID, COUNT(*) AS CATG_UNDER_ORG\
                FROM (\
                SELECT a.CATG_ID\
                FROM csa_catalog_master a, csa_catalog_detail b\
                WHERE a.CATG_ID = b.CATG_ID \
                GROUP BY b.CATG_ID, b.ORG_ID\
                ) AS subquery\
                where CATG_ID = '{catalog['CATG_ID']}'\
                GROUP BY CATG_ID"
        cur.execute(sql)
        catg_under_org = cur.fetchone()['CATG_UNDER_ORG']
        # print(organizations)
        # org_detail 별 콘텐츠 조회
        for organization in organizations:
            # print(organization["orgNm"], organization["cateNm"])
            sql = f"select SEQ, TITLE, URL, SHORT_URL, COL_DT, b.REQ_KEYWORD1, b.REQ_KEYWORD2, b.REQ_KEYWORD3, b.CONDITION1, b.CONDITION2, b.NEG_KEYWORD1, b.NEG_KEYWORD2, b.NEG_KEYWORD3 \
                    from col_col_contents A, col_user_subs_master b\
                    where A.ORG_ID = '{organization['ORG_ID']}' \
                        and A.CATE_ID = '{organization['CATE_ID']}' \
                        and b.CATG_ID = '{organization['CATG_ID']}'\
                        and A.ORG_ID = b.ORG_ID\
                        and a.CATE_ID = b.CATE_ID\
                        and b.MBER_ID = '{member['MBER_ID']}'\
                        and A.SEND_YN = 'N'"
                        # DATE_FORMAT(DATE_SUB(NOW(), INTERVAL 1 DAY), '%y-%m-%d') = DATE_FORMAT(A.COL_DT, '%y-%m-%d')
                        # and DATE_FORMAT(sysdate(), '%y-%m-%d') = DATE_FORMAT(A.COL_DT, '%y-%m-%d')"
                        # sysdate() '2023-07-31'
            cur.execute(sql)
            contents = cur.fetchall()
            if len(contents) == 0:
                pass
                # print('콘텐츠 없음')
            # 콘텐츠가 사용자가 요청한 키워드에 해당하면 보낼 목록에 추가
            for content in contents:
                match_keyword1 = None
                match_keyword2 = None
                match_keyword3 = None
                if content["REQ_KEYWORD1"] != 'ALL':
                    req_keywords = [content["REQ_KEYWORD1"], content["REQ_KEYWORD2"], content["REQ_KEYWORD3"]]
                    if req_keywords[1] == None or req_keywords[1] == '':
                        req_keywords = req_keywords[:1]
                    elif req_keywords[2] == None or req_keywords[2] == '':
                        req_keywords = req_keywords[:2]
                    neg_keywords = [content["NEG_KEYWORD1"], content["NEG_KEYWORD2"], content["NEG_KEYWORD3"]]
                    neg_keywords = list(filter(lambda x: x is not None and x != '', neg_keywords))
                    conditions = [content["CONDITION1"], content["CONDITION2"]]
                    ############# and 조건 위한 2차원 배열 만들기 #############
                    final = [] # [['디지털', '데이터', '플랫폼']] # [['디지털', '데이터'], ['플랫폼']] 
                    temp = []
                    for i in range(len(req_keywords)-1):
                        if i == 0:
                            temp.append(req_keywords[i])
                        if conditions[i] == 'and':
                            temp.append(req_keywords[i+1])
                        elif conditions[i] == 'or':
                            final.append(temp)
                            temp = []
                            temp.append(req_keywords[i+1])
                    if len(req_keywords) == 1:
                        final.append(req_keywords)
                    else:
                        final.append(temp)    
                    print(final)
                    for i in range(len(final)):
                        for j in range(len(final[i])):
                            if final[i][j] in content["TITLE"]:
                                if j == 0:
                                    match_keyword1 = final[i][j]
                                elif j == 1:
                                    match_keyword2 = final[i][j]
                                elif j == 2:
                                    match_keyword3 = final[i][j]
                                continue
                            else:
                                break
                        else:
                            if any(neg_keyword in content["TITLE"] for neg_keyword in neg_keywords):
                                print('X 제외 키워드에 해당하므로 df에 담지 않습니다.')
                                print(f'TITLE : {content["TITLE"]} 제외키워드 : {neg_keywords}')
                            else:
                                print('O df에 추가')
                                print(f'TITLE : {content["TITLE"]}')
                                new_data = {
                                        'MBER_ID':member["MBER_ID"],
                                        'HASH_SEQ':member["hash_seq"],
                                        'CONTENTS_IDX':content["SEQ"],
                                        '카탈로그명':catalog["CATG_NM"],
                                        '카탈로그 ID':catalog["CATG_ID"],
                                        'ORG_ID':organization['ORG_ID'],
                                        'CATE_ID':organization['CATE_ID'],
                                        '기관명':organization["orgNm"], # com
                                        '분류명':organization["cateNm"], # cate
                                        'TITLE':content["TITLE"], # title
                                        'URL':content["URL"],
                                        'SHORT_URL':content["SHORT_URL"], # url
                                        '수집일자':content["COL_DT"],
                                        '카탈로그 CI':catalog["CATG_CI_PATH"],
                                        '기관 CI':organization["orgCiPath"],
                                        '하위 기관 수':catg_under_org,
                                        '카탈로그 CI(KDCC)':catalog["KDCC_CI_URL"],
                                        '기관 CI(KDCC)':organization["KDCC_CI_URL"],
                                        '카탈로그 CI WIDTH':catalog["CATG_CI_WIDTH"],
                                        '카탈로그 CI HEIGHT':catalog["CATG_CI_HEIGHT"],
                                        '기관 CI WIDTH':organization["ORG_CI_WIDTH"],
                                        '기관 CI HEIGHT':organization["ORG_CI_HEIGHT"],
                                        '카탈로그 CI SMALL':catalog["CATG_CI_SMALL_YN"],
                                        '기관 CI SMALL':organization["ORG_CI_SMALL_YN"],
                                        '요청 키워드1':content["REQ_KEYWORD1"],
                                        '요청 키워드2':content["REQ_KEYWORD2"],
                                        '요청 키워드3':content["REQ_KEYWORD3"],
                                        'MATCH_KEYWORD1':match_keyword1,
                                        'MATCH_KEYWORD2':match_keyword2,
                                        'MATCH_KEYWORD3':match_keyword3,
                                        'CATG_SUBS_YN':'Y'
                                            }
                                df = df.append(new_data, ignore_index=True)
                                # break
                else:
                    neg_keywords = [content["NEG_KEYWORD1"], content["NEG_KEYWORD2"], content["NEG_KEYWORD3"]]
                    neg_keywords = list(filter(lambda x: x is not None and x != '', neg_keywords))
                    if any(neg_keyword in content["TITLE"] for neg_keyword in neg_keywords):
                        print('X 제외 키워드에 해당하므로 df에 담지 않습니다.')
                        print(f'TITLE : {content["TITLE"]} 제외키워드 : {neg_keywords}')
                    else:
                        print('O df에 추가')
                        print(f'TITLE : {content["TITLE"]}')
                        new_data = {
                                'MBER_ID':member["MBER_ID"],
                                'HASH_SEQ':member["hash_seq"],
                                'CONTENTS_IDX':content["SEQ"],
                                '카탈로그명':catalog["CATG_NM"],
                                '카탈로그 ID':catalog["CATG_ID"],
                                'ORG_ID':organization['ORG_ID'],
                                'CATE_ID':organization['CATE_ID'],
                                '기관명':organization["orgNm"], # com
                                '분류명':organization["cateNm"], # cate
                                'TITLE':content["TITLE"], # title
                                'URL':content["URL"],
                                'SHORT_URL':content["SHORT_URL"], # url
                                '수집일자':content["COL_DT"],
                                '카탈로그 CI':catalog["CATG_CI_PATH"],
                                '기관 CI':organization["orgCiPath"],
                                '하위 기관 수':catg_under_org,
                                '카탈로그 CI(KDCC)':catalog["KDCC_CI_URL"],
                                '기관 CI(KDCC)':organization["KDCC_CI_URL"],
                                '카탈로그 CI WIDTH':catalog["CATG_CI_WIDTH"],
                                '카탈로그 CI HEIGHT':catalog["CATG_CI_HEIGHT"],
                                '기관 CI WIDTH':organization["ORG_CI_WIDTH"],
                                '기관 CI HEIGHT':organization["ORG_CI_HEIGHT"],
                                '카탈로그 CI SMALL':catalog["CATG_CI_SMALL_YN"],
                                '기관 CI SMALL':organization["ORG_CI_SMALL_YN"],
                                '요청 키워드1':content["REQ_KEYWORD1"],
                                '요청 키워드2':content["REQ_KEYWORD2"],
                                '요청 키워드3':content["REQ_KEYWORD3"],
                                'MATCH_KEYWORD1':content["REQ_KEYWORD1"], # ALL인 경우라서
                                'MATCH_KEYWORD2':match_keyword2,
                                'MATCH_KEYWORD3':match_keyword3,
                                'CATG_SUBS_YN':'Y'
                                    }
                        df = df.append(new_data, ignore_index=True)
                        # break
    # 구독카탈로그 기반 콘텐츠 추가
    print('구독카탈로그 기반 콘텐츠 추가 완료')
    print(df)

    # 키워드 기반
    sql = f"select A.*, B.CODENM as ORG_NM, C.CODENM as CATE_NM, D.*\
            from col_col_contents A\
            join cmmncode B on A.ORG_ID = B.CODE\
            join cmmncode C on A.cate_id = C.code\
            join csa_catalog_master D on B.CODENM = D.CATG_NM\
            where SEND_YN  = 'N'"
    cur.execute(sql)
    contents = cur.fetchall()

    sql = f"select A.PRDEF_REQ_KEYWORD, A.INPUT_REQ_KEYWORD, B.KEYWORD, C.RELATED_KEYWORD\
            from csa_user_keyword_subs_master A\
            left outer join csa_keyword_dic_master B\
            on A.PRDEF_REQ_KEYWORD = B.SEQ\
            left outer join csa_keyword_dic_detail C\
            on B.SEQ = C.SEQ \
            where A.USE_YN = 'Y'\
            and A.MBER_ID = '{member['MBER_ID']}'"
    cur.execute(sql)
    keyword_rows = cur.fetchall()
    keywords = set()
    for keyword_row in keyword_rows:
        if keyword_row['INPUT_REQ_KEYWORD'] != None:
            keywords.add(keyword_row['INPUT_REQ_KEYWORD'])
        if keyword_row['KEYWORD'] != None:
            keywords.add(keyword_row['KEYWORD'])
        if keyword_row['RELATED_KEYWORD'] != None:
            keywords.add(keyword_row['RELATED_KEYWORD'])
    print('####### 키워드 기반 구독신청 키워드 #######')
    print(keywords)

    if len(keywords) > 0:
        for content in contents:
            # print(content['TITLE'])
            for keyword in keywords:
                # print(keyword)
                if keyword in content['TITLE']:
                    print(content['TITLE'])
                    print(keyword)
                    print('키워드 기반 해당하는 keyword')
                    new_data = {
                                'MBER_ID':member["MBER_ID"],
                                'HASH_SEQ':member["hash_seq"],
                                'CONTENTS_IDX':content["SEQ"],
                                '카탈로그명':content["CATG_NM"],
                                '카탈로그 ID':content["CATG_ID"],
                                'ORG_ID':content['ORG_ID'],
                                'CATE_ID':content['CATE_ID'],
                                '기관명':content["ORG_NM"], # com
                                '분류명':content["CATE_NM"], # cate
                                'TITLE':content["TITLE"], # title
                                'URL':content["URL"],
                                'SHORT_URL':content["SHORT_URL"], # url
                                '수집일자':content["COL_DT"],
                                '카탈로그 CI':content["CATG_CI_PATH"],
                                '기관 CI':content["CATG_CI_PATH"],
                                '하위 기관 수':1,
                                '카탈로그 CI(KDCC)':content["KDCC_CI_URL"],
                                '기관 CI(KDCC)':content["KDCC_CI_URL"],
                                '카탈로그 CI WIDTH':content["CATG_CI_WIDTH"],
                                '카탈로그 CI HEIGHT':content["CATG_CI_HEIGHT"],
                                '기관 CI WIDTH':content["CATG_CI_WIDTH"],
                                '기관 CI HEIGHT':content["CATG_CI_HEIGHT"],
                                '카탈로그 CI SMALL':content["CATG_CI_SMALL_YN"],
                                '기관 CI SMALL':content["CATG_CI_SMALL_YN"],
                                '요청 키워드1':'',
                                '요청 키워드2':'',
                                '요청 키워드3':'',
                                'MATCH_KEYWORD1':keyword,
                                'MATCH_KEYWORD2':None,
                                'MATCH_KEYWORD3':None,
                                'CATG_SUBS_YN':'N'
                                    }
                    df = df.append(new_data, ignore_index=True)
                    break
    
    df_send = df
    print(df)
    if len(df) > 0:
        print('중복제거')
        df = df.drop_duplicates(['URL'])
        print(df)

        # 메일인 경우에만 정렬하게 밑으로 뺌
        # print('카탈로그 기관 정렬') 
        # df = df.sort_values(by=['카탈로그 ID', 'ORG_ID'])
        # print(df)

        # print('카탈로그 우선순위 반영 전')
        # print(df)

        # 어차피 카탈로그 구독이 위에 있을듯 먼저 쌓이니까
        # print('카탈로그 우선순위 반영 후')
        # df['sort_order'] = (df['CATG_SUBS_YN']=='Y').astype(int)
        # df = df.sort_values(by='sort_order', ascending=False).drop(columns='sort_order')
        # print(df)

        # print('인덱스 리셋')
        # df = df.reset_index()
        # print(df)

        # 메일 아닐 경우에만 기관별 2개씩으로 갯수 줄여주기
        if member["INFO_RECV_CLSF"] != 'E0001':
            print('기관별 2개씩만 뽑기')
            df_send = df.groupby('기관명').apply(lambda x: x.head(2)).reset_index(drop=True)
            # df_send = df.groupby('기관명', as_index=False).apply(lambda x:x.head(2))
            print(df_send)
            print('Y를 위로 끌어올리기')
            df_send = df_send.sort_values(by='CATG_SUBS_YN', ascending=False).reset_index(drop=True)
            print(df_send)

            # 카톡 함수 내로 이동. 텔레그램(20개)도. 
            # print('8개까지 자르기')
            # df_send = df_send.head(8)
            # print(df_send)
        else:
            df_send = df

    # 전송은 df_send
    # 히스토리는 df


    # 사용자 별 전송 및 send history 저장
    MYSQL_HOSTNAME = '10.99.2.37'
    MYSQL_PORT = 54321
    MYSQL_USER = 'cds'
    MYSQL_PASSWORD = '01WhDpsjwl3570%'
    MYSQL_DATABASE = 'cds'

    connection_string = f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOSTNAME}:{MYSQL_PORT}/{MYSQL_DATABASE}'

    db = create_engine(connection_string)
    # 전송 건이 있을 경우에만. 없으면 send history저장 key error 발생.
    if len(df_send) > 0:
        # 메일
        if member["INFO_RECV_CLSF"] == 'E0001':
            # 메일인 경우에만 카탈로그 org로 정렬
            df_send = df_send.sort_values(by=['카탈로그 ID', 'ORG_ID'])
            send_email(df_send, member["infoRecv"])
            # pass
        # 카카오톡
        elif member["INFO_RECV_CLSF"] == 'E0002':
            send_kakao(df_send, member["infoRecv"])
        # 텔레그램
        elif member["INFO_RECV_CLSF"] == 'E0003':
            send_telegram(df_send, member["infoRecv"])

        # send history 저장
        selected_columns = ['MBER_ID', 'MATCH_KEYWORD1', 'MATCH_KEYWORD2', 'MATCH_KEYWORD3', 'CONTENTS_IDX']
        df_selected = df[selected_columns]
        print('############ 저장 시작 ###########')
        for i in range(len(df_selected)):
            try:
                # print(df_maria.iloc[i:i+1])
                df_selected.iloc[i:i+1].to_sql(name="csa_send_history",if_exists='append',con = db, index=False)
            except Exception as e:
                print(e) #or any other action
    else:
        print('df 길이 0. 전송할 콘텐츠 없음')

    # 마지막 idx인 경우에 전송여부 Y로 업데이트
    if idx == len(members)-1:
        print('마지막 member까지 전송이 완료되었습니다. 콘텐츠 전송여부를 Y로 업데이트합니다.')
        data = [
        ]
        # ('KfAmz', 'Y'),
        # ('KfAmz', 'Y'),
        # ('KfAmz', 'Y'),
        # 어제 날짜 콘텐츠들(SEND_YN='N') SHORT_URL 값 가져오기
        # 지금 수준에서는 수집 1회(23시) 전송 1회(8시)
        # 추후 수집, 전송 시간 별로 하게 되면 바뀌어야 함
        sql = "select SHORT_URL\
                from col_col_contents\
                where SEND_YN = 'N'"
                # DATE_FORMAT(DATE_SUB(NOW(), INTERVAL 1 DAY), '%y-%m-%d') = DATE_FORMAT(A.COL_DT, '%y-%m-%d')
                # DATE_FORMAT(sysdate(), '%y-%m-%d') = DATE_FORMAT(COL_DT, '%y-%m-%d')
        cur.execute(sql)
        short_urls = cur.fetchall()
        if len(short_urls) == 0:
            print("업데이트할 콘텐츠가 없습니다. (SEND_YN = 'N' 인 콘텐츠 없음.)")
        print(short_urls)
        # 전송여부 Y로 UPDATE
        for short_url in short_urls:
            data.append(('Y', short_url["SHORT_URL"]))
        print(data)
        stmt = "UPDATE col_col_contents SET SEND_YN = %s WHERE SHORT_URL = %s"
        cur.executemany(stmt, data)
        conn.commit()
        cur.close()
        conn.close()
    print('---------------------------------------')
    print('---------------------------------------')
    print('---------------------------------------')
