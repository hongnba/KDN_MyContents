from pymongo import MongoClient
from ksubscribe_share.db.dbmodel.category import Category


# 카테고리 초기 데이터셋 ###################################################
category_dataset = {"IT", "통신", "과학연구", "AI", "데이터", "전기"}

for category in category_dataset:
    print(category)

    category = Category(name=category, description=category)
    category.insert_one()
