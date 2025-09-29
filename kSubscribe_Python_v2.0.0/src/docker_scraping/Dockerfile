FROM python:3.9

# Google Chrome 및 그 의존성 설치
RUN wget -q https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_132.0.6834.83-1_amd64.deb && \
    apt-get -y update && apt-get install -y ./google-chrome-stable_132.0.6834.83-1_amd64.deb && \
    rm google-chrome-stable_132.0.6834.83-1_amd64.deb && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ChromeDriver 설치
RUN wget -q https://storage.googleapis.com/chrome-for-testing-public/132.0.6834.83/linux64/chromedriver-linux64.zip && \
    unzip chromedriver-linux64.zip && \
    mv chromedriver-linux64/chromedriver /usr/local/bin/ && \
    rm -rf chromedriver-linux64.zip chromedriver-linux64

# 작업 디렉토리 설정
WORKDIR /app

# 소스 코드 복사
COPY ./ksubscribe_share /app/ksubscribe_share      
COPY ./docker_scraping /app/docker_scraping   
COPY ./ksubscribe_server /app/ksubscribe_server   
COPY ./docker_collect /app/docker_collect
COPY ./docker_talk_send /app/docker_talk_send    
COPY ./docker_shell /app/docker_shell
COPY ./all_requirements.txt /app/docker_scraping/all_requirements.txt    

# 백업 디렉토리 생성 및 초기 데이터 백업
RUN mkdir /app_backup && cp -a /app/* /app_backup/

# docker_collect에 __init__.py 파일 추가 (없을 경우를 대비)
RUN touch /app/docker_scraping/__init__.py
RUN touch /app/docker_talk_send/__init__.py
RUN touch /app/docker_collect/__init__.py

# 공유 라이브러리 설치
RUN pip install --no-cache-dir /app/ksubscribe_share

# pip 업그레이드
RUN pip install --no-cache-dir --upgrade pip

# 관련 패키지 설치
RUN  pip install --no-cache-dir -r /app/docker_scraping/all_requirements.txt

# Python 모듈 검색 경로 환경 변수 설정
ENV PYTHONPATH=/app

# 실행 명령 
# CMD ["python", "docker_scraping/contents_scraping.py"]
