
import csv
import os
from datetime import datetime, timedelta, timezone
from typing import List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from transformers import pipeline
from collections import Counter
import numpy as np
import pandas as pd
from konlpy.tag import Okt
from itertools import combinations
from transformers import LongformerForSequenceClassification, LongformerTokenizer
import torch
from transformers import pipeline, AutoTokenizer

from ksubscribe_share.db.dbmodelV2.contentsVO import ContentsVO
from ksubscribe_share.db.mongoManager import MongoManager
from ksubscribe_share.logger import Logger
from ksubscribe_share.db.dbmodelV2.contentsVO import SentimentInfo

class ContentsScrapingResult:
    
    '''
        평판 분석 신뢰도 평가를 위한 클래스 - 테스트 코드이므로 삭제해야 됨. 
    '''    

    mongoManager = MongoManager()
    
    logger = Logger()
    docker_scraping_logger = logger.setup_logger(logger.docker_scraping_logger_name)    
    okt = Okt()

    def __init__(self):
        # 감성 분석 모델 로드
        self.sentiment_pipeline = pipeline("sentiment-analysis", model="distilbert/distilbert-base-uncased-finetuned-sst-2-english")
        self.tokenizer = AutoTokenizer.from_pretrained("distilbert/distilbert-base-uncased-finetuned-sst-2-english")
    
    def summary_result(self):
        
        # CSV 파일 경로 및 이름 설정
        csv_file = f"docker_scraping/results/summary_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        # CSV 파일 헤더 정의
        headers = [
            "index", "orgId", "cateId", "rawCollectYN", "contentsRaw", "metaSucYN",
            "keywords_string", "predKeywords_string", "shortSummary_string", "longSummary_string"
        ]
        
        try: 
            # 파일이 존재하지 않으면 헤더를 추가
            write_header = not os.path.exists(csv_file)
            
            with open(csv_file, mode="a", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)
                
                # 헤더 추가 (처음 작성 시에만)
                if write_header:
                    writer.writerow(headers)
                
                            
                collection = self.mongoManager.getCollection("contents") 
                
                now = datetime.now() # 실행한 시간을 기점으로 24 시간 전까지만                
                start_of_day = now - timedelta(days=30)                
                query = {
                    "pubDt": {
                        "$gte": start_of_day,
                        "$lte": now
                    },
                    "rawCollectSucYN": "Y",
                    "metaSucYN": "Y"
                    
                }                
                # 조건을 만족하는 여러 문서 반환
                # 수집한 콘텐츠 가져오기            
                cursor = list(collection.find(query).sort("pubDt", -1).limit(100))
                contentsVO_list : List[ContentsVO] = [ContentsVO.from_mongo(item) for item in cursor] 
                
                for index, vo in enumerate(contentsVO_list): 
                    
                    orgId = vo.contentsOrgId
                    cateId = vo.categoryId
                    rawCollectYN = vo.rawCollectSucYN
                    contentsRaw = "" if vo.contentsRaw is None else vo.contentsRaw.contents
                    
                    metaSucYN = vo.metaSucYN
                    
                    keywords_string = None
                    predKeywords_string = None
                    shortSummary_string = None
                    longSummary_string = None
                    sentiments_string = None
                    
                    if vo.contentsMeta is not None:   
                                        
                        if vo.contentsMeta.keywords:
                            keywords_string = ",".join(vo.contentsMeta.keywords)
                        else:
                            keywords_string = ""  # 기본값

                        if vo.contentsMeta.predKeywords:
                            predKeywords_string = ",".join(vo.contentsMeta.predKeywords)
                        else:
                            predKeywords_string = ""  # 기본값                    
                            
                        shortSummary_string =  vo.contentsMeta.shortSummary
                        longSummary_string =  vo.contentsMeta.longSummary
                    
                    # 로그 데이터 추가
                    writer.writerow([
                        index, orgId, cateId, rawCollectYN, contentsRaw, metaSucYN,
                        keywords_string, predKeywords_string, shortSummary_string,
                        longSummary_string
                    ])
                
                    self.docker_scraping_logger.info(f'{index}')

        except Exception as e:
            print(f"An error occurred: {e}")
            return None
    
    
    def word_matching_simularity(self, article_text:str, positive_keywords:List[str], negative_keywords:List[str]):
        """기사 원문에서 긍정적인 단어와 부정적인 단어의 출현 빈도를 계산하여, 기존 분석 결과와 비교하는 방식
           긍정 키워드와 부정 키워드의 비율이 기존 분석과 얼마나 유사한지를 확인
        """

        # 기사 원문
        article_text = """산업통상자원부는 업계를 대상으로 디지털 통상협정에 대해 소개하는 자리를 마련했다고 2일 밝혔다.
        산업부는 지난 27일 서울 한국무역협회에서 '디지털 통상협정 설명회'를 개최하고, 한국이 체결한 디지털 통상협정에 대한 업계의 이해를 제고하기 위해 디지털 통상협정의 의의 및 주요 내용, 다양한 디지털 지원 플랫폼 활용 방안을 설명했다.
        """

        # 감성 키워드
        positive_keywords = ["도움", "지원", "제공", "기회", "참여", "활용", "효과", "기대", "설명", "발표"]
        negative_keywords = ["문제", "비판", "부정", "우려", "미흡", "지연", "장애", "한계"]

        # 기사에서 키워드 출현 횟수 계산
        word_counts = Counter(article_text.split())

        positive_count = sum(word_counts[word] for word in positive_keywords if word in word_counts)
        negative_count = sum(word_counts[word] for word in negative_keywords if word in word_counts)
        total_words = len(article_text.split())

        # 실제 긍정/부정 비율 계산
        actual_positive_ratio = positive_count / total_words
        actual_negative_ratio = negative_count / total_words
        actual_neutral_ratio = 1 - (actual_positive_ratio + actual_negative_ratio)

        # 기존 분석 결과와 비교하여 신뢰도 평가
        print(f"실제 긍정 비율: {actual_positive_ratio:.3f}, 실제 부정 비율: {actual_negative_ratio:.3f}")
        
    def sentiment_dataset_analyze(self):
        """ 평균적 감성 분포 데이터셋을 이용하여 산업 관련 기사에서 일반적으로 나타나는 감성 분포와 비교.
            과거 유사한 기사 100개의 긍정/부정 비율과 현재 기사의 감성 분포 차이를 분석.
        """

        # 과거 유사한 산업 기사에서 나타난 감성 분포
        historical_positive_ratios = np.random.normal(0.5, 0.1, 100)  # 평균 0.5, 표준편차 0.1
        historical_negative_ratios = np.random.normal(0.1, 0.05, 100)

        # 현재 기사 분석 결과
        current_positive_ratio = 0.8
        current_negative_ratio = 0.1

        # 현재 분석 결과가 평균과 얼마나 차이나는지 계산
        positive_diff = abs(np.mean(historical_positive_ratios) - current_positive_ratio)
        negative_diff = abs(np.mean(historical_negative_ratios) - current_negative_ratio)

        # 신뢰도 평가
        if positive_diff < 0.1 and negative_diff < 0.05:
            print("신뢰도 높음 ✅")
        elif positive_diff < 0.2 and negative_diff < 0.1:
            print("신뢰도 보통 ⚠️")
        else:
            print("신뢰도 낮음 ❌")
       
       
    def chunk_text(self, text, max_length=512, stride=256):
        """
        긴 문장을 max_length 크기로 나누되, stride 간격으로 겹치게 처리 (슬라이딩 윈도우 방식).
        decode() 이후에도 길이가 512 이하가 되도록 다시 조정.
        """
        tokens = self.tokenizer.encode(text, truncation=False)
        chunks = []

        for i in range(0, len(tokens), stride):
            chunk_tokens = tokens[i:i + max_length]  # 512개 이하로 자르기
            chunk_text = self.tokenizer.decode(chunk_tokens, skip_special_tokens=True)  # 🔥 decode 수행

            # 🔥 decode한 후에도 최종적으로 512자 이하로 제한
            chunk_tokens_rechecked = self.tokenizer.encode(chunk_text, truncation=True, max_length=512)
            decoded_chunk = self.tokenizer.decode(chunk_tokens_rechecked, skip_special_tokens=True)  # 🔥 추가됨

            # 🔥 decode한 후에도 최종적으로 512자 이하로 제한
            if len(decoded_chunk) > 512:
                decoded_chunk = decoded_chunk[:512]  # 문자열을 512자 이하로 잘라서 저장

            chunks.append(decoded_chunk)

            # 마지막 청크가 전체 문장의 끝을 포함하면 중단
            if i + max_length >= len(tokens):
                break

        return chunks  # 🔥 이제 모든 chunk는 512자 이하

           
    # def hugging_face_sentiment_analysis_model(self, article_text:str): 
    #     """Hugging Face의 감성 분석 모델(Sentiment Analysis Model)**을 사용하여 전체 기사에 대해 감성 분석을 수행하고 기존 분석 결과와 비교하는 방식입니다.
            
    #     Returns:
    #         _type_: _description_
    #     """    

    #     # 감성 분석 모델 로드
    #     #sentiment_pipeline = pipeline("sentiment-analysis") 
    #     #sentiment_pipeline = pipeline("sentiment-analysis", model="allenai/longformer-base-4096")
    #     sentiment_pipeline = pipeline("sentiment-analysis", model="distilbert/distilbert-base-uncased-finetuned-sst-2-english")
        

    #     # 기사 감성 분석 수행
    #     sentiment_results = sentiment_pipeline(article_text)
    #     # 레이블 변환 (LABEL_0 -> NEGATIVE, LABEL_1 -> POSITIVE)
    #     label_map = {"LABEL_0": "NEGATIVE", "LABEL_1": "POSITIVE"}
        
    #     # 변환 적용
    #     for result in sentiment_results:
    #         result["label"] = label_map[result["label"]]        
        
    #     # 결과 출력
    #     print(sentiment_results)

    #     return sentiment_results[0]["label"], sentiment_results[0]["score"]
         
    
    def hugging_face_sentiment_analysis_model(self, article_text: str):
        """
        Hugging Face의 감성 분석 모델을 사용하여 전체 기사 감성 분석 수행.
        긴 문장은 청크로 나누어 개별 분석 후 최종 결과를 가중 평균하여 반환.
        """
        # 긴 문장을 max_length 단위로 나누기 (stride 적용)
        text_chunks = self.chunk_text(article_text, max_length=512, stride=256)

        # 레이블 변환 (Hugging Face 모델이 반환하는 레이블을 통일)
        label_map = {"LABEL_0": "NEGATIVE", "LABEL_1": "POSITIVE"}

        # 청크별 감성 분석 결과 저장
        total_score = {"NEGATIVE": 0, "POSITIVE": 0}
        total_length = 0

        for chunk in text_chunks:
            
            encoded_chunk = self.tokenizer.encode(chunk, truncation=True, max_length=512)  # 🔥 다시 확인
            decoded_chunk = self.tokenizer.decode(encoded_chunk, skip_special_tokens=True)  # 🔥 재검증
            
            sentiment_results = self.sentiment_pipeline(decoded_chunk, truncation=True, max_length=512)

            # 개별 청크에 대한 감성 점수 적용
            for result in sentiment_results:
                label = result["label"] #label_map[result["label"]]  # 레이블 변환
                score = result["score"]
                chunk_length = len(decoded_chunk)

                # 가중 평균을 위한 점수 누적 (chunk 길이에 비례하여 가중치 부여)
                total_score[label] += score * chunk_length
                total_length += chunk_length

        # 최종 점수 계산
        if total_length > 0:
            positive_score = total_score["POSITIVE"] / total_length
            negative_score = total_score["NEGATIVE"] / total_length
        else:
            positive_score = negative_score = 0

        # 최종 라벨 결정
        final_label = "POSITIVE" if positive_score > negative_score else "NEGATIVE"
        
        return final_label, positive_score, negative_score


         
    def TF_IDF_simularity(self, article_text:str, positive_summary:str, is_positive:bool):
        """기사 원문과 기존 분석이 반영한 긍정적/부정적 요약 내용 간의 유사도를 비교하여 신뢰도를 검증.
           Term Frequency - Inverse Document Frequency : 텍스트 벡터화를 수행한 후 코사인 유사도를 측정  

        Args:
            article_text (str): _description_
            positive_summary (str): _description_
        """

        # TF-IDF 벡터화
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform([article_text, positive_summary])

        # 코사인 유사도 계산
        similarity_score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2]).flatten()[0]

        # 신뢰도 기준: 유사도가 높을수록 기존 분석 결과가 기사 원문과 일치함
        if is_positive:
            print(f"기사와 긍정 요약 간의 코사인 유사도: {similarity_score:.3f}")
        else :
            print(f"기사와 부정 요약 간의 코사인 유사도: {similarity_score:.3f}")

           
    def load_polarity(self):
        # KOSAC 감성 사전 CSV 파일 로드 (파일 경로 변경 필요)
        polarity_df = pd.read_csv(f"docker_scraping/SNU_KOSAC_lexicon/polarity.csv")

        # 감성 사전을 딕셔너리 형태로 변환 (형태소 -> 감성 점수)
        self.polarity_dict = polarity_df.set_index("ngram")[["NEG", "NEUT", "POS"]].to_dict(orient="index")

        # 예제: '좋다/VA' 단어의 감성 점수 확인
        print(self.polarity_dict.get("가*/JKS", "사전에 없음"))        
        pass                  

    okt_to_polarity = {
        "Noun": "NNG",         # 일반 명사
        "Verb": "VV",          # 동사
        "Adjective": "VA",     # 형용사
        "Josa": "JKS",         # 조사
        "Suffix": "XSN",       # 접미사
        "Modifier": "MM",      # 관형사
        "Determiner": "MD",    # 수식어
        "Alpha": "SL",         # 외래어
        "Foreign": "SW",       # 특수 기호
        "Number": "SN",        # 숫자
        "Punctuation": "SF"    # 문장 부호
    }

    def convert_pos_format(self, word, pos):
        """ Okt 품사 태그를 polarity.csv 형식으로 변환 """
        return f"{word}/{self.okt_to_polarity.get(pos, pos)}"


    def generate_ngrams(self, words, n=3):
        """ 형태소 리스트에서 1~n까지의 n-gram을 생성 """
        ngrams = []
        for size in range(1, n + 1):  # unigram, bigram, trigram 등 생성
            for i in range(len(words) - size + 1):
                ngram = ";".join(words[i:i + size])  # 형태소를 ;로 연결
                ngrams.append(ngram)
        return ngrams

    
    # 형태소 분석기 로드
    def analyze_sentiment_with_kosac(self, article_text: str):
        """
        KoNLPy를 이용하여 문장에서 형태소 분석 후, KOSAC 감성 사전(`polarity.csv`)을 적용하여 감성 분석 수행 (N-gram 포함)
        """
        #words = [f"{word}/{pos}" for word, pos in self.okt.pos(article_text)]
        words = [self.convert_pos_format(word, pos) for word, pos in self.okt.pos(article_text)]  # 변환 적용

        ngram_list = self.generate_ngrams(words, n=3)  # 최대 3-gram까지 생성

        # 감성 점수 초기화
        total_words = 0
        positive_score = 0
        negative_score = 0
        neutral_score = 0

        # 감성 점수 계산 (N-gram 기반)
        for ngram in ngram_list:
            if ngram in self.polarity_dict:  # 감성 사전에 존재하는 경우
                total_words += 1
                positive_score += self.polarity_dict[ngram]["POS"]
                negative_score += self.polarity_dict[ngram]["NEG"]
                neutral_score += self.polarity_dict[ngram]["NEUT"]

        # 최종 감성 점수 계산 (평균값)
        if total_words > 0:
            positive_ratio = positive_score / total_words
            negative_ratio = negative_score / total_words
            neutral_ratio = neutral_score / total_words
        else:
            positive_ratio = negative_ratio = neutral_ratio = 0.0  # 감성 단어가 없을 경우

        # 감성 판별
        if positive_ratio > negative_ratio:
            sentiment_label = "POSITIVE"
        elif negative_ratio > positive_ratio:
            sentiment_label = "NEGATIVE"
        else:
            sentiment_label = "NEUTRAL"

        return round(positive_ratio, 3), round(negative_ratio, 3), round(neutral_ratio, 3), sentiment_label


    def reputation_result(self):
        
        # CSV 파일 경로 및 이름 설정
        csv_file = f"docker_scraping/results/reputation_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        # CSV 파일 헤더 정의
        headers = [
            "line_num", "sourceOrgId", "title", "contents", "orgId", "orgName", "positiveRatio", "negativeRatio", "neutralRatio", "positiveReason", "negativeReason", "positiveKeywords", "negativeKeywords",
            "hf_label", "hf_positive", "hf_negative", 
            "kosac_positive", "kosac_negative", "kosac_neutral", "kosac_label", "kosac_positive_diff", "kosac_negative_diff", "kosac_neutral_diff", "label_diff"
        ]        

        try: 
            # 파일이 존재하지 않으면 헤더를 추가
            write_header = not os.path.exists(csv_file)
            
            with open(csv_file, mode="a", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)
                
                # 헤더 추가 (처음 작성 시에만)
                if write_header:
                    writer.writerow(headers)
                
                            
                collection = self.mongoManager.getCollection("contents") 
                
                now = datetime.now() # 실행한 시간을 기점으로 24 시간 전까지만                
                start_of_day = now - timedelta(days=30)                
                query = {
                    "pubDt": {
                        "$gte": start_of_day,
                        "$lte": now
                    },
                    "rawCollectSucYN": "Y",
                    "metaSucYN": "Y"
                    
                }                
                # 조건을 만족하는 여러 문서 반환
                # 수집한 콘텐츠 가져오기            
                cursor = list(collection.find(query).sort("pubDt", -1).limit(200))
                
                contentsVO_list : List[ContentsVO] = [ContentsVO.from_mongo(item) for item in cursor] 
                
                line_num = 1
                for index, vo in enumerate(contentsVO_list): 
                    
                    sourceOrgId = vo.contentsOrgId
                    #cateId = vo.categoryId
                    contentsRaw = "" if vo.contentsRaw is None else vo.contentsRaw.contents
                    title = vo.title

                    if vo.contentsMeta is not None and vo.contentsMeta.sentiments is not None:                                           
                        sentiments: List[SentimentInfo] =  vo.contentsMeta.sentiments
                        
                        for index2, sentiment in enumerate(sentiments): 
                            orgId = sentiment.orgId
                            orgName = sentiment.orgName
                            positiveRatio = sentiment.positiveRatio
                            negativeRatio = sentiment.negativeRatio
                            neutralRatio = sentiment.neutralRatio
                            positiveReason = sentiment.positiveReason
                            negativeReason = sentiment.negativeReason
                            positiveKeywords = "/".join(sentiment.positiveKeywords)
                            negativeKeywords = "/".join(sentiment.negativeKeywords)
                            
                            hf_label, hf_positive, hf_negative = self.hugging_face_sentiment_analysis_model(contentsRaw)
                            #positive_simularity = self.TF_IDF_simularity(contentsRaw, positiveReason, True)
                            #negative_simularity = self.TF_IDF_simularity(contentsRaw, negativeReason, False)
                            kosac_positive, kosac_negative, kosac_neutral, kosac_label = self.analyze_sentiment_with_kosac(contentsRaw)         
                            kosac_positive_diff = abs(positiveRatio - (kosac_positive*100) )
                            kosac_negative_diff = abs(negativeRatio - (kosac_negative*100) )
                            kosac_neutral_diff = abs(neutralRatio - (kosac_neutral*100) )
                            if positiveRatio > 65:
                                ollama_label = "POSITIVE"
                            elif neutralRatio > 65: 
                                ollama_label = "NEGATIVE"
                            else: 
                                ollama_label = "NEUTRAL"
                            label_diff = "다름" if ollama_label != kosac_label else "같음"
                            
                            writer.writerow([
                                line_num, sourceOrgId, title, contentsRaw, orgId, orgName, positiveRatio, negativeRatio, neutralRatio, positiveReason, negativeReason, positiveKeywords, negativeKeywords,
                                hf_label, hf_positive, hf_negative, 
                                kosac_positive, kosac_negative, kosac_neutral, kosac_label, kosac_positive_diff, kosac_negative_diff, kosac_neutral_diff, label_diff
                            ])
                            line_num +=1                

        except Exception as e:
            print(f"An error occurred: {e}")
            return None
                      
     
if __name__ == "__main__":
    dontentsScraping = ContentsScrapingResult()
    dontentsScraping.load_polarity()
    dontentsScraping.reputation_result()
    
    #dontentsScraping.summary_result()
    
    pass