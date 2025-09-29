import sys, os

sys.path.append(
    os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
)  # kSubscribe_Python_v1.0.0
import sys
from datetime import datetime, timedelta
import math
import urllib.request
import json
import concurrent.futures
from ksubscribe_share.db.dbmodel.news import News
from ksubscribe_share.db.dbmodel.category import Category

from ksubscribe_server.fileLoad.webLoader import WebLoader
from ksubscribe_server.models.model import LoadModel

import asyncio


class NaverNewsScraping:
    naverNewsUrl = "https://openapi.naver.com/v1/search/news.json"
    naver_client_id = "pdpWdp6YVWvrAO8L5dwT"
    naver_client_secret = "t4g0vG8aI9"
    display = 100
    sort = "date"
    cateogry_total_dict = {}

    def start_gatherLink(self):
        # categories = Category.find_all()
        categories = ["산업통산자원부", "산자부"]

        # 스레드 풀 생성 (최대 3개의 스레드를 동시에 실행)
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # 각 카테고리에 대해 naverNewsSearch를 스레드로 실행
            # future_to_category = {executor.submit(self.naverNewsSearch, category, self.start): category for category in categories}

            future_to_category = {}

            for category in categories:
                # 카테고리 검색 결과 Count 확인
                self.cateogry_total_dict[category] = self.getCategoryTotal(
                    category
                )

                # 스레드로 실행할 작업을 submit
                future = executor.submit(self.newsCategoryItems_main, category)
                future_to_category[future] = category  # future와 category의 매핑 저장

            # 작업이 완료된 스레드를 순차적으로 확인
            for future in concurrent.futures.as_completed(future_to_category):
                category = future_to_category[future]
                try:
                    result = future.result()
                    print("Thread " + result)
                except Exception as exc:
                    print(f"{category} generated an exception: {exc}")
                    

    def getCategoryTotal(self, category):
        encText = urllib.parse.quote(category)
        url = f"{self.naverNewsUrl}?query={encText}&display=1"
        # print(url)

        request = urllib.request.Request(url)
        request.add_header("X-Naver-Client-Id", self.naver_client_id)
        request.add_header("X-Naver-Client-Secret", self.naver_client_secret)
        response = urllib.request.urlopen(request)
        rescode = response.getcode()

        if rescode == 200:
            response_body = response.read()
            json_data = response_body.decode("utf-8")

            # JSON 데이터를 파싱하여 Python 딕셔너리로 변환
            parsed_data = json.loads(json_data)

            # 기사 목록을 가져옴
            total = parsed_data["total"]
            print("total = " + str(total))
            return total
        else:
            return 0

    def newsCategoryItems_main(self, category):

        total = self.cateogry_total_dict[category]
        page_count = math.ceil(total / self.display)

        if page_count > 10:
            page_count = 10

        for page in range(1, page_count + 1):
            newItemCount, last_pub_date = self.newsCategoryItems(category, page)
            if newItemCount == 0:
                break
            elif last_pub_date != None:
                pass
                #Category.update_lastDate(category._id, last_pub_date)

        return category + " gather completed!"

    def newsCategoryItems(self, category, page):

        encText = urllib.parse.quote(category)
        url = f"{self.naverNewsUrl}?query={encText}&display={self.display}&start={page}&sort={self.sort}"

        request = urllib.request.Request(url)
        request.add_header("X-Naver-Client-Id", self.naver_client_id)
        request.add_header("X-Naver-Client-Secret", self.naver_client_secret)
        response = urllib.request.urlopen(request)
        rescode = response.getcode()

        if rescode == 200:
            response_body = response.read()
            json_data = response_body.decode("utf-8")

            # JSON 데이터를 파싱하여 Python 딕셔너리로 변환
            parsed_data = json.loads(json_data)
            articles = parsed_data["items"]

            newItemCount = 0
            last_pub_date = None
            for article in articles:

                pub_date_str = article["pubDate"]
                date_format = "%a, %d %b %Y %H:%M:%S %z"
                pub_date = datetime.strptime(pub_date_str, date_format)

                #if pub_date.date() > category.lastDate.date():
                news = News(
                    title=article["title"],
                    originallink=article["originallink"],
                    link=article["link"],
                    description=article["description"],
                    pubDate=article["pubDate"],
                    category=category,
                )
                news.insert_one()
                newItemCount += 1
                last_pub_date = pub_date

            print(
                category
                + " document inserted successfully!  == "
                + str(newItemCount)
                + " 건"
            )

            return newItemCount, last_pub_date
        else:
            print("Error Code:" + rescode)
            return 0, None

    def getNews(cls, url):
        pass

    #########################################################
    # link에서 contents load하기
    #########################################################
    def start_gatherContents(self):

        # 스레드 풀 생성 (최대 3개의 스레드를 동시에 실행)
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:

            # 스레드로 실행할 작업을 submit (카테고리 없이)
            future = executor.submit(
                self.gatherContents_main
            )  # gatherContents_main 메서드를 스레드로 시작

            # 작업이 완료될 때까지 대기하고 결과 확인
            try:
                result = future.result()
                print("Thread result: ", result)
            except Exception as exc:
                print(f"Thread generated an exception: {exc}")

    def gatherContents_main(self):

        query_dict = {}
        query_dict["flag"] = False
        newsList = News.find_many(query_dict)

        gatherCount = 0
        for news in newsList:
            result = self.gatherContents(news)
            if result == True:
                gatherCount += 1

        return " gather count = " + str(gatherCount)

    def gatherContents(self, news):

        webLoader = WebLoader()
        # webLoader.WebTotalLoad(news.url)
        result = webLoader.WebTotalLoad(
            "https://n.news.naver.com/mnews/article/119/0002885509?sid=101"
        )

        # asyncio.run(webLoader.WebTotalLoad(news.link))
        # asyncio.run(webLoader.WebTotalLoad("https://n.news.naver.com/mnews/article/119/0002885509?sid=101"))

        # extractor = WebContentExtractor(news.link)
        # extractor.extract_and_save()

        print("debug")


if __name__ == "__main__":
    naver = NaverNewsScraping()
    naver.start_gatherLink()
    #naver.start_gatherContents()
