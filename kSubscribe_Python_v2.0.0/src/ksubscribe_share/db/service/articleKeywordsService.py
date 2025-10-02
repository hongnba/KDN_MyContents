from ksubscribe_share.db.data_migration.mariadb_manager import MariaDBManager
from ksubscribe_share.db.dbmodelV2.articleKeywordsVO import ArticleKeywordsVO

class ArticleKeywordsService:
    @staticmethod
    def insert_one(article: ArticleKeywordsVO):
        with MariaDBManager().get_connection() as conn:
            cursor = conn.cursor()
            sql = """
                INSERT INTO ARTICLE_KEYWORDS
                (orgId, keywords, ai_keywords, success, url, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(
                sql,
                tuple(article.to_dict().values())
            )
            conn.commit()
            return cursor.lastrowid