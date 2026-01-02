"""
엑셀 파일에서 중복 기사 제거 및 CSV 변환 스크립트
- 특정 키워드와 날짜 범위의 엑셀 파일들을 로드
- "실패" 행은 메모리에서만 제거 (원본 파일 수정 안 함)
- openapi_collector.py 방식으로 TF-IDF + 코사인 유사도로 중복 제거
- 최종 결과를 CSV로 변환 (naver_news_articles_11.csv 형식)
"""
import pandas as pd
import os
import sys
import glob
from datetime import datetime, timedelta
from sklearn.metrics.pairwise import linear_kernel
from sklearn.feature_extraction.text import TfidfVectorizer
import re


class DuplicateRemover:
    def __init__(self):
        self.input_dir = "/app/ksubscribe_share/test/news_scarppings"
        self.output_dir = "/app/ksubscribe_share/test/news_scarppings"
        
    def extract_date_from_filename(self, filename):
        """파일명에서 날짜 추출 (YYYYMMDD 형식)"""
        match = re.search(r'(\d{8})', filename)
        if match:
            return match.group(1)
        return None
    
    def filter_files_by_date_range(self, files, keyword, start_date_str, end_date_str):
        """날짜 범위에 해당하는 파일만 필터링"""
        filtered_files = []
        
        for file_path in files:
            filename = os.path.basename(file_path)
            
            # 키워드 확인
            if keyword not in filename:
                continue
            
            # 날짜 추출
            file_date = self.extract_date_from_filename(filename)
            if not file_date:
                continue
            
            # 날짜 범위 체크
            if start_date_str and file_date < start_date_str:
                continue
            if end_date_str and file_date > end_date_str:
                continue
            
            filtered_files.append(file_path)
        
        return filtered_files
    
    def load_excel_files(self, keyword, start_date_str, end_date_str):
        """
        날짜 범위에 해당하는 엑셀 파일들을 로드
        
        Returns:
            DataFrame: 모든 파일의 데이터를 합친 DataFrame
        """
        # 파일 패턴: naver_news_{keyword}_*.xlsx
        pattern = os.path.join(self.input_dir, f"naver_news_{keyword}_*.xlsx")
        excel_files = glob.glob(pattern)
        
        if not excel_files:
            print(f"❌ '{keyword}' 키워드의 엑셀 파일을 찾을 수 없습니다.")
            return None
        
        # 날짜 범위 필터링
        excel_files = self.filter_files_by_date_range(excel_files, keyword, start_date_str, end_date_str)
        
        if not excel_files:
            print(f"❌ 지정한 날짜 범위에 해당하는 파일이 없습니다.")
            return None
        
        # 날짜순으로 정렬
        excel_files.sort()
        
        print(f"📂 총 {len(excel_files)}개 파일 로드 예정")
        
        all_dataframes = []
        
        for file_path in excel_files:
            try:
                df = pd.read_excel(file_path, engine='openpyxl')
                
                if df.empty:
                    continue
                
                # 파일명에서 날짜 추출하여 추가
                filename = os.path.basename(file_path)
                file_date = self.extract_date_from_filename(filename)
                
                if file_date:
                    # YYYYMMDD -> YYYY-MM-DD 형식으로 변환
                    formatted_date = f"{file_date[:4]}-{file_date[4:6]}-{file_date[6:8]}"
                    df['파일날짜'] = formatted_date
                
                all_dataframes.append(df)
                print(f"  ✅ {os.path.basename(file_path)}: {len(df)}건")
                
            except Exception as e:
                print(f"  ❌ {os.path.basename(file_path)} 로드 실패: {e}")
                continue
        
        if not all_dataframes:
            print("❌ 로드된 데이터가 없습니다.")
            return None
        
        # 모든 데이터프레임 합치기
        combined_df = pd.concat(all_dataframes, ignore_index=True)
        print(f"\n📊 총 {len(combined_df)}건의 기사 로드 완료")
        
        return combined_df
    
    def remove_failed_articles(self, df):
        """
        "실패" 행을 메모리에서만 제거 (원본 파일 수정 안 함)
        
        Returns:
            DataFrame: 실패 행이 제거된 DataFrame
        """
        if df is None or df.empty:
            return df
        
        # content 컬럼 확인
        content_col = None
        if 'content' in df.columns:
            content_col = 'content'
        elif 'contents' in df.columns:
            content_col = 'contents'
        elif 'description' in df.columns:
            content_col = 'description'
        
        if content_col is None:
            print("⚠️  content 컬럼을 찾을 수 없습니다. 실패 행 제거를 건너뜁니다.")
            return df
        
        # "실패" 또는 "본문 추출 실패"가 포함된 행 찾기
        failed_mask = df[content_col].astype(str).str.contains('실패', na=False)
        failed_count = failed_mask.sum()
        
        if failed_count > 0:
            print(f"  → 실패 행 {failed_count}건 제거 (메모리에서만)")
            df_cleaned = df[~failed_mask].copy()
        else:
            print(f"  → 실패 행 없음")
            df_cleaned = df.copy()
        
        return df_cleaned
    
    def remove_duplicates_by_similarity(self, df):
        """
        openapi_collector.py 방식으로 TF-IDF + 코사인 유사도로 중복 제거
        
        Returns:
            DataFrame: 중복이 제거된 DataFrame
        """
        if df is None or df.empty:
            return df
        
        # 필수 컬럼 확인
        if 'title' not in df.columns and '제목' not in df.columns:
            print("❌ 제목 컬럼을 찾을 수 없습니다.")
            return df
        
        if 'link' not in df.columns and 'URL' not in df.columns:
            print("❌ 링크 컬럼을 찾을 수 없습니다.")
            return df
        
        # 컬럼명 정규화
        title_col = 'title' if 'title' in df.columns else '제목'
        link_col = 'link' if 'link' in df.columns else 'URL'
        
        # content 컬럼 확인
        content_col = None
        if 'content' in df.columns:
            content_col = 'content'
        elif 'contents' in df.columns:
            content_col = 'contents'
        elif 'description' in df.columns:
            content_col = 'description'
        
        if content_col is None:
            print("⚠️  content 컬럼을 찾을 수 없습니다. 제목만으로 중복 제거합니다.")
            # 제목만으로 중복 제거
            df_unique = df.drop_duplicates(subset=[link_col], keep='first')
            print(f"  → URL 기준 중복 제거: {len(df) - len(df_unique)}건 제거")
            return df_unique
        
        # content가 비어있거나 None인 행 처리
        df_with_content = df[df[content_col].notna() & (df[content_col].astype(str).str.strip() != '')].copy()
        df_without_content = df[df[content_col].isna() | (df[content_col].astype(str).str.strip() == '')].copy()
        
        print(f"  → content 있는 기사: {len(df_with_content)}건")
        print(f"  → content 없는 기사: {len(df_without_content)}건")
        
        if len(df_with_content) == 0:
            print("⚠️  content가 있는 기사가 없습니다. URL 기준으로만 중복 제거합니다.")
            df_unique = df.drop_duplicates(subset=[link_col], keep='first')
            return df_unique
        
        # TF-IDF 벡터화
        print(f"  → TF-IDF 벡터화 중...")
        try:
            tfidf = TfidfVectorizer()
            tfidf_matrix = tfidf.fit_transform(df_with_content[content_col].values.astype('U'))
            tfidf_matrix2 = tfidf.fit_transform(df_with_content[title_col].values.astype('U'))
        except Exception as e:
            print(f"  ❌ TF-IDF 벡터화 실패: {e}")
            print(f"  → URL 기준으로만 중복 제거합니다.")
            df_unique = df.drop_duplicates(subset=[link_col], keep='first')
            return df_unique
        
        # 코사인 유사도 계산
        print(f"  → 코사인 유사도 계산 중...")
        cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)
        cosine_sim2 = linear_kernel(tfidf_matrix2, tfidf_matrix2)
        
        n = len(df_with_content)
        duplicate_indices = []
        
        # 중복 기사 찾기
        print(f"  → 중복 기사 검사 중...")
        for i in range(n):
            for j in range(i + 1, n):  # i < j 조건
                if cosine_sim[i][j] >= 0.15 or cosine_sim2[i][j] >= 0.15:
                    # j를 중복으로 표시 (i가 더 먼저 나온 기사이므로 j를 제거)
                    duplicate_indices.append(df_with_content.index[j])
        
        # 중복 인덱스 제거
        duplicate_indices = list(set(duplicate_indices))
        
        if duplicate_indices:
            print(f"  → 중복 기사 {len(duplicate_indices)}건 제거")
            df_with_content_cleaned = df_with_content.drop(index=duplicate_indices)
        else:
            print(f"  → 중복 기사 없음")
            df_with_content_cleaned = df_with_content
        
        # content 없는 기사와 합치기
        if len(df_without_content) > 0:
            df_final = pd.concat([df_with_content_cleaned, df_without_content], ignore_index=True)
        else:
            df_final = df_with_content_cleaned
        
        print(f"  → 최종 기사 수: {len(df_final)}건 (원본: {len(df)}건)")
        
        return df_final
    
    def format_title_with_quotes(self, title):
        """
        기사 제목을 ""로 감싸기
        - pandas의 to_csv가 자동으로 처리하지만, 명시적으로 "" 포함 확인
        - CSV에서 제목은 항상 ""로 감싸져야 함
        """
        if pd.isna(title) or title == '':
            return ''
        
        title_str = str(title).strip()
        
        # 빈 문자열이면 빈 문자열 반환 (pandas가 자동으로 "" 처리)
        if title_str == '':
            return ''
        
        # 이미 ""로 시작하고 끝나면 내부 내용만 반환 (pandas가 다시 감쌀 것)
        if title_str.startswith('"') and title_str.endswith('"') and len(title_str) >= 2:
            # 내부 내용 추출
            inner = title_str[1:-1]
            # 이스케이프된 " 복원
            inner = inner.replace('""', '"')
            return inner
        
        # 일반 문자열은 그대로 반환 (pandas의 to_csv가 자동으로 "" 처리)
        return title_str
    
    def save_to_csv(self, df, keyword, start_date_str, end_date_str):
        """
        DataFrame을 CSV로 저장 (naver_news_articles_11.csv 형식)
        
        컬럼:
        - 날짜: YYYY-MM-DD 형식
        - 구분: (빈 값 또는 추후 추가 가능)
        - 기사 제목: ""로 감싼 형식
        - 기사 URL: 링크
        """
        if df is None or df.empty:
            print("❌ 저장할 데이터가 없습니다.")
            return None
        
        # 컬럼명 매핑
        title_col = 'title' if 'title' in df.columns else '제목'
        link_col = 'link' if 'link' in df.columns else 'URL'
        date_col = 'date' if 'date' in df.columns else ('파일날짜' if '파일날짜' in df.columns else None)
        
        # 결과 DataFrame 생성
        result_df = pd.DataFrame()
        
        # 날짜 컬럼 처리 (파일날짜 우선 사용)
        if '파일날짜' in df.columns:
            result_df['날짜'] = df['파일날짜'].astype(str)
        elif date_col and date_col in df.columns:
            # 날짜 형식 변환 (YYYY-MM-DD)
            dates = []
            for date_val in df[date_col]:
                if pd.isna(date_val):
                    dates.append('')
                else:
                    date_str = str(date_val)
                    # YYYYMMDD 형식인 경우 YYYY-MM-DD로 변환
                    if len(date_str) == 8 and date_str.isdigit():
                        dates.append(f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}")
                    # 이미 YYYY-MM-DD 형식인 경우
                    elif len(date_str) >= 10 and '-' in date_str:
                        dates.append(date_str[:10])
                    else:
                        dates.append('')
            result_df['날짜'] = dates
        else:
            # 날짜를 찾을 수 없으면 빈 문자열
            result_df['날짜'] = ''
        
        # 구분 컬럼 (빈 값)
        result_df['구분'] = ''
        
        # 기사 제목 (원본 유지)
        result_df['기사 제목'] = df[title_col].astype(str)
        
        # 기사 URL
        result_df['기사 URL'] = df[link_col].astype(str)
        
        # 파일명 생성
        date_range = f"{start_date_str}_{end_date_str}" if start_date_str and end_date_str else "all"
        filename = f"naver_news_{keyword}_deduped_{date_range}.csv"
        filepath = os.path.join(self.output_dir, filename)
        
        # CSV 저장 (UTF-8 BOM 포함, 제목만 따옴표로 감싸기)
        # csv.writer를 사용하여 제목만 따옴표로 감싸기
        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            # 헤더 작성
            f.write('날짜,구분,기사 제목,기사 URL\n')
            
            # 데이터 작성
            for idx, row in result_df.iterrows():
                date_val = str(row['날짜']) if pd.notna(row['날짜']) else ''
                category_val = str(row['구분']) if pd.notna(row['구분']) else ''
                title_val = str(row['기사 제목']) if pd.notna(row['기사 제목']) else ''
                url_val = str(row['기사 URL']) if pd.notna(row['기사 URL']) else ''
                
                # 제목만 따옴표로 감싸기
                # 내부의 "를 ""로 이스케이프
                if title_val:
                    title_escaped = title_val.replace('"', '""')
                    title_quoted = f'"{title_escaped}"'
                else:
                    title_quoted = '""'
                
                # CSV 라인 작성 (날짜, 구분, 제목(따옴표 포함), URL)
                f.write(f'{date_val},{category_val},{title_quoted},{url_val}\n')
        
        print(f"\n✅ CSV 저장 완료: {filepath}")
        print(f"   총 {len(result_df)}건의 기사 저장")
        
        return filepath
    
    def process(self, keyword, start_date_str, end_date_str):
        """
        전체 프로세스 실행
        
        Args:
            keyword: 검색 키워드
            start_date_str: 시작 날짜 (YYYYMMDD 형식)
            end_date_str: 종료 날짜 (YYYYMMDD 형식)
        """
        print("=" * 60)
        print("중복 기사 제거 및 CSV 변환 시작")
        print("=" * 60)
        print(f"키워드: {keyword}")
        if start_date_str or end_date_str:
            date_range = ""
            if start_date_str:
                date_range += f"{start_date_str}"
            if start_date_str and end_date_str:
                date_range += " ~ "
            if end_date_str:
                date_range += f"{end_date_str}"
            print(f"날짜 범위: {date_range}")
        print("=" * 60)
        print()
        
        # 1. 엑셀 파일 로드
        print("1단계: 엑셀 파일 로드")
        df = self.load_excel_files(keyword, start_date_str, end_date_str)
        
        if df is None or df.empty:
            print("❌ 처리할 데이터가 없습니다.")
            return
        
        print()
        
        # 2. 실패 행 제거 (메모리에서만)
        print("2단계: 실패 행 제거 (메모리에서만)")
        df_cleaned = self.remove_failed_articles(df)
        print(f"  → 남은 기사: {len(df_cleaned)}건")
        print()
        
        # 3. 중복 제거
        print("3단계: 중복 기사 제거 (TF-IDF + 코사인 유사도)")
        df_deduped = self.remove_duplicates_by_similarity(df_cleaned)
        print()
        
        # 4. CSV 저장
        print("4단계: CSV 변환 및 저장")
        output_file = self.save_to_csv(df_deduped, keyword, start_date_str, end_date_str)
        
        print()
        print("=" * 60)
        print("처리 완료!")
        print("=" * 60)
        print(f"원본: {len(df)}건")
        print(f"실패 제거 후: {len(df_cleaned)}건")
        print(f"중복 제거 후: {len(df_deduped)}건")
        print(f"최종 저장: {len(df_deduped)}건")
        print("=" * 60)


if __name__ == "__main__":
    # 명령줄 인자로부터 키워드 및 날짜 범위 받기
    if len(sys.argv) < 2:
        print("사용법: python remove_duplicate_articles_from_excel.py <keyword> [start_date] [end_date]")
        print("예시: python remove_duplicate_articles_from_excel.py 한국전력")
        print("예시: python remove_duplicate_articles_from_excel.py 한국전력 20251101 20251130")
        sys.exit(1)
    
    keyword = sys.argv[1]
    start_date_str = None
    end_date_str = None
    
    # 날짜 범위 인자 처리
    if len(sys.argv) >= 3:
        start_date_str = sys.argv[2]
        # 날짜 형식 검증 (YYYYMMDD)
        if len(start_date_str) != 8 or not start_date_str.isdigit():
            print(f"❌ 오류: 시작 날짜 형식이 올바르지 않습니다. (YYYYMMDD 형식 필요)")
            print(f"   입력된 값: {start_date_str}")
            sys.exit(1)
    
    if len(sys.argv) >= 4:
        end_date_str = sys.argv[3]
        # 날짜 형식 검증 (YYYYMMDD)
        if len(end_date_str) != 8 or not end_date_str.isdigit():
            print(f"❌ 오류: 종료 날짜 형식이 올바르지 않습니다. (YYYYMMDD 형식 필요)")
            print(f"   입력된 값: {end_date_str}")
            sys.exit(1)
    
    # 시작일이 종료일보다 늦으면 오류
    if start_date_str and end_date_str and start_date_str > end_date_str:
        print(f"❌ 오류: 시작일이 종료일보다 늦습니다.")
        print(f"   시작일: {start_date_str}")
        print(f"   종료일: {end_date_str}")
        sys.exit(1)
    
    remover = DuplicateRemover()
    remover.process(keyword, start_date_str, end_date_str)

