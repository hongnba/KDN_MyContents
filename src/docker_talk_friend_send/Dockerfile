FROM python:3.8

# install google chrome(2023.10.11)
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN apt-get -y update
RUN apt-get install -y ./google-chrome-stable_current_amd64.deb

# install chromedriver
RUN apt-get install -yqq unzip
RUN wget https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/116.0.5845.96/linux64/chromedriver-linux64.zip
RUN unzip chromedriver-linux64.zip 
RUN mv /chromedriver-linux64/chromedriver /usr/local/bin/


WORKDIR /app
COPY ./ksubscribe_share /app/ksubscribe_share                       #ksubscribe_share 디렉토리 복사 
COPY ./docker_talk_friend_send /app/docker_talk_friend_send         #docker_talk_friend_send 디렉토리 복사 

#공유라이브러리 설치 
RUN pip install /app/ksubscribe_share

# upgrade pip
RUN pip install --upgrade pip

RUN  pip install -r /app/docker_talk_friend_send/requirements.txt

CMD ["python", "collect_v2"]

