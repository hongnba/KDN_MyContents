from ksubscribe_share.db.data_migration.mariadb_manager import MariaDBManager
from ksubscribe_share.db.mariadb_model.articleSummaryVO import ArticlesSummaryVO

class ArticlesSummaryService:
    @staticmethod
    def insert_one(article: ArticlesSummaryVO):
        with MariaDBManager().get_connection() as conn:
            cursor = conn.cursor()
            sql = """
                INSERT INTO articles_summary
                (orgId, long_summary, short_summary, success, url, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(
                sql,
                tuple(article.to_dict().values())
            )
            conn.commit()
            return cursor.lastrowid

    @staticmethod
    def insert_many(articles: list[ArticlesSummaryVO]):
        """Optional: bulk insert multiple rows"""
        if not articles:
            return 0
        with MariaDBManager().get_connection() as conn:
            cursor = conn.cursor()
            sql = """
                INSERT INTO articles_summary
                (orgId, long_summary, short_summary, success, url, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            data = [tuple(article.to_dict().values()) for article in articles]
            cursor.executemany(sql, data)
            conn.commit()
            return cursor.rowcount