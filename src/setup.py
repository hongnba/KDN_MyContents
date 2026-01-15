
from setuptools import setup, find_packages
# requirements.txt 파일 읽기
def read_requirements(file):
    with open(file, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().splitlines()
    
    
setup(
    name="ksubscribe",
    version="1.0.0",
    packages=find_packages(include=["ksubscribe_server", "ksubscribe_share", "docker_collect", "docker_crawl", "docker_talk_friend_send", "docker_talk_send"]),
    description="ksubscribe project package",
    author="3waysoft",
    author_email="3waysoft@3waysoft.com",
    url="https://github.com/ksubscribe/share",
    #install_requires=read_requirements("requirements.txt"),  # requirements.txt 연결
)


