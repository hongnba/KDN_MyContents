from collections import Counter
import typing

from ksubscribe_server.recommand.collaborate_filter import (
    collaborate_filter_v2,
)
from ksubscribe_share.db.dbmodelV2.memberVO import MemberVO
from ksubscribe_share.db.dbmodelV2.contentsOrgVO import ContentsOrgVO
from ksubscribe_share.db.dbmodelV2.nouse.memberOrgStatVO import MemberOrgStatVO
from ksubscribe_share.db.mongoManager import MongoManager
import datetime

from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.service.memberService import MemberService
from ksubscribe_share.db.service.contentsService import ContentsService
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO


def find_best_sub_org_keywords(orgStat: MemberOrgStatVO):

    sortedSubOrgName = sorted(
        orgStat.OrgSubscribeCount,
        key=lambda orgName: orgStat.OrgSubscribeCount[orgName],
        reverse=True,
    )

    result = {}
    coll = MongoManager().getCollection("contents_org")
    for orgName in sortedSubOrgName:
        # 1. Redis 체크

        # 2. 없으면 데이터 조회
        doc = coll.find_one({"orgName": orgName})
        doc = ContentsOrgVO.from_mongo(doc)

        # 3. redis 캐시 추가
        result[orgName] = doc.orgKeywordList
    return result


def find_best_keywords(orgStat: MemberOrgStatVO, limit: int = 2):
    sortedKeywords = sorted(
        orgStat.PredkeywordSubscribeCount,
        key=lambda keyword: orgStat.PredkeywordSubscribeCount[keyword],
        reverse=True,
    )
    return sortedKeywords[:limit]


def find_recent_org_stat(orgId: str):
    coll = MongoManager().getCollection("member_organization_statistics")
    orgStat = (
        coll.find({"mber_org_id": orgId}).sort({"yyyymmdd": -1}).limit(1).to_list()
    )
    return orgStat


def find_best_contents(
    collaborate_keywords: typing.List[str],
    my_keywords: typing.List[str],
    start_0am: datetime.datetime,
    end_24pm: datetime.datetime,
    limit: int = 10,
):
    coll = MongoManager().getCollection("contents")
    col_result = coll.aggregate(
        [
            {
                "$match": {
                    "pubDt": {
                        "$gte": start_0am,
                        "$lt": end_24pm,
                    },
                },
            },
            {
                "$project": {
                    "total": {
                        "$sum": [
                            {"$ifNull": [f"$newsMeta.predKeywords.{key}", 0]}
                            for key in collaborate_keywords
                        ]
                    }
                }
            },
            {"$sort": {"total": -1}},
            {"$limit": int(limit * 0.5)},
        ]
    ).to_list()
    my_result = coll.aggregate(
        [
            {
                "$match": {
                    "pubDt": {
                        "$gte": start_0am,
                        "$lt": end_24pm,
                    },
                },
            },
            {
                "$project": {
                    "total": {
                        "$sum": [
                            {"$ifNull": [f"$newsMeta.predKeywords.{key}", 0]}
                            for key in my_keywords
                        ]
                    }
                }
            },
            {"$sort": {"total": -1}},
            {"$limit": int(limit * 0.5)},
        ]
    ).to_list()
    return col_result + my_result


##############################################################################
def append_unique(target: list[str], source: list[str]) -> None:
    for item in source:
        if item not in target:
            target.append(item)


def reommand_contents(mberId: str, orgId: str):
    # 1. 유저정보 조회
    user: MemberVO = MemberVO.find_one({"mberId": mberId})
    if user is None:
        print("user를 찾을 수 없습니다.")
    else:
        print("user를 찾았습니다:", user)
    
    # 기관 정보 가져오기
    # myOrg: ContentsOrgVO = ContentsOrgVO.find_one({"orgId": user.orgId})
    myOrg: ContentsOrgVO = ContentsOrgVO.find_one({"orgId": orgId})

    # 기관 정보가 없으면?
    if myOrg is None:
        # 기관 정보 활용 안하도록 수정해야 함.
        return
    
    # 2. 내 기관의 사용자들이 구독한 제일 많은 기관 조회
    
    # 3. 가장 많이 구독된 기관의 키워드 조회 Contents_Org > orgKeywordList 반환
    # 근데 orgKeywordList 는 0:"한국에너지기술평가원", 1:"에기평" 과 같은 데이터가 있는데 실제로 원하는 것은 '전력 : 54, 데이터 : 32, 인공지능 : 27' 같음
    
    
    
    # 2. 현재 기관의 구독현황 조회
    # orgStatList = find_recent_org_stat(user.orgId)
    orgStatList = find_recent_org_stat("A0001")
    if len(orgStatList) != 1:
        return

    # 3. Best 구독기관의 키워드 조회
    orgStatVO = MemberOrgStatVO.from_mongo(orgStatList[0])
    subOrgKeywords = find_best_sub_org_keywords(orgStatVO)
    subOrgKeywords[myOrg.orgName] = myOrg.orgKeywordList

    # 4. 가장 많이 구독한 키워드 탐색
    subKeywords = find_best_keywords(orgStatVO, 2)

    # 5. 최고의 N개 키워드 추출
    top_N_keywords = collaborate_filter_v2(subOrgKeywords, subKeywords)

    # 6. 컨텐츠 탐색하기
    now = datetime.datetime.now()
    today_0am = datetime.datetime(now.year, now.month, now.day)
    pastDay = today_0am - datetime.timedelta(days=3)
    today_24pm = today_0am + datetime.timedelta(days=3)
    contents = find_best_contents(
        top_N_keywords, user.keywordSubscribe, pastDay, today_24pm
    )
    result = []
    print(contents)
    for c in contents:
        result.append(str(c["_id"]))
    result = list(set(result))
    return result

# 내가 속한 기관의 멤버들이 구독한 기관의 카테고리에 대한 키워드 Dict
def get_org_member_subs_cate_keywords(mberId: str, orgId: str):
    # 2-1. 내 기관의 사용자들이 구독한 제일 많은 기관 조회
        # 방법
        #  1. 내 기관에 속한 모든 Member 의 정보 가져옴.
        #  2. 모든 Member 의 구독한 기관의 카테고리에서 키워드에 대한 정보 수집
        #    => contentsOrgSubscribe 의 categoryList 에서 keywords 에서 해당 정보 추출
    
    contentsOrgService = ContentsOrgService()
    
    pipeline = [
                {"$match": {"$and": [{"orgId": orgId}, {"mberId": {"$ne": mberId}}]}},
                {"$project": {"_id": 0, "mberId": 1, "contentsOrgSubscribe": 1}},  # 필요한 필드만 선택
                ]
    
    coll = MongoManager().getCollection("member_account")
    org_members = coll.aggregate(pipeline).to_list()
    
    counter = Counter()  # 문자열 카운트를 위한 Counter 객체
    
    # 같은 기관의 멤버들이 구독한 기관에 대한 keyword 를 누적해서 dictionary [전기 : 10, 에너지 : 8 ...] 으로 만들기
    for item in org_members:
        member = MemberVO.from_mongo(item)
        if (hasattr(member, 'contentsOrgSubscribe')):
            for subscribe_org in member.contentsOrgSubscribe:
                if not (hasattr(subscribe_org, 'categoryList')):
                    continue
                
                for category in subscribe_org.categoryList:
                    # 카테고리를 검색할 정보가 없으면 건너뛰기
                    if not (hasattr(category, 'orgId')) or not (hasattr(category, 'cateId')):
                        continue
                    
                    # 카테고리 정보 찾기
                    org, category_detail = ContentsOrgService.findOrgAndCategory(contentsOrgService, category.orgId, category.cateId)
                    
                    # 카테고리를 정보를 못 찾았으면 건너뛰기
                    if (org is None or category_detail is None):
                        continue
                        
                    # 카테고리 정보에 키워드가 없으면 건너뛰기
                    if not (hasattr(category_detail, 'keywords')):
                        continue
                    
                    counter.update(category_detail.keywords)  # CClass -> list[str]
    
    result_keyword_count_dict = dict(counter)
    # 1. 빈 문자열 키 제거
    cleaned_data = {key: value for key, value in result_keyword_count_dict.items() if key != '' and key != None}
    
    # 2. 값 기준으로 정렬 (내림차순)
    sorted_items = sorted(cleaned_data.items(), key=lambda item: item[1], reverse=True)
    
    # 3. 요청한 개수만큼 자르기
    top_items = sorted_items[:5]
    
    # 4. 딕셔너리로 변환하여 반환
    result_keyword_count_dict = dict(top_items)
    
    for key, value in result_keyword_count_dict.items():
        print(f"Key: {key}, Value: {value}")


if __name__ == "__main__":
    reommand_contents("114156798605800635208", "A0001")
