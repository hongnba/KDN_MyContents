import mysql.connector
from ksubscribe_share.db.mariadb_model.articleSentimentVO import ArticleSentimentVO


class ArticleSentimentService:
    def __init__(self, db_config):
        self.conn = mysql.connector.connect(**db_config)
        self.cursor = self.conn.cursor(dictionary=True)

    def insert(self, article: ArticleSentimentVO) -> int:
        sql = """
        INSERT INTO ARTICLE_SENTIMENT
        (orgId, url, positive_ratio, positive_reason, negative_ratio, negative_reason,
         neutral_reason, positive_keywords, negative_keywords, success, created_at)
        VALUES (%(orgId)s, %(url)s, %(positive_ratio)s, %(positive_reason)s,
                %(negative_ratio)s, %(negative_reason)s, %(neutral_reason)s,
                %(positive_keywords)s, %(negative_keywords)s, %(success)s, %(created_at)s)
        """
        self.cursor.execute(sql, article.to_dict())
        self.conn.commit()
        return self.cursor.lastrowid


    def close(self):
        self.cursor.close()
        self.conn.close()