from sklearn.feature_extraction.text import CountVectorizer
import typing


def find_my_keywords(use, debug=False):
    my_keywords = []
    if debug:
        my_keywords = ["전기", "의료", "인공지능", "에너지", "건강"]
    else:
        pass
    return my_keywords


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


def knowledge_filter(user, debug=False):
    # 1. 사용자의 키워드 조회
    return find_my_keywords(user, debug)


if __name__ == "__main__":
    print(knowledge_filter("", True))
