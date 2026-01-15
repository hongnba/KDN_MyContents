# sysemd를 사용한 FastAPI 서버관리 

1. 서비스 파일 생성 

``` bash 
sudo nano /etc/systemd/system/fastapi.service
``` 

2. 아래 내용을 추가
``` ini 
[Unit]
Description=FastAPI Application
After=network.target

[Service]
User=mhchoi
Group=3waysoft
WorkingDirectory=/path/to/your/app
ExecStart=/path/to/your/python /path/to/your/app/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
``` 

* ExecStart: FastAPI 애플리케이션을 실행하는 명령어.
* Restart=always: 프로세스가 중단될 경우 항상 재시작.
* RestartSec=5: 프로세스 재시작 대기 시간(초).

3. 서비스 활성화 및 실행

``` bash 
sudo systemctl daemon-reload
sudo systemctl start fastapi.service
sudo systemctl enable fastapi.service
```

4. 서비스 상태 확인 

``` bash 
sudo systemctl status fastapi.service
```


