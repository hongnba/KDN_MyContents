import json
import pandas as pd
import os
import sys
import glob
import argparse
from datetime import datetime

# -----------------------------------------------------------------------------
# 설정: 분석할 JSON 파일 리스트 (자동 생성)
# -----------------------------------------------------------------------------
# 명령줄 인자로 모델 이름 받기
parser = argparse.ArgumentParser(description="Generate Excel report from JSON test results")
parser.add_argument("--model", default="unknown_model", help="The model name used in the tests")
args = parser.parse_args()

model = args.model
OUTPUT_FILENAME_PREFIX = model.replace(":", "-")

# JSON 파일이 위치한 디렉토리 (컨테이너 내부 경로 기준)
BASE_DIR = "/app/ksubscribe_share/test/result/"
# 결과 엑셀 파일 저장 경로 및 접두어
OUTPUT_DIR = "/app/ksubscribe_share/test/test_summary/"

# TARGET_FILES 자동 생성: BASE_DIR에서 최신 JSON 파일 10개
files = glob.glob(os.path.join(BASE_DIR, "*.json"))
files.sort(key=os.path.getmtime, reverse=True)

# 모델 이름으로 필터링 (파일명에 모델 이름이 포함된 것만 선택)
model_normalized = model.replace(":", "-").replace("/", "-")
filtered_files = [f for f in files if model_normalized in os.path.basename(f)]
TARGET_FILES = [os.path.basename(f) for f in filtered_files[:10]]


# -----------------------------------------------------------------------------

def load_json_file(filepath):
    """JSON 파일을 읽어서 파이썬 객체로 반환"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None

def format_list_or_dict(value):
    """리스트나 딕셔너리를 보기 좋은 문자열로 변환"""
    if isinstance(value, list):
        if not value:  # 빈 리스트인 경우 공백 반환
            return ""
        return ", ".join(map(str, value))
    elif isinstance(value, dict):
        return "\n".join([f"{k}: {v}" for k, v in value.items()])
    return value

def count_keywords(value):
    """키워드 개수 카운트 (리스트 또는 쉼표 구분 문자열)"""
    if isinstance(value, list):
        return len(value)
    elif isinstance(value, str) and value.strip():
        return len([k.strip() for k in value.split(',') if k.strip()])
    return 0

def calculate_keyword_ratios(positive_kw, neutral_kw, negative_kw):
    """
    키워드 개수 기반 감정 비율 계산
    Returns: (positiveKeywordRatio, neutralKeywordRatio, negativeKeywordRatio)
    """
    pos_count = count_keywords(positive_kw)
    neu_count = count_keywords(neutral_kw)
    neg_count = count_keywords(negative_kw)
    total = pos_count + neu_count + neg_count
    
    if total == 0:
        return 0.0, 0.0, 0.0
    
    pos_ratio = round((pos_count / total) * 100, 2)
    neu_ratio = round((neu_count / total) * 100, 2)
    neg_ratio = round((neg_count / total) * 100, 2)
    
    return pos_ratio, neu_ratio, neg_ratio

def main():
    print(f"Selected TARGET_FILES (latest 10 JSON files): {TARGET_FILES}")
    print()
    
    # 기사별 데이터를 모을 딕셔너리
    # Key: URL (기사 식별자), Value: { title: 제목, runs: { 1회차: 데이터, 2회차: 데이터 ... } }
    articles_map = {}
    
    # 1. 파일 순회하며 데이터 수집
    for idx, filename in enumerate(TARGET_FILES):
        run_label = f"{idx + 1}회차"
        filepath = os.path.join(BASE_DIR, filename)
        
        print(f"Processing [{run_label}] {filename}...")
        
        data = load_json_file(filepath)
        if not data:
            continue
            
        docs = data.get('docs', [])
        for doc in docs:
            url = doc.get('url')
            if not url:
                continue
                
            title = doc.get('title', 'No Title')
            
            # 기사 맵 초기화
            if url not in articles_map:
                articles_map[url] = {
                    'title': title,
                    'runs': {}
                }
            
            # 메타 데이터 추출
            meta = doc.get('contentsMeta', {})
            if not meta:
                meta = {}
                
            # 감성 분석 정보 (첫 번째 기관 기준)
            sentiments = meta.get('sentiments', [])
            sentiment = sentiments[0] if isinstance(sentiments, list) and len(sentiments) > 0 else {}
            
            # 키워드 기반 감정 비율 계산
            pos_kw = sentiment.get('positiveKeywords', [])
            neu_kw = sentiment.get('neutralKeywords', [])
            neg_kw = sentiment.get('negativeKeywords', [])
            
            pos_count = count_keywords(pos_kw)
            neu_count = count_keywords(neu_kw)
            neg_count = count_keywords(neg_kw)
            
            pos_kw_ratio, neu_kw_ratio, neg_kw_ratio = calculate_keyword_ratios(pos_kw, neu_kw, neg_kw)
            
            # 데이터 추출 및 가공
            if run_label == "1회차":
                extracted = {
                    "title": title,
                    "url": url,
                    "scrapingDuration": meta.get('scrapingDuration'),
                    "analysisDuration": meta.get('analysisDuration'),
                    "totalProcessingDuration": meta.get('totalProcessingDuration'),
                    "predKeywords": format_list_or_dict(meta.get('predKeywords')),
                    "keywords": format_list_or_dict(meta.get('keywords')),
                    "shortSummary": meta.get('shortSummary'),
                    "longSummary": meta.get('longSummary'),
                    "longDetailSummaryFormat1": meta.get('longDetailSummaryFormat1'),
                    "longDetailSummaryFormat2": meta.get('longDetailSummaryFormat2'),
                    "longDetailSummaryFormat3": meta.get('longDetailSummaryFormat3'),
                    "longDetailSummaryFormat4": meta.get('longDetailSummaryFormat4'),
                    "longDetailSummaryFormat5": meta.get('longDetailSummaryFormat5'),
                    "positiveRatio": sentiment.get('positiveRatio'),
                    "negativeRatio": sentiment.get('negativeRatio'),
                    "neutralRatio": sentiment.get('neutralRatio'),
                    "reason": sentiment.get('reason'), # 2025.12.15: 통합 프롬프트(CoT)의 '종합 판단 근거'
                    "positiveReason": sentiment.get('positiveReason'),
                    "neutralReason": sentiment.get('neutralReason'), # 20251209 추가: 중립 비율 판단 근거
                    "negativeReason": sentiment.get('negativeReason'),
                    "positiveKeywords": format_list_or_dict(pos_kw),
                    "negativeKeywords": format_list_or_dict(neg_kw),
                    "neutralKeywords": format_list_or_dict(neu_kw),
                    "positiveKeywordCount": pos_count,
                    "neutralKeywordCount": neu_count,
                    "negativeKeywordCount": neg_count,
                    "positiveKeywordRatio": pos_kw_ratio,
                    "neutralKeywordRatio": neu_kw_ratio,
                    "negativeKeywordRatio": neg_kw_ratio
                }
            else:
                extracted = {
                    "title": "",
                    "url": "",
                    "scrapingDuration": meta.get('scrapingDuration'),
                    "analysisDuration": meta.get('analysisDuration'),
                    "totalProcessingDuration": meta.get('totalProcessingDuration'),
                    "predKeywords": format_list_or_dict(meta.get('predKeywords')),
                    "keywords": format_list_or_dict(meta.get('keywords')),
                    "shortSummary": meta.get('shortSummary'),
                    "longSummary": meta.get('longSummary'),
                    "longDetailSummaryFormat1": meta.get('longDetailSummaryFormat1'),
                    "longDetailSummaryFormat2": meta.get('longDetailSummaryFormat2'),
                    "longDetailSummaryFormat3": meta.get('longDetailSummaryFormat3'),
                    "longDetailSummaryFormat4": meta.get('longDetailSummaryFormat4'),
                    "longDetailSummaryFormat5": meta.get('longDetailSummaryFormat5'),
                    "positiveRatio": sentiment.get('positiveRatio'),
                    "negativeRatio": sentiment.get('negativeRatio'),
                    "neutralRatio": sentiment.get('neutralRatio'),
                    "reason": sentiment.get('reason'), # 2025.12.15: 통합 프롬프트(CoT)의 '종합 판단 근거'
                    "positiveReason": sentiment.get('positiveReason'),
                    "neutralReason": sentiment.get('neutralReason'), # 20251209 추가: 중립 비율 판단 근거
                    "negativeReason": sentiment.get('negativeReason'),
                    "positiveKeywords": format_list_or_dict(pos_kw),
                    "negativeKeywords": format_list_or_dict(neg_kw),
                    "neutralKeywords": format_list_or_dict(neu_kw),
                    "positiveKeywordCount": pos_count,
                    "neutralKeywordCount": neu_count,
                    "negativeKeywordCount": neg_count,
                    "positiveKeywordRatio": pos_kw_ratio,
                    "neutralKeywordRatio": neu_kw_ratio,
                    "negativeKeywordRatio": neg_kw_ratio
                }
            
            # Null 처리 (None인 경우 "Null" 문자열로 변환)
            for k, v in extracted.items():
                if v is None:
                    extracted[k] = "Null"
            
            articles_map[url]['runs'][run_label] = extracted

    # 2. 엑셀 파일 생성
    # 폴더가 없으면 생성
    if not os.path.exists(OUTPUT_DIR):
        try:
            os.makedirs(OUTPUT_DIR)
            print(f"Created directory: {OUTPUT_DIR}")
        except Exception as e:
            print(f"Error creating directory {OUTPUT_DIR}: {e}")
            return

    # 파일명에 날짜/시간 추가
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(OUTPUT_DIR, f"{OUTPUT_FILENAME_PREFIX}_{timestamp}.xlsx")

    print(f"Generating Excel report: {output_file}")
    
    # 행 순서 정의
    row_indices = [
        "title", "url",
        "scrapingDuration", "analysisDuration",
        "totalProcessingDuration",
        "predKeywords", "keywords", "shortSummary", "longSummary",
        "longDetailSummaryFormat1", "longDetailSummaryFormat2", "longDetailSummaryFormat3", "longDetailSummaryFormat4", "longDetailSummaryFormat5",
        "positiveRatio", "negativeRatio", "neutralRatio",
        "reason",
        "positiveReason", "neutralReason", "negativeReason",
        "positiveKeywords", "negativeKeywords", "neutralKeywords",
        "positiveKeywordCount", "neutralKeywordCount", "negativeKeywordCount",
        "positiveKeywordRatio", "neutralKeywordRatio", "negativeKeywordRatio"
    ]
    
    try:
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            for url, article_data in articles_map.items():
                title = article_data['title']
                
                # 시트 이름 생성 (특수문자 제거 및 길이 제한)
                sheet_name = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-'))[:30]
                if not sheet_name:
                    sheet_name = "Untitled"
                
                # 데이터프레임 생성 준비
                df_data = {}
                run_labels = [f"{i+1}회차" for i in range(len(TARGET_FILES))]
                
                for run in run_labels:
                    run_data = article_data['runs'].get(run, {})
                    col_values = []
                    for field in row_indices:
                        col_values.append(run_data.get(field, "Null"))
                    df_data[run] = col_values
                
                df = pd.DataFrame(df_data, index=row_indices)
                
                # 엑셀 시트에 쓰기
                df.to_excel(writer, sheet_name=sheet_name)
                
                # 스타일링 (줄바꿈 처리 등)
                worksheet = writer.sheets[sheet_name]
                
                # 열 너비 조정
                worksheet.column_dimensions['A'].width = 20  # 인덱스 열
                for col_idx in range(2, len(run_labels) + 3): # B열부터 데이터
                    col_letter = chr(64 + col_idx)
                    worksheet.column_dimensions[col_letter].width = 50
                
                # 줄바꿈(Wrap Text) 및 정렬 설정
                from openpyxl.styles import Alignment
                for row in worksheet.iter_rows():
                    for cell in row:
                        cell.alignment = Alignment(wrap_text=True, vertical='top')
                        
        print("Done.")
        
    except ImportError:
        print("Error: pandas or openpyxl is not installed. Please install them using: pip install pandas openpyxl")
    except Exception as e:
        print(f"Error creating Excel file: {e}")

if __name__ == "__main__":
    main()
