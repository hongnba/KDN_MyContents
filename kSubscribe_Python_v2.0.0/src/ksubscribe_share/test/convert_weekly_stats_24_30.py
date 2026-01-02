import json
import csv

# JSON 파일 경로
json_file_path = "/home/themiraclesoft/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src/ksubscribe_share/test/mycontents.weekly_stats_24-30.json"
csv_file_path = "/home/themiraclesoft/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src/ksubscribe_share/test/mycontents.weekly_stats_24-30.csv"

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

def format_keyword_map(keyword_map):
    """키워드 맵을 문자열로 변환 (키워드:횟수 형식)"""
    if not keyword_map or not isinstance(keyword_map, dict):
        return ''
    items = [f"{k}:{v}" for k, v in keyword_map.items()]
    return ', '.join(items)

# JSON 파일 읽기
with open(json_file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# CSV 파일 작성
with open(csv_file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
    fieldnames = [
        'orgId',
        'last_calculate_date',
        'start_date',
        'end_date',
        'startDate',
        'endDate',
        'totalContentsCounts',
        'pastTotalContentsCounts',
        'averagePositiveRatio',
        'averageNegativeRatio',
        'averageNeutralRatio',
        'pastAveragePositiveRatio',
        'totalPositiveContentsCount',
        'totalNegativeContentsCount',
        'totalNeutralContentsCount',
        'totalPositiveKeywordList',
        'totalNegativeKeywordList',
        'positiveKeywordMap',
        'negativeKeywordMap',
        'ollamaReputationChangeReason'
    ]
    
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    
    # 배열의 각 항목 처리
    for item in data:
        # 배열 필드를 문자열로 변환
        total_positive_keywords = ', '.join(item.get('totalPositiveKeywordList', []))
        total_negative_keywords = ', '.join(item.get('totalNegativeKeywordList', []))
        
        # 키워드 맵을 문자열로 변환
        positive_keyword_map = format_keyword_map(item.get('positiveKeywordMap', {}))
        negative_keyword_map = format_keyword_map(item.get('negativeKeywordMap', {}))
        
        row = {
            'orgId': item.get('orgId', ''),
            'last_calculate_date': extract_date(item.get('last_calculate_date', '')),
            'start_date': extract_date(item.get('start_date', '')),
            'end_date': extract_date(item.get('end_date', '')),
            'startDate': extract_date(item.get('startDate', '')),
            'endDate': extract_date(item.get('endDate', '')),
            'totalContentsCounts': item.get('totalContentsCounts', ''),
            'pastTotalContentsCounts': item.get('pastTotalContentsCounts', ''),
            'averagePositiveRatio': item.get('averagePositiveRatio', ''),
            'averageNegativeRatio': item.get('averageNegativeRatio', ''),
            'averageNeutralRatio': item.get('averageNeutralRatio', ''),
            'pastAveragePositiveRatio': item.get('pastAveragePositiveRatio', ''),
            'totalPositiveContentsCount': item.get('totalPositiveContentsCount', ''),
            'totalNegativeContentsCount': item.get('totalNegativeContentsCount', ''),
            'totalNeutralContentsCount': item.get('totalNeutralContentsCount', ''),
            'totalPositiveKeywordList': total_positive_keywords,
            'totalNegativeKeywordList': total_negative_keywords,
            'positiveKeywordMap': positive_keyword_map,
            'negativeKeywordMap': negative_keyword_map,
            'ollamaReputationChangeReason': item.get('ollamaReputationChangeReason', '')
        }
        
        writer.writerow(row)

print(f"CSV 파일이 생성되었습니다: {csv_file_path}")