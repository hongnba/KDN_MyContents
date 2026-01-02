#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
수집 URL 작동 여부 확인 스크립트
"""

import sys
import time
import traceback
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO
from ksubscribe_share.logger import Logger
import feedparser
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from docker_collect.driver_utils import get_driver

logger = Logger().setup_logger(Logger.docker_collect_logger_name)

def check_rss_url(url):
    """RSS URL 확인"""
    try:
        f = feedparser.parse(url)
        if f.bozo and f.bozo_exception:
            return False, f"RSS 파싱 오류: {f.bozo_exception}"
        if not f.get('entries'):
            return False, "RSS 항목 없음"
        return True, f"성공 (항목 {len(f['entries'])}개)"
    except Exception as e:
        return False, f"예외: {str(e)}"

def check_api_url(url):
    """API URL 확인 (간단한 GET 요청)"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return True, f"성공 (상태코드: {response.status_code})"
        else:
            return False, f"실패 (상태코드: {response.status_code})"
    except Exception as e:
        return False, f"예외: {str(e)}"

def check_selenium_url(url, driver):
    """Selenium URL 확인"""
    try:
        driver.get(url)
        time.sleep(2)
        title = driver.title
        return True, f"성공 (제목: {title[:50]})"
    except Exception as e:
        return False, f"예외: {str(e)}"

def main():
    logger.info("=" * 100)
    logger.info("수집 URL 작동 여부 확인 시작")
    logger.info("=" * 100)
    
    # IS_USE 필터 없이 모든 기관 조회
    mongoManager = MongoManager()
    collection = mongoManager.getCollection("contents_org")
    cursor = collection.find({})  # IS_USE 필터 제거
    orgs = [ContentsOrgVO.from_mongo(item) for item in cursor]
    
    logger.info(f"총 {len(orgs)}개 기관 확인 (IS_USE 필터 없음)")
    
    driver = None
    selenium_checked = False
    
    for org in orgs:
        if len(org.categoryList) == 0:
            continue
            
        logger.info(f"\n{org.orgId}: {org.orgName} (카테고리 {len(org.categoryList)}개)")
        
        for cate in org.categoryList:
            url = getattr(cate, 'collectUrlInfo', None)
            method = getattr(cate, 'COL_METHOD', 'N/A')
            
            if not url:
                logger.warning(f"  ✗ {cate.cateId}: {cate.cateName} - URL 없음")
                continue
            
            logger.info(f"  {cate.cateId}: {cate.cateName} (방법: {method})")
            logger.info(f"    URL: {url[:80]}..." if len(url) > 80 else f"    URL: {url}")
            
            # 수집 방법별 확인
            if method == "C0001":  # RSS
                success, msg = check_rss_url(url)
            elif method == "C0003":  # SELENIUM
                if not driver:
                    driver = get_driver()
                    selenium_checked = True
                success, msg = check_selenium_url(url, driver)
            else:  # OPEN API
                success, msg = check_api_url(url)
            
            if success:
                logger.info(f"    ✓ {msg}")
            else:
                logger.error(f"    ✗ {msg}")
    
    if driver:
        driver.quit()
    
    logger.info("\n" + "=" * 100)
    logger.info("수집 URL 확인 완료")
    logger.info("=" * 100)

if __name__ == "__main__":
    main()

