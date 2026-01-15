from ksubscribe_share.db.mariadb_model.articleKeywordsVO import ArticleKeywordsVO
from ksubscribe_share.db.data_migration.mariadb_manager import MariaDBManager  


class ArticleKeywordsService:
    @staticmethod
    def insert_one(article: ArticleKeywordsVO):
        try:
            with MariaDBManager().get_connection() as conn:
                cursor = conn.cursor()
                sql = """
                    INSERT INTO ARTICLE_KEYWORDS
                    (orgId, keywords, ai_keywords, success, url, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, tuple(article.to_dict().values()))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"ArticleKeywordsService.insert_one failed: {e}")
            raise e
