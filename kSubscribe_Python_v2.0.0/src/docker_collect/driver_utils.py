# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

import os
import subprocess
 





def get_driver2(): #git에서 다운받은 SELENIUM_LAYER.zip을 사용했다면, 아래 설정 중 아무것도 건드리지 않는다. 
    # chrome_options = Options()
    # chrome_options.add_argument('--headless')
    # chrome_options.add_argument('--no-sandbox')
    # chrome_options.add_argument('--disable-gpu')
    # chrome_options.add_argument('--window-size=1280x1696')
    # chrome_options.add_argument('--user-data-dir=/tmp/user-data')
    # chrome_options.add_argument('--hide-scrollbars')
    # chrome_options.add_argument('--enable-logging')
    # chrome_options.add_argument('--log-level=0')
    # chrome_options.add_argument('--v=99')
    # chrome_options.add_argument('--single-process')
    # chrome_options.add_argument('--data-path=/tmp/data-path')
    # chrome_options.add_argument('--ignore-certificate-errors')
    # chrome_options.add_argument('--homedir=/tmp')
    # chrome_options.add_argument('--disk-cache-dir=/tmp/cache-dir')
    # chrome_options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36')
    # # chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36')
    # # 이미지 로딩 X
    # chrome_options.add_argument('--blink-settings=imagesEnabled=false')
    # chrome_options.binary_location = "/opt/python/bin/headless-chromium" 
    
    # driver = webdriver.Chrome('/opt/python/bin/chromedriver', chrome_options=chrome_options)
    # # driver.set_page_load_timeout(30)


    # window 버전
    # 옵션 설정
    options = Options()
    # user-agent 설정
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
    options.add_argument('user-agent=' + user_agent)
    options.add_argument('Content-Type=application/json; charset=utf-8')
    options.add_argument('--blink-settings=imagesEnabled=false')
    # options.add_argument('headless') #headless모드 브라우저가 뜨지 않고 실행됩니다

    driver = webdriver.Chrome(executable_path='C:\chromedriver_win32\chromedriver.exe', chrome_options=options)
    return driver

# NEW
# def get_driver():
#     options = webdriver.ChromeOptions()
#     options.binary_location = '/opt/chrome/chrome'
#     options.add_argument('--headless')
#     options.add_argument('--no-sandbox')
#     options.add_argument("--disable-gpu")
#     options.add_argument("--window-size=1280x1696")
#     options.add_argument("--single-process")
#     options.add_argument("--disable-dev-shm-usage")
#     options.add_argument("--disable-dev-tools")
#     options.add_argument("--no-zygote")
#     options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36')
    
#     driver = webdriver.Chrome("/opt/chromedriver", options=options)
#     return driver
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import ksubscribe_share.config as Conf

def get_driver():
    chrome_options = Options()
    
    # Headless 모드 활성화 (Docker 환경 필수)
    chrome_options.add_argument('--headless') 
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--blink-settings=imagesEnabled=false')  # 이미지 로드 비활성화
    
    # 다운로드 경로 설정 (Docker 내부 경로)
    chrome_version = subprocess.check_output(["chromium", "--version"]).decode().strip().split()[1].split(".")[0]
    download_path = Conf.SCRAPING_DOWNLOAD_FOLDER
    prefs = {
        "download.default_directory": download_path,
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    

    # ChromeDriverManager : 크롬 브라우저에 맞는 크롬 드라이버를 알아서 설치해줌.
    chrome_path = ChromeDriverManager(driver_version=chrome_version).install()
    print(f"chrome_path : {chrome_path}")
    # if "THIRD_PARTY_NOTICES.chromedriver" in chrome_path:     
    #     chrome_path = chrome_path.replace("THIRD_PARTY_NOTICES.chromedriver", "chromedriver")
    driver = webdriver.Chrome(service=Service(chrome_path), options=chrome_options)

    return driver

# def get_driver():
#     chrome_options = webdriver.ChromeOptions()
#     chrome_options.add_argument('--no-sandbox')
#     # chrome_options.add_argument('--headless') # 이미지 만들 땐 주석해제 해야 함
#     chrome_options.add_argument('--disable-gpu')
#     chrome_options.add_argument('--disable-dev-shm-usage')
#     chrome_options.add_argument("--window-size=1920,1080")
#     chrome_options.add_argument('--ignore-certificate-errors')
#     # 이미지 로딩 X
#     chrome_options.add_argument('--blink-settings=imagesEnabled=false')
#     # chrome_options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36')
#     chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
#     # driver = webdriver.Chrome('/usr/local/bin/chromedriver', options=chrome_options)
    
#     # 다운로드 경로 지정
#     download_path = r"C:\Users\admin\Downloads\mycontents"#C:\Users\admin\Downloads\mycontents
#     prefs = {
#         "download.default_directory": download_path,  # 다운로드 경로 설정
#         "download.prompt_for_download": False,  # 다운로드 시 사용자 확인 방지
#         "plugins.always_open_pdf_externally": True  # PDF를 브라우저 내에서 열지 않고 다운로드
#     }
#     chrome_options.add_experimental_option("prefs", prefs)
    
#     # ChromeDriverManager : 크롬 브라우저에 맞는 크롬 드라이버를 알아서 설치해줌.
#     chrome_path = ChromeDriverManager().install()
#     if "THIRD_PARTY_NOTICES.chromedriver" in chrome_path:     
#         chrome_path = chrome_path.replace("THIRD_PARTY_NOTICES.chromedriver", "chromedriver")
#     driver = webdriver.Chrome(service=Service(chrome_path), options=chrome_options)

#     return driver