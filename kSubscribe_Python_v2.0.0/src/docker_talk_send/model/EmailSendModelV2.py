import base64
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import os
import smtplib
import time
from urllib.parse import urlencode
import zlib
from ksubscribe_share.db.dbmodelV2.commCodeVO import CommCodeVO
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.dbmodelV2.contentsImageVO import ContentsImageVO
from docker_talk_send.model.SendResult import SendResult
from ksubscribe_share.db.dbmodelV2.memberVO import MemberVO
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.contentsImageService import ContentsImageService
from ksubscribe_share.logger import Logger
import ksubscribe_share.config as Conf

class EmailSendModel:
    def __init__(self, mail: str, token: str):
        self.mail = mail
        self.token = token
        self.initialized = False
        self.send_type = "Email"
        self.domain_url = Conf.DOMAIN_URL
        self.base_url = Conf.CONTENTS_BASE_URL
        self.resource_url = Conf.MAIL_RESOURCE_URL
        logger = Logger()
        self.docker_collect_logger = logger.setup_logger(logger.docker_talk_send_logger_name)
        
        # ✅ Gmail SMTP 제한 고려
        self.MAX_EMAILS_PER_SESSION = 100  # 100건마다 재연결
        self.EMAIL_DELAY = 1  # 1초 대기 (서버 부하 방지)
        self.EMAIL_SEND_COUNT = 0 # 이메일 전송 횟수
        
    def initialize(self):
        try:
            self.SMTP = smtplib.SMTP('smtp.gmail.com', 587) # 서버랑 포트 정보
            self.SMTP.ehlo() # SMTP 프로토콜의 명령어 중 하나로, Extended Hello를 의미, 클라이언트가 SMTP 서버에 연결된 후 가장 먼저 호출하는 명령어
            self.SMTP.starttls() # TLS 암호화 시작
            self.SMTP.login(self.mail, self.token) # 서버 로그인
            self.initialized = True
            
        except Exception as ex:
            self.docker_collect_logger.info(ex)
            self.initialized = False
    
    def refresh_smtp_connection(self):
        self.docker_collect_logger.info("SMTP 세션 종료 및 재연결")
        try:
            if self.SMTP:
                self.docker_collect_logger.info("SMTP 세션 종료")
                self.SMTP.quit()
        except Exception as e:
            self.docker_collect_logger.info(f"SMTP 종료 중 예외 발생: {e}")
        
        self.docker_collect_logger.info("SMTP 재연결 중...")
        time.sleep(5)  # 5초 대기 (서버 과부하 방지)
        self.initialize()
        
    # request 에 대한 response 를 SendResult 로 리턴해주는 함수
    def return_response(self, receiver: MemberVO, response: dict[str, str], contents: list[ContentsVO]):
        
        self.docker_collect_logger.info(response)
        if not response:
            contentIds = [str(content._id) for content in contents]
            sendResult = SendResult(sendType=self.send_type, receiver=receiver, isSuccess=True, message=response, sendIds=contentIds)
            # 성공/실패 판단
            # if not response:
            #     sendResult = SendResult(sendType=self.send_type, receiver=receiver.mberEmail, isSuccess=True, message="Email sent successfully!", sendIds=add_contents_ids)
            #     return sendResult
            # else:
            #     sendResult = SendResult(sendType=self.send_type, receiver=receiver.mberEmail, isSuccess=False, message=result, sendIds=[])
            #     return sendResult
                # 에러 메시지 추적하는 코드
                # print("Failed to send to the following recipients:")
                # for failed_email, error in result.items():
                #     print(f"  {failed_email}: {error}")
            return sendResult
        
        else:
            sendResult = SendResult(sendType=self.send_type, receiver=receiver, isSuccess=False, message=response, sendIds=[])
            return sendResult
    
    
    def return_exception_response(self, receiver: MemberVO, ex: Exception):
        response = {}
        response["ex"] = str(ex)
        sendResult = SendResult(sendType=self.send_type, receiver=receiver, isSuccess=False, message=response, sendIds=[])
        return sendResult
    
    def send(self, receiver: MemberVO, title: str, contents: list[ContentsVO]):
        try:
            # initialize 체크
            if not self.initialized:
                sendMail = self.mail
                sendResult = SendResult(sendType=self.send_type, receiver=receiver.mberEmail, isSuccess=False, message=f"{sendMail} 의 메일 계정이 유효하지 않습니다.")
                return sendResult
            
            # 요청 객체가 None이면 예외 처리
            if contents is None or len(contents) == 0:
                return SendResult(isSuccess=False, message="Bad Parameter : No Contents", sendIds=[], sendType=self.send_type, receiver=receiver.get_decrypt_email())
            
            # 제목, 본문 작성
            msg = MIMEMultipart()
            msg['Subject'] = title
            msg["Return-Path"] = ""
            # '({today}) (전송모듈테스트)전력유관기관 및 주요기관 동향 - 총 {len(df)}건 알림'
            
            html_content, add_contents = self.make_html(contents)
            
            part2 = MIMEText(html_content, 'html')

            msg.attach(part2)
            msg['From'] = '한전KDN 콘텐츠 구독 서비스'
            msg['To'] = f'{receiver.mberName}'
            mail_address = receiver.get_decrypt_email()
            
            result = self.SMTP.sendmail("", mail_address, msg.as_string())
            
            self.EMAIL_SEND_COUNT += 1
            
            return self.return_response(receiver=receiver, response=result, contents=add_contents)
            
        except Exception as ex:
            return self.return_exception_response(receiver=receiver, ex=ex)    
    
    def HTML_HEADER(self):
        return """
            <!DOCTYPE html>
            <html lang="ko">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            """
        
    def HTML_BODY_TITLE_backup(self, myContents_icon_type : str, myContents_icon_source : str, 
                        calendar_icon_type : str, calendar_icon_source : str, 
                        news_icon_type : str, news_icon_source : str, 
                        formatted_date : str) -> str:
        try:
            html_body_title_template = """
                <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f6fa;">
                    <div>
                        <img src="{myContents_icon_source}" alt="Top Left Image" style="position: absolute; top: 20px; left: 20px; width: 150px; height: 30px;">
                        <div style="position: absolute; top: 20px; right: 20px; display: flex; align-items: center; gap: 10px;">
                            <img src="{calendar_icon_source}" alt="Top Right Image" style="width: 20px; height: 20px;">
                            <p style="margin: 0px 0; font-weight: bold; font-size: 15px; color: #000;">{send_date}</p>
                        </div>
                    </div>

                    <div style="text-align: center; align: center; padding: 0px; margin: 70px 0px 0px 0px;">
                        <img src="{news_icon_source}" alt="News Image" style="width: 100px; height: 100px; display: block; margin: 0 auto 5px;">
                        <h1 style="background-color: #6600e2; 
                        color: #ffffff; 
                        padding: 10px 20px; 
                        font-size: 15px;
                        border-radius: 16px;
                        display: inline-block;
                        min-width: 210px;
                        ">구독 콘텐츠 정기 뉴스레터</h1>
                    </div>
                """
            
            html_body_title_variables = {
                # "myContents_icon_type": myContents_icon_type,
                "myContents_icon_source": myContents_icon_source,
                # "calendar_icon_type": calendar_icon_type,
                "calendar_icon_source": calendar_icon_source,
                # "news_icon_type": news_icon_type,
                "news_icon_source": news_icon_source,
                "send_date": formatted_date,
            }
            
            html_body_title = html_body_title_template.format(**html_body_title_variables)
            return html_body_title
        except Exception as e:
            print(f"다른 예외 발생: {e}")
            return None
            
    def HTML_BODY_TITLE(self, myContents_icon_type : str, myContents_icon_source : str, 
                        calendar_icon_type : str, calendar_icon_source : str, 
                        news_icon_type : str, news_icon_source : str, 
                        formatted_date : str) -> str:
        try:
            html_body_title_template = """
                <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f6fa;">
                    <!-- 상단 영역 시작 -->
                    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width: 508px; margin: 0 auto;">
                    <!-- 상단 로고 + 날짜 -->
                    <tr>
                        <td style="padding: 20px;">
                        <table width="100%" cellpadding="0" cellspacing="0" border="0">
                            <tr>
                            <!-- 좌측 로고 -->
                            <td align="left" valign="middle">
                                <img src="{myContents_icon_source}" alt="Top Left Image" width="150" height="30" style="display: block;">
                            </td>

                            <!-- 우측 날짜 -->
                            <td align="right" valign="middle">
                                <table cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td>
                                    <img src="{calendar_icon_source}" alt="Calendar Icon" width="20" height="20" style="display: block;">
                                    </td>
                                    <td style="padding-left: 10px; font-weight: bold; font-size: 15px; color: #000;">
                                    {send_date}
                                    </td>
                                </tr>
                                </table>
                            </td>
                            </tr>
                        </table>
                        </td>
                    </tr>

                    <!-- 뉴스 타이틀 -->
                    <tr>
                        <td align="center" style="padding-top: 20px; padding-bottom: 20px;">
                        <img src="{news_icon_source}" alt="News Icon" width="100" height="100"
                            style="display: block; margin: 0 auto 5px;">
                        <table cellpadding="0" cellspacing="0" border="0">
                            <tr>
                            <td align="center" bgcolor="#6600e2"
                                style="color: #ffffff; padding: 10px 20px; font-size: 15px; border-radius: 16px;
                                        display: inline-block; min-width: 210px;">
                                구독 콘텐츠 정기 뉴스레터
                            </td>
                            </tr>
                        </table>
                        </td>
                    </tr>
                    </table>
                """
            
            html_body_title_variables = {
                # "myContents_icon_type": myContents_icon_type,
                "myContents_icon_source": myContents_icon_source,
                # "calendar_icon_type": calendar_icon_type,
                "calendar_icon_source": calendar_icon_source,
                # "news_icon_type": news_icon_type,
                "news_icon_source": news_icon_source,
                "send_date": formatted_date,
            }
            
            html_body_title = html_body_title_template.format(**html_body_title_variables)
            return html_body_title
        except Exception as e:
            print(f"다른 예외 발생: {e}")
            return None
            
    def HTML_BODY_CONTENT_backup(self, content_url: str, content_image_source: str, org_image_source: str,
                          orgName: str, pubDt: str, title: str, 
                          longSummary: str, predKeywords: dict[str, int]) -> str:
        try:
            html_body_content_template = """
                <div style="max-width: 508px; max-height: 205px; margin: 20px auto; background-color: #ffffff; border-radius: 10px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); overflow: hidden;">
                    <a href="{content_url}">
                        <div style="display: flex; align-items: center;" border-radius: 10px;>
                            <img src="{content_image_source}" alt="News Image" style="width: 200px; height: 175px; margin: 15px 15px;">
                            <div style="flex: 1; display: flex; flex-direction: column; justify-content: space-between; word-break: break-word;">             
                                <div>
                                    <img src="{org_image_source}" alt="Organization Image" style="height: 20px; width: auto; object-fit: cover;">
                                </div>
                                <p style="margin: 0; font-size: 14px; color: #333; line-height: 1;">{orgName}<span style="color: #999;"> | </span> <span style="font-size: 13px; color: #999;">{pubDt}</span></p>
                                
                                <h2 style="margin: 10px 0; font-size: 15px; color: #000;
                                    display: -webkit-box;            /* Flex 컨테이너, Firefox 에서는 안된다고 함. */
                                    -webkit-line-clamp: 1;          /* 최대 1줄까지 표시 */
                                    -webkit-box-orient: vertical;   /* 수직 방향 */
                                    overflow: hidden;               /* 넘치는 텍스트 숨김 */
                                    text-overflow: ellipsis;        /* ... 표시 */
                                    line-height: 1.0;               /* 줄 높이 */
                                    max-height: calc(1.1em * 1);    /* 최대 높이 (1줄 기준) */">{title}</h2>
                                
                                <p style="margin: 10px 0; font-size: 13px; color: #555; 
                                    display: -webkit-box;            /* Flex 컨테이너, Firefox 에서는 안된다고 함. */
                                    -webkit-line-clamp: 3;          /* 최대 3줄까지 표시 */
                                    -webkit-box-orient: vertical;   /* 수직 방향 */
                                    overflow: hidden;               /* 넘치는 텍스트 숨김 */
                                    text-overflow: ellipsis;        /* ... 표시 */
                                    line-height: 1.3;               /* 줄 높이 */
                                    max-height: calc(1.3em * 3);    /* 최대 높이 (3줄 기준) */">{longSummary}</p>
                                    
                                <p style="margin: 0; font-size: 12px; color: #2F45D5; 
                                    display: -webkit-box;
                                    -webkit-line-clamp: 1;
                                    -webkit-box-orient: vertical;
                                    overflow: hidden;
                                    text-overflow: ellipsis;
                                    line-height: 1;
                                    max-height: calc(1.1em * 1);">{predKeywords}</p>
                            </div>
                        </div>
                    </a>
                </div>
                """
            
            # 변수 값
            html_body_content_variables = {
                "content_url": content_url,
                # "content_image_type": content_image_type,
                "content_image_source": content_image_source,
                # "org_image_type": org_image_type,
                "org_image_source": org_image_source,
                "orgName": orgName,
                "pubDt": pubDt,
                "title": title,
                "longSummary": longSummary,
                "predKeywords": predKeywords,
            }
            
            html_body_content = html_body_content_template.format(**html_body_content_variables)
            return html_body_content
        except Exception as e:
            print(f"다른 예외 발생: {e}")
            return None
    
    def HTML_BODY_CONTENT(self, content_url: str, content_image_source: str, org_image_source: str,
                          orgName: str, pubDt: str, title: str, 
                          longSummary: str, predKeywords: dict[str, int]) -> str:
        try:
            html_body_content_template = """
                <div style="max-width: 508px; max-height: 205px; margin: 20px auto; background-color: #ffffff; border-radius: 10px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); overflow: hidden;">
                    <a href="{content_url}">
                        <div style="display: flex; align-items: center;" border-radius: 10px;>
                            <img src="{content_image_source}" alt="News Image" style="width: 200px; height: 175px; margin: 15px 15px;">
                            <div style="flex: 1; display: flex; flex-direction: column; justify-content: space-between; word-break: break-word;">             
                                <div>
                                    <img src="{org_image_source}" alt="Organization Image" style="height: 20px; width: auto; object-fit: cover;">
                                </div>
                                <p style="margin: 0; font-size: 14px; color: #333; line-height: 1;">{orgName}<span style="color: #999;"> | </span> <span style="font-size: 13px; color: #999;">{pubDt}</span></p>
                                
                                <h2 style="margin: 10px 0; font-size: 15px; color: #000;
                                    width: 95%;
                                    display: block;
                                    overflow: hidden;               /* 넘치는 텍스트 숨김 */
                                    line-height: 1.1;               /* 줄 높이 */
                                    max-height: calc(1.1em * 1);    /* 최대 높이 (1줄 기준) */">{title}</h2>
                                
                                <p style="margin: 10px 0; font-size: 13px; color: #555; 
                                    width: 95%;
                                    display: block;
                                    overflow: hidden;               /* 넘치는 텍스트 숨김 */
                                    line-height: 1.3;               /* 줄 높이 */
                                    max-height: calc(1.3em * 3);    /* 최대 높이 (3줄 기준) */">{longSummary}</p>
                                    
                                <p style="margin: 0; font-size: 12px; color: #2F45D5; 
                                    width: 95%;
                                    display: block;
                                    overflow: hidden;
                                    line-height: 1.1;
                                    max-height: calc(1.1em * 1);">{predKeywords}</p>
                            </div>
                        </div>
                    </a>
                </div>
                """
            
            # 변수 값
            html_body_content_variables = {
                "content_url": content_url,
                # "content_image_type": content_image_type,
                "content_image_source": content_image_source,
                # "org_image_type": org_image_type,
                "org_image_source": org_image_source,
                "orgName": orgName,
                "pubDt": pubDt,
                "title": title,
                "longSummary": longSummary,
                "predKeywords": predKeywords,
            }
            
            html_body_content = html_body_content_template.format(**html_body_content_variables)
            return html_body_content
        except Exception as e:
            print(f"다른 예외 발생: {e}")
            return None
    
    def HTML_BODY_CONTENT_GMail(self, content_url: str, content_image_source: str, org_image_source: str,
                          orgName: str, pubDt: str, title: str, 
                          longSummary: str, predKeywords: dict[str, int]) -> str:
        try:
            html_body_content_template = """
                <!-- 카드 전체 -->
                <table width="100%" cellpadding="0" cellspacing="0" border="0"
                    style="max-width: 508px; margin: 0 auto; background-color: #ffffff; border-radius: 10px; border: 1px solid #ddd; table-layout: fixed;">
                    <tr>
                        <td style="padding: 0;">
                        <a href="{content_url}" style="text-decoration: none; color: inherit; display: block;">
                            <table width="100%" cellpadding="0" cellspacing="0" border="0">
                            <tr>
                                <!-- 이미지 -->
                                <td width="200" style="padding: 15px;">
                                <img src="{content_image_source}" alt="Image" width="200" height="150"
                                    style="display: block; border: 0;" />
                                </td>

                                <!-- 텍스트 -->
                                <td style="padding: 15px; vertical-align: top;">
                                <!-- 조직 정보 -->
                                <img src="{org_image_source}" alt="Org" height="20" style="display: block; margin-bottom: 5px; max-width: 100%;" />
                                <p style="margin: 0; font-size: 14px; color: #333;">
                                    {orgName} <span style="color: #999;"> | </span>
                                    <span style="font-size: 13px; color: #999;">{pubDt}</span>
                                </p>

                                <!-- 제목: 1줄 제한 -->
                                <h2 style="
                                    margin: 10px 0 5px;
                                    font-size: 15px;
                                    color: #000;
                                    line-height: 1.2;
                                    display: block;
                                    max-height: 1.2em; /* 1줄 기준 */
                                    overflow: hidden;
                                ">
                                    {title}
                                </h2>

                                <!-- 요약: 2줄 제한 -->
                                <p style="
                                    margin: 5px 0;
                                    font-size: 13px;
                                    color: #555;
                                    line-height: 1.4;
                                    display: block;
                                    max-height: 2.8em; /* 2줄 기준 */
                                    overflow: hidden;
                                ">
                                    {longSummary}
                                </p>

                                <!-- 키워드 -->
                                <p style="
                                    margin: 5px 0 0; 
                                    font-size: 12px; 
                                    color: #2F45D5; 
                                    display: block;
                                    max-height: 1.2em; /* 1줄 기준 */
                                    overflow: hidden;
                                ">
                                    {predKeywords}
                                </p>
                                </td>
                            </tr>
                            </table>
                        </a>
                        </td>
                    </tr>
                </table>
                
                <table width="100%" cellpadding="0" cellspacing="0" border="0">
                    <tr>
                        <td height="20" style="line-height: 20px; font-size: 0;">&nbsp;</td>
                    </tr>
                </table>
                """
            
            # 변수 값
            html_body_content_variables = {
                "content_url": content_url,
                # "content_image_type": content_image_type,
                "content_image_source": content_image_source,
                # "org_image_type": org_image_type,
                "org_image_source": org_image_source,
                "orgName": orgName,
                "pubDt": pubDt,
                "title": title,
                "longSummary": longSummary,
                "predKeywords": predKeywords,
            }
            
            html_body_content = html_body_content_template.format(**html_body_content_variables)
            return html_body_content
        except Exception as e:
            print(f"다른 예외 발생: {e}")
            return None
    
    def HTML_FOOTER_backup(self):
        return """
            <div style="text-align: center; padding: 20px; font-size: 12px; color: #000; background-color: #E0E7F6; margin: 50px auto 0px auto;">
                    <span>본 메일은 회원님의 뉴스레터 수신동의 여부를 확인한 후 발송되는 메일입니다. 더이상 수신을 원하지 않으시면 </span>
                    <span>마이페이지 &gt; 정보수정</span>
                    <span>을 통해 수신방법을 변경해주세요.</span>
                    
                    <p>대표전화 : 061-931-7114</p>
                    
                    <p>(58322) 전라남도 나주시 빛가람로 661 (BITGARAM Ro 661) <br />©한전 KDN(주). All right reserved.</p>
                </div>
            </body>
            </html>
            """
       
    def HTML_FOOTER(self):
        return """
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width: 508px; margin: 50px auto 0 auto; background-color: #E0E7F6;">
                <tr>
                    <td align="center" style="padding: 20px; font-size: 12px; color: #000;">
                    <p style="margin: 0;">
                        본 메일은 회원님의 뉴스레터 수신동의 여부를 확인한 후 발송되는 메일입니다. 더이상 수신을 원하지 않으시면
                        <a href="{mypage_link}" style="color: #000; text-decoration: underline;">마이페이지 &gt; 정보수정</a>
                        을 통해 수신방법을 변경해주세요.
                    </p>
                    <p style="margin: 10px 0 0;">
                        대표전화 : 061-931-7114
                    </p>
                    <p style="margin: 0;">
                        (58322) 전라남도 나주시 빛가람로 661 (BITGARAM Ro 661) <br />©한전 KDN(주). All right reserved.
                    </p>
                    </td>
                </tr>
            </table>
            </body>
            </html>
            """
       
    @property
    def MYCONTENTS_ICON(self):
        # return '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'
        return self.resource_url + 'mycontents.png'
    
    @property
    def MYCONTENTS_TYPE(self):
        return "png"
    
    @property
    def CALENDAR_ICON(self):
        # return 'iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAHmSURBVHgBvVRLThtBEK2ecUJ2ZJkIG3WkZOys4hsE7xIxk8wNMCfAN7BvAJzA5gIYECB2+AjDjs/CAwKJpdkh7K6iytY0FmosYwneYqbfdPebV9VVDfAeKJSiqi7F+qV5mfsa/I1dc8q1eECDtiKVkEdbzk2oVlBhGZBWby4OE6fg4s+oRgh1AvoMr4AClfLPG1fne1sjDqMQiagJBI0P/Y+tbnf7chox/SMu973+Eouus1Ll+nS/M5woBFF7IVhuwoyQvfkgbMs4Jw9SpNn2zqSDmAQkTAyYmhVky5pFG3wYDZgd6ZNDPggEjOcePiUwAx7m7iuKvKYVFHjG7017GM+RL4Wp1XEtKBSj7kJxuTbG2/lieGwFgrAua1x7c66PXEItTkGacVRml0OazzjX2gmnaQNetFwMKf89+g0zgkNeEg0ZO0OWrhnvVeGLwb+VjBeCMJawXXuHgmw/JQ919tEgrvng/8o4Iv2XKrCc65bLrJpxAtSiIeOsDnv8sD18c3bwbfyv12f7lXHO85I/m0OfcvNc2D3rkAU7/HJeR9OA3VfZZjLSYnwp/dE++cfi1AOvZdTgToGXThKRMMWZpILD1UaZyu3pUWqvr6Eo+nWlVFk6R9pxsiClYoCQOsY3myIGb4FHZgjK6Oi+/N0AAAAASUVORK5CYII='
        return self.resource_url + 'calendar.png'
    
    @property
    def CALENDAR_TYPE(self):
        return "png"
    
    @property
    def NEWS_ICON(self):
    #     return """
    # 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
    # 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
    # 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
    # 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
    # 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
    # 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
    # fgmtzz1os1bZ+nOPvBt3R2F/RwfJBUthYGApdBJ/8h9saGf90Ly4Rn1ueuaBTzz/4g/gMmiLYLrI7dd+7TPXtQXhh7Hnn0QSfw+S767kegqojGM014UpFnJ3pD918Gpz3rpOkpdgjmenZ/7+07/8K/8GLpO2CKZL3P7WCy/cIfLBowiW2xBM91MlBKdaUN02/Kmvv48FTQKdXuiihrm4f/L0Zz77L+EyaotguowakfkiknkE1t0knrYV2m7t6+vLDSN/omcaU46uVq/ta9Tr/+DZF3/9S3CZtUUwXcbtxRdfXNLX3Xb3kr4lq4uFjr62tnB7Pah873d+56VxWGyLbbEttsW22BbbxWz/F2qmaCKa/m4nAAAAAElFTkSuQmCC
    # """
        return self.resource_url + 'newsIcon.png'
    
    @property
    def NEWS_TYPE(self):
        return "png"
    
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
    
    def truncate_string(self, s, max_length=70):
        return s[:max_length] + "..." if len(s) > max_length else s
    
    # html 만들기
    def make_html(self, contents: list[ContentsVO]):
        # Gmail 최대 크기 제한
        GMAIL_MAX_SIZE = 25 * 1024 * 1024  # 25MB in bytes
        
        # 헤더 만들기 (반복 x)
        header = self.HTML_HEADER()
        header_size = len(header.encode('utf-8'))
        
        # footer 만들기 (반복 x)
        footer = self.HTML_FOOTER()
        footer_size = len(footer.encode('utf-8'))
        
        formatted_date = datetime.now().strftime("%Y-%m-%d")
        # 바디 타이틀 만들기 (반복 x)
        body_title = self.HTML_BODY_TITLE(self.MYCONTENTS_TYPE, self.MYCONTENTS_ICON,
                                           self.CALENDAR_TYPE, self.CALENDAR_ICON,
                                           self.NEWS_TYPE, self.NEWS_ICON,
                                           formatted_date)
        
        max_count = 20
        
        if len(contents) > max_count:
            contents = contents[:max_count]
        
        # html 에 추가된 contents id 목록
        add_contents: list[ContentsVO] = []
        
        # 바디 컨텐츠 만들기 (반복 o, 최대 8번)
        body_contents = ""
        add_contents_cnt = 0
        common_service = CommCodeService()
        contents_img_service = ContentsImageService()
        email_size = 0
        
        for content in contents:
            # 필요한 정보 찾기 => Common Code 의 Org Image Source, Type & contents_image 의 image Source, Type
            commCode = common_service.get_commonCode_by_orgId(content.contentsOrgId)
            contentsImage = contents_img_service.get_contentsImage_by_id(content.imageId)
            
            # 못찾으면 continue
            if (commCode is None or contentsImage is None or commCode.imageSource is None or commCode.imgPath is None):
                continue
            
            # 확장자 추출
            org_img_type = os.path.splitext(commCode.imgPath)[1]
            
            # 컨텐츠를 볼 수 있는 url 넣기.
            reordered_list = [content] + [item for item in contents if item is not content]
            content_url = self.make_url_from_contents_list(reordered_list) # 우선 Login 화면으로 이동하기로 해서 필요 없음. # 0829 KDN측에서 다시 링크 이동 요청
            # content_url = self.base_url
            
            
            long_summary = "요약 정보 없음"
            predKeywords = []
            
            if hasattr(content, "contentsMeta"): # not 제거할 것.
                if content.contentsMeta != None:
                    if hasattr(content.contentsMeta, "longSummary"):
                        long_summary = self.truncate_string(content.contentsMeta.longSummary, 70) if content.contentsMeta.longSummary else "요약 정보 없음"
                    if hasattr(content.contentsMeta, "predKeywords"):
                        predKeywords = list(content.contentsMeta.predKeywords.keys())[:3] if content.contentsMeta.predKeywords.keys() else []
                
            if (len(predKeywords) <= 0):
                predKeywords.append("없음")
                
            # contents_image_type =  contentsImage.imageType if contentsImage.image else ""
            # encoded_contents_image = base64.b64encode(contentsImage.image).decode("utf-8") if contentsImage.image else ""
            # encoded_commcode_image = base64.b64encode(commCode.imageSource).decode("utf-8") if commCode.imageSource else ""
            
            contents_image_url = self.domain_url + contentsImage.imageUrl if contentsImage.imageUrl else ""
            commcode_image_url = self.domain_url + commCode.imgPath if commCode.imgPath else ""
            # encoded_commcode_image = base64.b64encode(commCode.imageSource).decode("utf-8") if commCode.imageSource else ""
            
            # 글자 제한수 적용한 title
            truncated_title = self.truncate_string(content.title, 15) if content.title else "제목 정보 없음"
            
            body_content = self.HTML_BODY_CONTENT_GMail(content_url,
                                                  contents_image_url, commcode_image_url,
                                                  content.contentsOrgName, content.pubDt.strftime("%Y-%m-%d"),
                                                  truncated_title, long_summary, predKeywords
                                                  )
            
            # HTML 본문 크기 계산
            body_size = len(body_contents.encode('utf-8'))
            email_size = header_size + body_size + footer_size
            # print(f"Email Size : {email_size} | GMAIL_MAX_SIZE : {GMAIL_MAX_SIZE}")
            if email_size > GMAIL_MAX_SIZE:
                self.docker_collect_logger.info(f"메일 크기 초과: {email_size} | GMAIL_MAX_SIZE : {GMAIL_MAX_SIZE} bytes. 컨텐츠 개수를 추가하지 않습니다. 총 개수 : {len(contents)}, 현재 개수 : {add_contents_cnt}")
                # 이미지 크기 줄이기 (최대 허용 크기에 맞게)
                break
            else:
                body_contents += body_content
                add_contents.append(content)
                add_contents_cnt += 1
        
        # print(f"컨텐츠 html 생성 완료 : {email_size} | GMAIL_MAX_SIZE : {GMAIL_MAX_SIZE} bytes. 컨텐츠 개수를 추가하지 않습니다. 총 개수 : {len(contents)}, 현재 개수 : {add_contents_cnt}")
        
        return (header + body_title + body_contents + footer, add_contents)