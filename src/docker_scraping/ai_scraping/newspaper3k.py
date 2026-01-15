from newspaper import Article

class Newspater3kScraper:

    def get_newbody(self, url:str) -> tuple[bool, str, str]:
        """_summary_

        Args:
            url (str): _description_

        Returns:
            tuple[bool, str, str]: 성공실패여부, 타이틀, 뉴스기사 
        """
        try:
            article = Article(url)
            article.download()
            article.parse()
            
            return True, article.title, article.text
        except Exception as e: 
            return False, None, None
        
    def test(self):
                
        news_url_list = [
        "http://www.wsobi.com/news/articleView.html?idxno=229039",
        "http://www.suhyupnews.co.kr/news/articleView.html?idxno=31636",
        "http://www.gasnews.com/news/articleView.html?idxno=113122",
        "http://www.newstnt.com/news/articleView.html?idxno=310450",
        "http://www.newmanagement.co.kr/?p=14432",
        "https://www.sciencetimes.co.kr/news/%EC%84%B8%EC%83%81%EC%9D%98-%EC%88%98%EB%A7%8E%EC%9D%80-%EB%B0%94%EC%9D%B4%EB%9F%AC%EC%8A%A4-%EC%96%B4%EB%96%A4-%EB%B0%94%EC%9D%B4%EB%9F%AC%EC%8A%A4%EA%B0%80-%EC%9C%84%ED%97%98%ED%95%A0%EA%B9%8C/",
        "https://akomnews.com/bbs/board.php?bo_table=news&wr_id=57525",
        "http://www.civicnews.com/news/articleView.html?idxno=37779",
        "https://www.thebell.co.kr/free/content/ArticleView.asp?key=202312141450234760102760",
        "http://www.bigtanews.co.kr/article/view/big202402090002",
        "https://www.dailysecu.com/news/articleView.html?idxno=149008",
        "http://www.mediatoday.co.kr/news/articleView.html?idxno=312845",
        "http://www.marketnews.co.kr/news/articleView.html?idxno=66239"
        ]


        for url in news_url_list:
            article = Article(url)
            article.download()
            article.parse()
            print("------------------------------------------------------")
            print(article.title)  # 기사 제목
            print(article.text)   # 뉴스 본문 (광고 및 불필요한 부분 제거됨)
    
    
    
    
