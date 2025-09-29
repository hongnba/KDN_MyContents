from bs4 import BeautifulSoup
from bs4 import NavigableString
import requests
from ksubscribe_share.db.dbmodel.webSite import WebSite


class WebInfoLoader:
    def __init__(self):
        pass

    def GetWebInfo(self, url):
        # 이미 정보가 있는지 확인
        query_dict = {}
        query_dict["tld_url"] = self.GetTldUrl(url)
        webinfolist = WebSite.find_many(query_dict)

        if len(webinfolist) != 0:
            return

        try:
            html = self.GetHTML(url)
        except:
            return

        selectors = self.GetSelectors(html)

        if len(selectors) > 0:
            webinfo = WebSite(
                tld_url=self.GetTldUrl(url),
                selector=selectors,
            )
            webinfo.insert_one()

    def GetSelectors(self, html):
        soup = BeautifulSoup(html, "html.parser")
        parts = []

        # p단락 검사
        # 만약 2개의 이상의 단락이 있으면 본문으로 가정
        for paragraph in soup.find_all("p"):
            parent_div = paragraph.find_parent(True)

            if parent_div and len(parent_div.find_all("p")) > 5:
                return self.GetCssSelectors(parent_div)

        # div 글자수로 검사 (글자수가 길면 본문으로 가정)
        for div in soup.find_all("div"):
            direct_text = ""
            for child in div.children:
                if isinstance(child, NavigableString):
                    direct_text += child

            if len(direct_text) > 300:
                return self.GetCssSelectors(div)

        # article 글자수로 검사 (글자수가 길면 본문으로 가정)
        for article in soup.find_all("article"):
            direct_text = ""
            for child in article.children:
                if isinstance(child, NavigableString):
                    direct_text += child

            if len(direct_text) > 300:
                return self.GetCssSelectors(article)

        return "Not detected"

    def GetCssSelectors(self, div):
        parts = []
        while div is not None and div.name != "[document]":
            selector = div.name
            if div.get("id"):
                selector += f"#{div['id']}"
                parts.insert(0, selector)
                break
            elif div.get("class"):
                selector += "." + ".".join(div["class"])
            else:
                sibling_count = 1
                sibling = div.previous_sibling
                while sibling:
                    if sibling.name == div.name:
                        sibling_count += 1
                    sibling = sibling.previous_sibling
                if sibling_count > 1:
                    selector += f":nth-of-type({sibling_count})"

            parts.insert(0, selector)
            div = div.parent

        return " > ".join(parts)

    def GetHTML(self, url):
        response = requests.get(url)

        if response.status_code == 200:
            html = response.text
            result = html

        return result

    def GetTldUrl(self, url):
        parts = url.split("/")
        return f"{parts[0]}//{parts[2]}"

    def GetClassName(self, div, depth):
        # 3번 이상 들어가면 null 반환
        if depth > 3:
            return "Too deep"

        parent_div = div.find_parent(True)

        # class name 추출
        if "class" in parent_div.attrs:
            return parent_div["class"]

        # class name이 없으면 부모로 재귀
        return self.GetClassName(parent_div, depth + 1)
