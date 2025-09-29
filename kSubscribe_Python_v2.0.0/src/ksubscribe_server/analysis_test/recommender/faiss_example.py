import faiss
import numpy as np
import time 

# 사용자 수와 키워드 수 정의
num_users = 10000000  # 사용자 수
num_keywords = 500   # 키워드 수 

# # 사용자-키워드 밀집 행렬 생성 (랜덤 데이터 사용)
# # 실제 사용 시 사용자별 구독 키워드를 기반으로 데이터 생성 필요
# user_keyword_matrix = np.random.randint(2, size=(num_users, num_keywords), dtype=bool)
# # 파일로 저장
# np.save("user_keyword_matrix_bool.npy", user_keyword_matrix)

# start_time = time.time()

# # Faiss 인덱스 생성 (L2 거리 기반, ANN을 위한 IVF 인덱스)
# d = num_keywords  # 데이터 차원
# nlist = 1000      # 클러스터 수 (효율성과 정확성의 트레이드오프)
# quantizer = faiss.IndexFlatL2(d)  # 인덱싱에 사용할 기본 인덱스
# index = faiss.IndexIVFFlat(quantizer, d, nlist, faiss.METRIC_L2)

# # 인덱스 트레이닝 (필수)
# index.train(user_keyword_matrix)
# index.add(user_keyword_matrix)  # 데이터 추가

# end_time = time.time() 
# execution_time = end_time - start_time
# print(f"학습 시간: {execution_time:.5f}초")

# # 인덱스, 사용자/키워드 매트릭스를 파일로 저장
# np.save("user_keyword_matrix_bool.npy", user_keyword_matrix)
# faiss.write_index(index, "faiss_index.ivf")

# 인덱스, 사용자/키워드 매트릭스를 파일에서 로드
# loaded_index = faiss.read_index("faiss_index.ivf")
# loaded_matrix = np.load("user_keyword_matrix_bool.npy")

start_time = time.time()

# A 사용자의 벡터 설정 (예시로 첫 번째 사용자)
A_user_index = 0
query_vector = user_keyword_matrix[A_user_index:A_user_index + 1]  # A 사용자의 벡터

# 검색할 클러스터 수 설정 (정확도와 성능의 트레이드오프)
index.nprobe = 10

# ANN 탐색 수행 (가장 유사한 5명의 사용자 찾기)
distances, indices = index.search(query_vector, k=5)

end_time = time.time() 
execution_time = end_time - start_time
print(f"수행 시간: {execution_time:.5f}초")
# 결과 출력
print("0 사용자와 유사한 사용자 인덱스:", indices[0])
print("각 사용자와의 거리:", distances[0])


start_time = time.time()

# A 사용자의 벡터 설정 (예시로 첫 번째 사용자)
A_user_index = 1
query_vector = user_keyword_matrix[A_user_index:A_user_index + 1]  # A 사용자의 벡터

# 검색할 클러스터 수 설정 (정확도와 성능의 트레이드오프)
index.nprobe = 10

# ANN 탐색 수행 (가장 유사한 5명의 사용자 찾기)
distances, indices = index.search(query_vector, k=5)

end_time = time.time() 
execution_time = end_time - start_time
print(f"수행 시간: {execution_time:.5f}초")
# 결과 출력
print("1 사용자와 유사한 사용자 인덱스:", indices[0])
print("각 사용자와의 거리:", distances[0])


start_time = time.time()

# A 사용자의 벡터 설정 (예시로 첫 번째 사용자)
A_user_index = 2
query_vector = user_keyword_matrix[A_user_index:A_user_index + 1]  # A 사용자의 벡터

# 검색할 클러스터 수 설정 (정확도와 성능의 트레이드오프)
index.nprobe = 10

# ANN 탐색 수행 (가장 유사한 5명의 사용자 찾기)
distances, indices = index.search(query_vector, k=5)

end_time = time.time() 
execution_time = end_time - start_time
print(f"수행 시간: {execution_time:.5f}초")
# 결과 출력
print("2 사용자와 유사한 사용자 인덱스:", indices[0])
print("각 사용자와의 거리:", distances[0])


