FROM python:3.9

# # Install Google Chrome and its dependencies
# RUN wget -q https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_132.0.6834.83-1_amd64.deb && \
#     apt-get -y update && apt-get install -y ./google-chrome-stable_132.0.6834.83-1_amd64.deb && \
#     rm google-chrome-stable_132.0.6834.83-1_amd64.deb && \
#     apt-get clean && rm -rf /var/lib/apt/lists/*



# # Install ChromeDriver
# RUN wget -q https://storage.googleapis.com/chrome-for-testing-public/132.0.6834.83/linux64/chromedriver-linux64.zip && \
#     unzip chromedriver-linux64.zip && \
#     mv chromedriver-linux64/chromedriver /usr/local/bin/ && \
#     rm -rf chromedriver-linux64.zip chromedriver-linux64


WORKDIR /app
COPY ./ksubscribe_share /app/ksubscribe_share     
COPY ./docker_talk_send /app/docker_talk_send         

RUN touch /app/docker_talk_send/__init__.py

#공유라이브러리 설치 
RUN pip install /app/ksubscribe_share

# upgrade pip
RUN pip install --upgrade pip

RUN  pip install -r /app/docker_talk_send/requirements.txt

ENV PYTHONPATH=/app

CMD ["python", "docker_talk_send/sendHistory.py"]

