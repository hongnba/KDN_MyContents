from datetime import datetime
from ksubscribe_share.db.service.contentsService import ContentsService
from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO
from ksubscribe_share.db.dbmodelV2.contentsQueueVO import ContentsQueueVO
from ksubscribe_server.analysis.analysis_ollama_generate import AnalysisOllamaGenerateCall
from ksubscribe_share.db.service.commCodeService import CommCodeService
from ksubscribe_share.db.service.predefineKeywordService import PredefineKeywordService
from ksubscribe_share.logger import Logger
import json

def compare_analysis(url: str):
    """특정 URL의 기사를 분석하여 결과 반환"""
    logger = Logger().setup_logger(Logger.docker_scraping_logger_name)
   
    # 1. 기사 조회
    contentsService = ContentsService()
    contents_data = contentsService.findByURL(url)
   
    if not contents_data:
        print(f"URL을 찾을 수 없습니다: {url}")
        return None
   
    contentsVO = ContentsVO.from_mongo(contents_data)
   
    if not contentsVO.contentsRaw or not contentsVO.contentsRaw.contents:
        print(f"기사 원문이 없습니다: {url}")
        return None
   
    print(f"기사 찾음: {contentsVO.title}\n")
   
    # 2. 분석 설정
    org_list = list(CommCodeService().get_org_name_list())
    keywords = PredefineKeywordService().getKeywordList()
   
    org_name_list = ", ".join([org["codeName"] for org in org_list])
    keyword_name_list = ", ".join(keywords)
   
    # 3. queueContent 객체 생성
    queueContent = ContentsQueueVO(
        contentOrgId=contentsVO.contentsOrgId,
        cateId=contentsVO.categoryId,
        title=contentsVO.title,
        url=contentsVO.url
    )
   
    # 4. 분석 실행
    print("=" * 60)
    print("분석 시작...")
    print("=" * 60)
   
    analysisOllama = AnalysisOllamaGenerateCall()
    text = contentsVO.contentsRaw.contents
   
    isSuccess, contentsMetaResult, summary, sentiment, error_result = \
        analysisOllama.analysis_main(
            content=text,
            pred_keyword_list=keyword_name_list,
            org_name_list=org_name_list,
            mycontents_logger=logger,
            queueContent=queueContent
        )
   
    # 5. 분석 결과를 contentsVO에 반영
    if isSuccess and contentsMetaResult:
        # metaSucYN을 "Y" 또는 "N" 문자열로 변환
        meta_flag = contentsMetaResult.metaSucYN
        contentsVO.metaSucYN = "Y" if meta_flag in [True, "Y", "y"] else "N"
        contentsVO.metaAnalyzeDt = contentsMetaResult.metaAnalyzeDt
        contentsVO.contentsMeta = contentsMetaResult.contentsMeta
    else:
        contentsVO.metaSucYN = "N"
        contentsVO.metaAnalyzeDt = datetime.now()
   
    # 6. 기관명과 카테고리명 가져오기
    commCodeService = CommCodeService()
    contentsOrgName = commCodeService.get_orgName_by_orgId(contentsVO.contentsOrgId) if contentsVO.contentsOrgId else None
    categoryName = commCodeService.get_cateName_by_cateId(contentsVO.categoryId) if contentsVO.categoryId else None
   
    # 7. MongoDB 형식으로 변환 (docker_scraping과 동일한 방식)
    result = contentsVO.to_mongo()
   
    # _id를 문자열로 변환
    if '_id' in result:
        result['_id'] = str(result['_id'])
   
    # datetime 객체를 ISO 형식 문자열로 변환
    for field in ['collectDt', 'pubDt', 'rawCollectDt', 'metaAnalyzeDt']:
        if field in result and result[field]:
            if hasattr(result[field], 'isoformat'):
                result[field] = result[field].isoformat()
            else:
                result[field] = str(result[field])
   
    # 기관명과 카테고리명 추가 (to_mongo()에서 제외되므로 별도 추가)
    if contentsOrgName:
        result["contentsOrgName"] = contentsOrgName
    if categoryName:
        result["categoryName"] = categoryName
   
    # 요약 텍스트 추출 (출력용)
    summary_text = None
    if isSuccess and contentsMetaResult and contentsMetaResult.contentsMeta:
        summary_text = contentsMetaResult.contentsMeta.shortSummary or contentsMetaResult.contentsMeta.longSummary
   
    print(f"\n분석 완료")
    print(f"   성공: {isSuccess}")
    if isSuccess:
        if summary_text:
            print(f"   요약: {summary_text[:100]}..." if len(summary_text) > 100 else f"   요약: {summary_text}")
        else:
            print(f"   요약: 없음")
        print(f"   감정: {sentiment}")
   
    return result

if __name__ == "__main__":
    print("분석할 기사의 URL을 입력하세요 (여러 개 입력 시 줄바꿈으로 구분, 빈 줄 입력 시 종료):")
    urls = []
   
    while True:
        url = input().strip()
        if not url:
            break
        urls.append(url)
   
    if urls:
        results = []
        for idx, url in enumerate(urls, 1):
            print(f"\n[{idx}/{len(urls)}] URL 처리 중: {url}")
            print("-" * 60)
            result = compare_analysis(url)
            if result:
                results.append(result)
       
        # JSON 저장
        output_file = f"./analysis_result_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
       
        print(f"\n{'='*60}")
        print(f"전체 분석 완료: {len(results)}개")
        print(f"결과 저장: {output_file}")
        print(f"{'='*60}")
    else:
        print("URL을 입력해주세요.")
