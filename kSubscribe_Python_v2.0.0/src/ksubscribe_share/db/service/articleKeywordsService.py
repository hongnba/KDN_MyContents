from ksubscribe_share.db.mariadb_model.articleKeywordsVO import ArticleKeywordsVO
from ksubscribe_share.db.data_migration.mariadb_manager import MariaDBManager  


class ArticleSentimentService:
    @staticmethod
    def insert_one(article: ArticleSentimentVO):
        with MariaDBManager().get_connection() as conn:
            cursor = conn.cursor()
            sql = """
                INSERT INTO ARTICLE_SENTIMENT
                (orgId, url, positive_ratio, positive_reason,
                 negative_ratio, negative_reason, neutral_ratio,
                 positive_keywords, negative_keywords, success, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, tuple(article.to_dict().values()))
            conn.commit()
            return cursor.lastrowid
