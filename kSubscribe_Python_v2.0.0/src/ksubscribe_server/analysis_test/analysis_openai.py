from openai import OpenAI

# 개발을 위해서 소스코드에 api 사용, 나중에 환경변수로 수정해야함
OPENAI_API_KEY = "os.getenv("OPENAI_API_KEY", "")"
pred_keywords = (
    "데이터, 인공지능, 에너지, 전기, 전력, 플랫폼, 반도체, 교육, 의료, 항공, 우주"
)

question = f"""
다음 HTML에서 기사를 추출하고 아래 형식에 맞춰 JSON 객체로 응답해줘. JSON 객체의 구조는 다음과 같아
{{
    "keyword" : [주요 키워드1, 주요 키워드2, 주요 키워드3],
    "predkeywords": "{pred_keywords} 중 가장 유사도가 높은 키워드 순으로 3개를 "[키워드1, 키워드2, 키워드3]" 형태로 만들어줘",
    "short_summary" : "한줄 기사 요약",
    "long_summary" : "세줄 기사 요약",
    "organization" : "위 기사가 대한민국 기관과 관련된 기사이면 기관명을 알려줘 (1개이상 가능), 맥락으로 파악하지 말고 확실한 것만, 리스트 형식으로",
    "sentiment" :  {{
        "positiveRatio": "기사 내용이 앞에서 추출한 기관에 대해 긍정적인 비율 (%), 주석 달지말고 비율만 알려줘",
        "negativeRatio": "기사 내용이 앞에서 추출한 기관에 대해 부정적인 비율 (%), 주석 달지말고 비율만 알려줘",
        "reason": "긍정과 부정 비율 판단 근거",
    }}
}}
"""


class analysis:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        pass

    def analysis(self, content):
        # totalTimeStart = time.time()

        try:
            completion = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": question},
                    {
                        "role": "user",
                        "content": f"{content}",
                    },
                ],
            )
            return {"success": True, "data": completion.choices[0].message.content}

        except Exception as e:
            msg = f"{e.status_code} : {e.type} - {e.code}"
            return {"success": False, "data": msg}

    def analysis_org(self, content):
        # totalTimeStart = time.time()
        completion = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """다음 기사를 분석하고 아래 형식에 맞춰 JSON 객체로 응답해줘. JSON 객체의 구조는 다음과 같아
                                {
                                "keyword" : [기사의 주체1, 기사의 주체2, 기사의 주체3],
                                "predKeyword" : "",
                                "keyword_reason" : "각 키워드 추출한 이유",
                                "sentiment" : {
                                    "positive_ratio": "기사 내용이 기사 주체에 대해 긍정적인 비율 (%)",
                                    "negative_ratio": "기사 내용이 기사 주체에 대해 부정적인 비율 (%)",
                                },
                                "sentiment_reason" : "긍정적 부정적으로 이유",
                                },
                                "short_summary" : "세줄 이내 기사 요약",
                                },
                                "long_summary" : "세줄 이상 기사 요약",
                                }
                                """,
                },
                {
                    "role": "user",
                    "content": f"{content}",
                },
            ],
        )
        return completion.choices[0].message.content


if __name__ == "__main__":
    pass
