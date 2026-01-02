"""
엑셀 파일에 기사 본문(content) 추가 스크립트
- trafilaura 라이브러리를 사용하여 각 기사의 URL에서 본문 추출
- 실패한 기사는 나중에 재시도 (최대 3번, 30초 간격)
"""
import pandas as pd
import os
import time
import sys
from pathlib import Path
import glob

# trafilaura 라이브러리 import
try:
    from docker_scraping.ai_scraping.trafilaura import TrafilauraScraper
except ImportError:
    # 경로 문제 시 직접 import
    import sys
    sys.path.append('/app')
    try:
        from docker_scraping.ai_scraping.trafilaura import TrafilauraScraper
    except ImportError as e:
        print(f"❌ TrafilauraScraper import 실패: {e}")
        print("   경로 확인이 필요합니다.")
        raise


class ArticleContentCollector:
    def __init__(self):
        print("  → TrafilauraScraper 초기화 중...")
        try:
            self.trafilaura_scraper = TrafilauraScraper()
            print("  → TrafilauraScraper 초기화 완료")
        except Exception as e:
            print(f"  ❌ TrafilauraScraper 초기화 실패: {e}")
            raise
        
        self.output_dir = "/app/ksubscribe_share/test/news_scarppings"
        print(f"  → 출력 디렉토리: {self.output_dir}")
        
        # 디렉토리 존재 확인
        if not os.path.exists(self.output_dir):
            print(f"  ⚠️  출력 디렉토리가 존재하지 않습니다: {self.output_dir}")
            print(f"  → 디렉토리 생성 시도...")
            os.makedirs(self.output_dir, exist_ok=True)
            print(f"  → 디렉토리 생성 완료")
        
    def check_content_column_exists(self, df):
        """
        contents 또는 description 컬럼이 존재하고 null이 아닌지 확인
        
        Returns:
            tuple: (컬럼 존재 여부, 모든 행에 데이터가 있는지 여부)
        """
        # contents 또는 description 컬럼 확인
        has_content_col = 'content' in df.columns or 'contents' in df.columns or 'description' in df.columns
        
        if not has_content_col:
            return False, False
        
        # 컬럼 이름 확인
        content_col = None
        if 'content' in df.columns:
            content_col = 'content'
        elif 'contents' in df.columns:
            content_col = 'contents'
        elif 'description' in df.columns:
            content_col = 'description'
        
        if content_col is None:
            return False, False
        
        # null 값이 아닌 행이 있는지 확인
        has_data = df[content_col].notna().any()
        
        # 모든 행에 데이터가 있는지 확인
        all_have_data = df[content_col].notna().all()
        
        return True, all_have_data
    
    def extract_content_from_url(self, url, retry_count=0, max_retries=3):
        """
        URL에서 기사 본문 추출
        
        Args:
            url: 기사 URL
            retry_count: 현재 재시도 횟수
            max_retries: 최대 재시도 횟수
        
        Returns:
            tuple: (성공 여부, 본문 내용, 실패 원인)
        """
        try:
            is_success, title, text = self.trafilaura_scraper.get_newbody(url)
            
            if is_success and text and text.strip():
                return True, text, None
            else:
                return False, None, "본문 추출 실패"
                
        except Exception as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                return False, None, "타임아웃"
            elif "404" in error_msg or "not found" in error_msg.lower():
                return False, None, "페이지 없음 (404)"
            elif "403" in error_msg or "forbidden" in error_msg.lower():
                return False, None, "접근 거부 (403)"
            else:
                return False, None, f"오류: {error_msg[:50]}"
    
    def process_excel_file(self, file_path, keyword):
        """
        엑셀 파일 처리: 기사 본문 수집 및 추가
        
        Args:
            file_path: 엑셀 파일 경로
            keyword: 검색 키워드 (파일명에서 추출)
        
        Returns:
            tuple: (처리 여부, 성공 개수, 실패 개수, 스킵 여부)
        """
        print(f"\n{'='*60}")
        print(f"파일 처리: {os.path.basename(file_path)}")
        print(f"{'='*60}")
        
        try:
            # 엑셀 파일 읽기
            df = pd.read_excel(file_path, engine='openpyxl')
            
            if df.empty:
                print("  → 파일이 비어있습니다. 스킵합니다.")
                return False, 0, 0, True
            
            # 컬럼 존재 여부 및 데이터 확인
            has_col, all_have_data = self.check_content_column_exists(df)
            
            if has_col and all_have_data:
                print("  → content 컬럼이 이미 존재하고 모든 행에 데이터가 있습니다. 스킵합니다.")
                return False, 0, 0, True
            
            # content 컬럼이 없으면 생성
            if 'content' not in df.columns:
                df['content'] = None
            
            # link 컬럼 확인
            if 'link' not in df.columns:
                print("  → 'link' 컬럼이 없습니다. 스킵합니다.")
                return False, 0, 0, True
            
            total_articles = len(df)
            success_count = 0
            failed_urls = []  # (index, url) 튜플 리스트
            
            print(f"  → 총 {total_articles}개 기사 처리 시작...")
            
            # 첫 번째 패스: 모든 기사 시도
            for idx, row in df.iterrows():
                url = row.get('link', '')
                
                if pd.isna(url) or not url or url.strip() == '':
                    df.at[idx, 'content'] = 'URL 없음'
                    failed_urls.append((idx, url))
                    continue
                
                # 이미 content가 있으면 스킵
                if pd.notna(df.at[idx, 'content']) and df.at[idx, 'content'] != '':
                    success_count += 1
                    continue
                
                print(f"  [{idx+1}/{total_articles}] 수집 중...", end=' ')
                
                is_success, content, error_msg = self.extract_content_from_url(url)
                
                if is_success:
                    df.at[idx, 'content'] = content
                    success_count += 1
                    print(f"✅ 성공")
                else:
                    df.at[idx, 'content'] = '실패'
                    failed_urls.append((idx, url))
                    print(f"❌ 실패 ({error_msg})")
                
                # 진행 상황 출력 (10개마다)
                if (idx + 1) % 10 == 0:
                    print(f"    진행: {idx+1}/{total_articles} (성공: {success_count}, 실패: {len(failed_urls)})")
            
            # 실패한 기사 재시도 (최대 3번)
            if failed_urls:
                print(f"\n  → 실패한 {len(failed_urls)}개 기사 재시도 시작...")
                
                for retry_num in range(1, 4):  # 1, 2, 3
                    if not failed_urls:
                        break
                    
                    print(f"\n  [재시도 {retry_num}/3] {len(failed_urls)}개 기사 재시도 중...")
                    time.sleep(30)  # 30초 대기
                    
                    remaining_failed = []
                    
                    for idx, url in failed_urls:
                        if pd.isna(url) or not url or url.strip() == '':
                            continue
                        
                        print(f"    [{idx+1}] 재시도 중...", end=' ')
                        
                        is_success, content, error_msg = self.extract_content_from_url(url)
                        
                        if is_success:
                            df.at[idx, 'content'] = content
                            success_count += 1
                            print(f"✅ 성공")
                        else:
                            df.at[idx, 'content'] = f'실패 ({error_msg})'
                            remaining_failed.append((idx, url))
                            print(f"❌ 실패 ({error_msg})")
                    
                    failed_urls = remaining_failed
                    
                    if not failed_urls:
                        print(f"  → 모든 기사 수집 완료!")
                        break
            
            # 엑셀 파일 저장
            df.to_excel(file_path, index=False, engine='openpyxl')
            
            failed_count = len(failed_urls)
            print(f"\n  → 처리 완료: 성공 {success_count}개, 실패 {failed_count}개")
            
            return True, success_count, failed_count, False
            
        except Exception as e:
            print(f"  → 파일 처리 오류: {e}")
            return False, 0, 0, False
    
    def extract_date_from_filename(self, filename):
        """
        파일명에서 날짜 추출 (YYYYMMDD 형식)
        
        Args:
            filename: 파일명 (예: naver_news_한국전력_20251101.xlsx)
        
        Returns:
            str: 날짜 문자열 (YYYYMMDD) 또는 None
        """
        import re
        # 파일명에서 8자리 숫자 추출 (YYYYMMDD)
        match = re.search(r'(\d{8})', filename)
        if match:
            return match.group(1)
        return None
    
    def filter_files_by_date_range(self, files, start_date_str=None, end_date_str=None):
        """
        날짜 범위에 해당하는 파일만 필터링
        
        Args:
            files: 파일 경로 리스트
            start_date_str: 시작 날짜 (YYYYMMDD 형식, 예: "20251101")
            end_date_str: 종료 날짜 (YYYYMMDD 형식, 예: "20251130")
        
        Returns:
            list: 필터링된 파일 경로 리스트
        """
        if not start_date_str and not end_date_str:
            return files
        
        filtered_files = []
        
        for file_path in files:
            filename = os.path.basename(file_path)
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
    
    def process_all_files(self, keyword, start_date_str=None, end_date_str=None):
        """
        특정 키워드의 모든 엑셀 파일 처리
        
        Args:
            keyword: 검색 키워드
            start_date_str: 시작 날짜 (YYYYMMDD 형식, 예: "20251101")
            end_date_str: 종료 날짜 (YYYYMMDD 형식, 예: "20251130")
        """
        # 파일 패턴: naver_news_{keyword}_*.xlsx
        pattern = os.path.join(self.output_dir, f"naver_news_{keyword}_*.xlsx")
        excel_files = glob.glob(pattern)
        
        if not excel_files:
            print(f"❌ '{keyword}' 키워드의 엑셀 파일을 찾을 수 없습니다.")
            print(f"   검색 경로: {pattern}")
            return
        
        # 날짜 범위 필터링
        if start_date_str or end_date_str:
            excel_files = self.filter_files_by_date_range(excel_files, start_date_str, end_date_str)
            
            if not excel_files:
                print(f"❌ 지정한 날짜 범위에 해당하는 파일이 없습니다.")
                if start_date_str:
                    print(f"   시작일: {start_date_str}")
                if end_date_str:
                    print(f"   종료일: {end_date_str}")
                return
        
        # 날짜순으로 정렬
        excel_files.sort()
        
        print(f"\n{'='*60}")
        print(f"기사 본문 수집 시작")
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
        print(f"총 {len(excel_files)}개 파일 처리 예정")
        print(f"저장 경로: {self.output_dir}")
        print(f"{'='*60}")
        
        total_success = 0
        total_failed = 0
        processed_count = 0
        skipped_count = 0
        
        for file_path in excel_files:
            is_processed, success, failed, is_skipped = self.process_excel_file(file_path, keyword)
            
            if is_skipped:
                skipped_count += 1
            elif is_processed:
                processed_count += 1
                total_success += success
                total_failed += failed
        
        print(f"\n{'='*60}")
        print(f"전체 처리 완료")
        print(f"{'='*60}")
        print(f"처리된 파일: {processed_count}개")
        print(f"스킵된 파일: {skipped_count}개")
        print(f"총 성공: {total_success}개")
        print(f"총 실패: {total_failed}개")
        print(f"{'='*60}")


if __name__ == "__main__":
    print("=" * 60)
    print("기사 본문 수집 스크립트 시작")
    print("=" * 60)
    
    # 명령줄 인자로부터 키워드 및 날짜 범위 받기
    if len(sys.argv) < 2:
        print("사용법: python collect_article_content_trafilaura.py <keyword> [start_date] [end_date]")
        print("예시: python collect_article_content_trafilaura.py 한국전력")
        print("예시: python collect_article_content_trafilaura.py 한국전력 20251101 20251130")
        sys.exit(1)
    
    keyword = sys.argv[1]
    start_date_str = None
    end_date_str = None
    
    print(f"키워드: {keyword}")
    
    # 날짜 범위 인자 처리
    if len(sys.argv) >= 3:
        start_date_str = sys.argv[2]
        # 날짜 형식 검증 (YYYYMMDD)
        if len(start_date_str) != 8 or not start_date_str.isdigit():
            print(f"❌ 오류: 시작 날짜 형식이 올바르지 않습니다. (YYYYMMDD 형식 필요)")
            print(f"   입력된 값: {start_date_str}")
            sys.exit(1)
        print(f"시작일: {start_date_str}")
    
    if len(sys.argv) >= 4:
        end_date_str = sys.argv[3]
        # 날짜 형식 검증 (YYYYMMDD)
        if len(end_date_str) != 8 or not end_date_str.isdigit():
            print(f"❌ 오류: 종료 날짜 형식이 올바르지 않습니다. (YYYYMMDD 형식 필요)")
            print(f"   입력된 값: {end_date_str}")
            sys.exit(1)
        print(f"종료일: {end_date_str}")
    
    # 시작일이 종료일보다 늦으면 오류
    if start_date_str and end_date_str and start_date_str > end_date_str:
        print(f"❌ 오류: 시작일이 종료일보다 늦습니다.")
        print(f"   시작일: {start_date_str}")
        print(f"   종료일: {end_date_str}")
        sys.exit(1)
    
    print("=" * 60)
    print("초기화 중...")
    
    try:
        collector = ArticleContentCollector()
        print("✅ 초기화 완료")
        print("=" * 60)
        
        collector.process_all_files(keyword, start_date_str, end_date_str)
        
        print("=" * 60)
        print("스크립트 종료")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

