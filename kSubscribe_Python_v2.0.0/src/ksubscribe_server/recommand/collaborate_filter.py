from sklearn.feature_extraction.text import CountVectorizer
from ksubscribe_share.db.dbmodelV2.nouse.memberOrgStatVO import MemberOrgStatVO
import typing


def find_top5_my_org_keywords(my_org, debug=False):
    # 1. 특정 기관의 맴버가 가장 많이 구독하고있는 기관 목록 조회
    my_org_keywords = {}
    if debug:
        my_org_keywords = ["전기", "전력", "인공지능", "에너지", "정보보안"]
    else:
        pass

    return my_org_keywords


def find_top5_sub_org_keywords(my_org, debug=False):
    org_top5_org = {}
    if debug:
        org_top5_org = {
            "한국전력공사": ["전기", "전력", "플랫폼", "에너지", "건강"],
            "전력연구원": ["전기", "전력", "반도체", "에너지", "정보보안"],
            "한전 KPS": ["전기", "전력", "플랫폼", "에너지", "정보보안"],
            "한국남동발전": ["전기", "정보보안", "인공지능", "교육", "노동인권"],
            "한국남서발전": ["전기", "전력", "에너지", "로봇", "반도체"],
        }
    else:
        pass

    return org_top5_org


def combine_docs(relative_org, my_org) -> typing.List[typing.List[str]]:
    relative_org["내회사"] = my_org
    docs = []
    for key in relative_org:
        value = ""
        for keyword in relative_org[key]:
            value += f"{keyword} "
        docs.append(value)
    return docs


def dtm(docs: typing.List[typing.List[str]]):
    vectorizer = CountVectorizer()
    matrix = vectorizer.fit_transform(docs)
    matrix = matrix.todense()
    names = vectorizer.get_feature_names_out()
    return matrix, names


def dtm_to_top_n(matrix, names, n):
    values = {}
    for index in range(len(names)):
        name = names[index]
        value = sum(matrix[:, index])
        values[name] = int(value)
    if len(values) < n:
        n = len(values) - 1
    return sorted(values.items(), key=lambda item: item[1], reverse=True)[:n]


def collaborate_filter(my_org, debug=False):
    # 1. 내 기관 맴더들이 가장 많이 구독한 기관의 키워드 조회
    relative_org_keywords = find_top5_sub_org_keywords(my_org, debug)
    # 2. 내 기관 맴버들이 가장 많이 구독한 키워드
    my_org_keywords = find_top5_my_org_keywords(my_org, debug)
    # 3. document 합치기
    docs = combine_docs(relative_org_keywords, my_org_keywords)
    # 4. 많이 사용된 키워드 순위 추출
    matrix, names = dtm(docs)
    # 5. N개 키워드 추출
    return dtm_to_top_n(matrix, names, 5)


def collaborate_filter_v2(org_keywords, sub_keywords):
    # 3. document 합치기
    docs = combine_docs(org_keywords, sub_keywords)
    # 4. 많이 사용된 키워드 순위 추출
    matrix, names = dtm(docs)
    # 5. N개 키워드 추출
    keywords_and_value = dtm_to_top_n(matrix, names, 5)
    return [key[0] for key in keywords_and_value]


if __name__ == "__main__":
    print(collaborate_filter("", True))
