import json
import csv
from datetime import datetime

# JSON 파일 경로
json_file_path = "/home/themiraclesoft/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src/ksubscribe_share/test/mycontents.contents_24-30.json"
csv_file_path = "/home/themiraclesoft/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src/ksubscribe_share/test/mycontents.contents_24-30.csv"

def extract_date(date_obj):
    """날짜 객체에서 날짜 문자열 추출"""
    if isinstance(date_obj, dict) and '$date' in date_obj:
        date_str = date_obj['$date']
        # ISO 형식에서 날짜 부분만 추출 (예: "2025-12-30T00:00:00.000Z" -> "2025-12-30")
        if 'T' in date_str:
            return date_str.split('T')[0]
        return date_str
    elif isinstance(date_obj, str):
        return date_obj
    return ''

# JSON 파일 읽기
with open(json_file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# CSV 파일 작성
with open(csv_file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
    fieldnames = [
        'title',
        'url',
        'contentsOrgId',
        'contentsOrgName',
        'categoryId',
        'categoryName',
        'originallink',
        'link',
        'pubDt',
        'collectDt',
        'positiveRatio',
        'negativeRatio',
        'neutralRatio',
        'positiveKeywords',
        'negativeKeywords',
        'neutralKeywords'
    ]
    
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    
    # 각 문서의 sentiments 배열을 순회
    for item in data:
        # 문서 레벨 필드 추출
        title = item.get('title', '')
        url = item.get('url', '')
        contents_org_id = item.get('contentsOrgId', '')
        contents_org_name = item.get('contentsOrgName', '')
        category_id = item.get('categoryId', '')
        category_name = item.get('categoryName', '')
        originallink = item.get('originallink', '')
        link = item.get('link', '')
        pub_dt = extract_date(item.get('pubDt', ''))
        collect_dt = extract_date(item.get('collectDt', ''))
        
        # sentiments 배열 처리
        if 'contentsMeta' in item and item['contentsMeta']:
            sentiments = item['contentsMeta'].get('sentiments', [])
            
            for sentiment in sentiments:
                # keywords 배열을 문자열로 변환 (쉼표로 구분)
                positive_keywords = ', '.join(sentiment.get('positiveKeywords', []))
                negative_keywords = ', '.join(sentiment.get('negativeKeywords', []))
                neutral_keywords = ', '.join(sentiment.get('neutralKeywords', []))
                
                row = {
                    'title': title,
                    'url': url,
                    'contentsOrgId': contents_org_id,
                    'contentsOrgName': contents_org_name,
                    'categoryId': category_id,
                    'categoryName': category_name,
                    'originallink': originallink,
                    'link': link,
                    'pubDt': pub_dt,
                    'collectDt': collect_dt,
                    'positiveRatio': sentiment.get('positiveRatio', ''),
                    'negativeRatio': sentiment.get('negativeRatio', ''),
                    'neutralRatio': sentiment.get('neutralRatio', ''),
                    'positiveKeywords': positive_keywords,
                    'negativeKeywords': negative_keywords,
                    'neutralKeywords': neutral_keywords
                }
                
                writer.writerow(row)

print(f"CSV 파일이 생성되었습니다: {csv_file_path}")