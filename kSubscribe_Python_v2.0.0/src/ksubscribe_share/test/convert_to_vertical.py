import csv

# CSV 파일 경로
csv_file_path = "/home/themiraclesoft/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src/ksubscribe_share/test/mycontents.weekly_stats_24-30.csv"
output_csv_path = "/home/themiraclesoft/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src/ksubscribe_share/test/mycontents.weekly_stats_24-30_vertical.csv"

# 기존 CSV 파일 읽기
with open(csv_file_path, 'r', encoding='utf-8-sig') as csvfile:
    reader = csv.DictReader(csvfile)
    
    # 첫 번째 행만 읽기 (데이터가 하나만 있다고 가정)
    row = next(reader, None)
    
    if row:
        # 세로 형식으로 변환
        with open(output_csv_path, 'w', newline='', encoding='utf-8-sig') as outfile:
            writer = csv.writer(outfile)
            
            # 헤더 작성
            writer.writerow(['field', 'value'])
            
            # 각 필드를 세로로 변환
            for field, value in row.items():
                writer.writerow([field, value])
        
        print(f"세로 형식 CSV 파일이 생성되었습니다: {output_csv_path}")
        print(f"총 {len(row)}개 필드가 변환되었습니다.")
    else:
        print("데이터가 없습니다.")