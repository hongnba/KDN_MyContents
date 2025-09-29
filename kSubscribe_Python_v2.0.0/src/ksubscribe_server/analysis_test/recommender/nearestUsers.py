import numpy as np
from sklearn.neighbors import NearestNeighbors
import time
from scipy.sparse import csr_matrix

# 예시 데이터: 각 사용자가 구독한 키워드 벡터 (여기서는 랜덤하게 생성된 벡터)
# 실제 구현에서는 사용자의 키워드 구독 정보로 벡터를 생성해야 함.
num_users = 100000  # 총 사용자 수
num_keywords = 500  # 키워드 수 (사용자가 구독 가능한 키워드 종류)
user_keyword_matrix = np.random.randint(2, size=(num_users, num_keywords), dtype=bool)


# Dense Matrix로 처리 #############################################################
start_time = time.time()

# A 사용자의 인덱스 (특정 사용자의 키워드 구독 벡터)
user_index_A = 0
user_A_vector = user_keyword_matrix[user_index_A].reshape(1, -1)

# Nearest Neighbors 모델 생성 및 학습
# metric='cosine'을 사용하면 코사인 유사도로 유사도 계산이 가능
model = NearestNeighbors(n_neighbors=10, metric='cosine', algorithm='brute')
model.fit(user_keyword_matrix)

# A 사용자와 유사한 사용자 탐색
distances, indices = model.kneighbors(user_A_vector)

end_time = time.time()
execution_time = end_time - start_time
# 결과 출력
print("유사한 사용자 인덱스:", indices[0])
print("각 사용자와의 거리(유사도):", distances[0])
print(f"수행 시간: {execution_time:.5f}초")


