
from setuptools import setup, find_packages
# requirements.txt 파일 읽기
def read_requirements(file):
    with open(file, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().splitlines()
    
    
setup(
    name="ksubscribe_share",
    version="0.1.0",
    packages=find_packages(),
    description="Shared utility functions for the project",
    author="3waysoft",
    author_email="3waysoft@3waysoft.com",
    url="https://github.com/ksubscribe/share",
    #install_requires=read_requirements("requirements.txt"),  # requirements.txt 연결
)


