도커 빌드 명령어
docker build -t [이름] -f [도커파일 경로]


도커 실행 명령어 (-v 통해서 마운트 걸어줌)
docker run -v C:/Users/admin/Appl_logs/python:/Appl_logs/python [도커 이미지 이름]

ex:
 docker run -v C:/Users/admin/Appl_logs/python:/Appl_logs/python ksubscribe_python

도커 이미지 저장
docker save -o [도커 이미지 이름].tar [도커 이미지 이름]

도커 이미지 로드
docker load -i [도커 이미지 이름].tar



docker run -v D:/app:/app ksubscribe_python