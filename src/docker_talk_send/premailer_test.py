import base64
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import smtplib

from src.docker_talk_send.model.EmailSendModel import EmailSendModel
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO

# HTML 파일 로드
# with open("index.html", "r", encoding="utf-8") as html_file:
#     html_content = html_file.read()

html_header_template = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
"""

html_body_title_template = """
<body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f6fa;">
	<div>
        <img src="data:image/{myContents_icon_type};base64,{myContents_icon_source}" alt="Top Left Image" style="position: absolute; top: 20px; left: 20px; width: 150px; height: 30px;">
		<div style="position: absolute; top: 20px; right: 20px; display: flex; align-items: center; gap: 10px;">
			<img src="data:image/{calendar_icon_type};base64,{calendar_icon_source}" alt="Top Right Image" style="width: 20px; height: 20px;">
			<p style="margin: 0px 0; font-weight: bold; font-size: 15px; color: #000;">{send_date}</p>
		</div>
    </div>

    <div style="text-align: center; align: center; padding: 0px; margin: 70px 0px 0px 0px;">
		<img src="data:image/{news_icon_type};base64,{news_icon_source}" alt="News Image" style="width: 100px; height: 100px; display: block; margin: 0 auto 5px;">
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

html_body_content_template = """
<!-- 뉴스 카드 반복 시작 -->
<div style="max-width: 508px; max-height: 200px; margin: 20px auto; background-color: #ffffff; border-radius: 10px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); overflow: hidden;">
        <div style="display: flex; align-items: center;">
            <img src="data:image/{content_image_type};base64,{content_image_source}" alt="News Image" style="width: 160px; height: 150px; margin: 15px 15px;">
            <div style="padding: 15px;">
				<div style="display: flex; align-items: center; gap: 10px;">
					
					<!-- 원 안에 기관 이미지 -->
					<div style="width: 25px; height: 25px; border-radius: 50%; overflow: hidden; display: flex; justify-content: center; align-items: center; background-color: #f0f0f0;">
						<img src="data:image/{org_image_type};base64,{org_image_source}" alt="Circular Org Image" style="width: 100%; height: 100%; object-fit: cover;">
					</div>
					
					<p style="margin: 0px; font-size: 13px; color: #333;">{orgName}</p>
					<span style="color: #999;">|</span>
					<p style="margin: 0px; font-size: 13px; color: #999;">{pubDt}</p>
				</div>
                
				<h2 style="margin: 10px 0; font-size: 15px; color: #000;">{title}</h2>
                
                <p style="margin: 10px 0; font-size: 13px; color: #555; 
					display: -webkit-box;            /* Flex 컨테이너, Firefox 에서는 안된다고 함. */
					-webkit-line-clamp: 3;          /* 최대 3줄까지 표시 */
					-webkit-box-orient: vertical;   /* 수직 방향 */
					overflow: hidden;               /* 넘치는 텍스트 숨김 */
					text-overflow: ellipsis;        /* ... 표시 */
					line-height: 1.5;               /* 줄 높이 */
					max-height: calc(1.5em * 3);    /* 최대 높이 (3줄 기준) */
					                   /* 컨테이너 너비 */">{longSummary}</p>
                <p style="margin: 0; font-size: 13px; color: #2F45D5;">{predKeywords}</p>
            </div>
        </div>
    </div>
"""

html_footer_template = """
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

# 헤더에 사용할 이미지 가져오기
myContents_icon_type = None
myContents_icon_source = None

calendar_icon_type = None
calendar_icon_source = None

news_icon_type = None
news_icon_source = None

# 현재 소스 파일의 디렉터리 경로 가져오기
current_dir = os.path.dirname(os.path.abspath(__file__))
img_dir = os.path.join(current_dir, "img")


for file_name in os.listdir(img_dir):
    if file_name.endswith(".jpg") or file_name.endswith(".png"):
        # 파일 이름 파싱
        keyword = file_name.split('.')[0]
        
        ext = os.path.splitext(file_name)[1][1:]
        
        # 이미지 파일 읽기
        file_path = os.path.join(img_dir, file_name)
        with open(file_path, "rb") as file:
            image_bytes = file.read()
            base64_image = base64.b64encode(image_bytes).decode("utf-8")
        
        # myContents Icon 정보
        if (keyword == "myContentsIcon"):
            myContents_icon_type = ext
            myContents_icon_source = base64_image
            
        elif (keyword == "calendarIcon"):
            calendar_icon_type = ext
            calendar_icon_source = base64_image
            
        elif (keyword == "newsIcon"):
            news_icon_type = ext
            news_icon_source = base64_image

# 현재 날짜와 시간
current_datetime = datetime.datetime.now()

# yyyy-mm-dd 형식으로 추출
formatted_date = current_datetime.strftime("%Y-%m-%d")

# 변수 값
html_body_title_variables = {
    "myContents_icon_type": myContents_icon_type,
    "myContents_icon_source": myContents_icon_source,
    "calendar_icon_type": calendar_icon_type,
    "calendar_icon_source": calendar_icon_source,
    "news_icon_type": news_icon_type,
    "news_icon_source": news_icon_source,
    "send_date": formatted_date,
}

# HTML body 의 title 부분 생성
html_body_title = html_body_title_template.format(**html_body_title_variables)

# 변수 값
html_body_content_variables = {
    "content_image_type": news_icon_type,
    "content_image_source": news_icon_source,
    "org_image_type": calendar_icon_type,
    "org_image_source": calendar_icon_source,
    "orgName": "한전 KDN(주)",
    "pubDt": datetime.datetime.now().strftime("%Y-%m-%d"),
    "title": "한전KPS, 지역사회공헌 인정제 보건복지부장관 표창 수훈",
    "longSummary": "한전KPS, 지역사회공헌 인정제 보건복지부장관 표창 수훈한전KPS, 지역사회공헌 인정제 보건복지부장관 표창 수훈한전KPS, 지역사회공헌 인정제 보건복지부장관 표창 수훈",
    "predKeywords": ["#asd", "#qwe", "#zxc", "#qaz"],
}

# HTML body 의 content 부분 생성
html_body_content = html_body_content_template.format(**html_body_content_variables)

# HTML footer 부분 생성

html_content = html_header_template + html_body_title + html_body_content + html_footer_template





mailSend = EmailSendModel('3waysoft.com@gmail.com', 'ygqgarkrfiovqcmk')
# mailSend.initialize()
contents = ContentsVO.find_all()
result = mailSend.send("tmdvlf6636@3waysoft.com", "테스트 제목입니다.", contents)


# html_content = mailSend.make_html(contents=contents)


# s = smtplib.SMTP('smtp.gmail.com', 587) # 서버랑 포트 정보
# s.ehlo() # SMTP 프로토콜의 명령어 중 하나로, Extended Hello를 의미, 클라이언트가 SMTP 서버에 연결된 후 가장 먼저 호출하는 명령어
# s.starttls() # TLS 암호화 시작
# s.login('3waysoft.com@gmail.com', 'ygqgarkrfiovqcmk') # 서버 로그인

# # 제목, 본문 작성
# msg = MIMEMultipart()
# msg['Subject'] = f'테스트 메일입니다.'
# # '({today}) (전송모듈테스트)전력유관기관 및 주요기관 동향 - 총 {len(df)}건 알림'
# part2 = MIMEText(html_content, 'html')

# msg.attach(part2)
# # msg.attach(html)
# # msg['From'] = '한전KDN 데이터 신사업 정보 제공 서비스'
# msg['From'] = '한전KDN 콘텐츠 구독 서비스'
# msg['NonTo'] = 'hh3990@naver.com, hh44683990@gmail.com'
# # msg['NonTo'] = 'jaehyuk_choi2@kdn.com, hh3990@naver.com'
    
# s.sendmail("kepcokdnkcs@gmail.com", "tmdvlf6636@3waysoft.com", msg.as_string())