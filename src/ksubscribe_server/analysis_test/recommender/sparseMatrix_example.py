import numpy as np
import time 
from scipy.sparse import csr_matrix, csc_matrix 
from sklearn.neighbors import NearestNeighbors

# Sparse Matrix로 처리하면 메모리를 절감되는 시간을 훨씬 오래 걸리네 #############
num_users = 100000  # 총 사용자 수
num_keywords = 500  # 키워드 수 (사용자가 구독 가능한 키워드 종류)
user_keyword_matrix = np.random.randint(2, size=(num_users, num_keywords))


sparse_matrix = csr_matrix(user_keyword_matrix)

start_time = time.time()

# NearestNeighbors 모델 설정 및 학습
# metric='cosine'을 사용하면 코사인 유사도 기반의 이웃 탐색 가능
model = NearestNeighbors(metric='cosine', algorithm='brute')
model.fit(sparse_matrix)

# 특정 데이터 포인트의 인덱스를 찾기 위해 사용할 벡터
query_index = 0  # 첫 번째 행(사용자)
query_vector = sparse_matrix[query_index]

# 가장 가까운 이웃 찾기 (자기 자신 제외)
distances, indices = model.kneighbors(query_vector, n_neighbors=3)

end_time = time.time()
execution_time = end_time - start_time
# 결과 출력
print("유사한 사용자 인덱스:", indices[0])
print("각 사용자와의 거리(유사도):", distances[0])
print(f"수행 시간: {execution_time:.5f}초")

