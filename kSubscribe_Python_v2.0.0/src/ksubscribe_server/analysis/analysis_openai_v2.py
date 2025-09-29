from openai import OpenAI
import traceback
from datetime import datetime
import logging 
import ksubscribe_share.config as Conf

# 개발을 위해서 소스코드에 api 사용, 나중에 환경변수로 수정해야함
#OPENAI_API_KEY = "os.getenv("OPENAI_API_KEY", "")"

class analysisV2:
  #여러기관이 나왔을 경우에는 리스트로 반환해",
    # 기관 순서에 맞게 리스트 형식으로 반환해줘
    question = f"""
    다음 HTML에서 기사를 추출하고 아래 형식에 맞춰 JSON 객체로 응답해줘. JSON 객체의 구조는 다음과 같아
    {{
        "keyword" : [주요 키워드1, 주요 키워드2, 주요 키워드3],
        "predkeywords":  [pred_keywords_from_db] 중 가장 유사도가 높은 키워드 순으로 3개만, "{{"키워드1": "유사도점수", "키워드2": "유사도점수", "키워드3": "유사도점수"}}" 형태로 만들어줘",
        "short_summary" : "한줄 기사 요약",
        "long_summary" : "세줄 기사 요약",
        "sentiments" :  {{
            "organization" : "위 기사가 [org_name_list_from_db] 기관 중 관련된 기사이면 가장 유사도가 높은 기관 순으로 기관명을 알려줘. 리스트에 있는 기관명과 동일한 것만 찾아. 리스트 형식으로 반환해줘",
            "positiveRatio": "기사 내용이 기관에 대한 긍정적인 비율 (%), 주석 달지말고 비율만 알려줘. organization의 개수와 동일한 크기를 가진 리스트 형식으로 반환해줘, %없이 출력해 ",
            "negativeRatio": "기사 내용이 기관에 대한 부정적인 비율 (%), 주석 달지말고 비율만 알려줘.  organization의 개수와 동일한 크기를 가진 리스트 형식으로 반환해줘, %없이 출력해 ",
            "neutralRatio": "기사 내용이 기관에 대한 중립적인 비율 (%), 주석 달지말고 비율만 알려줘.  organization의 개수와 동일한 크기를 가진 리스트 형식으로 반환해줘, %없이 출력해 ",
            "reason": "긍정과 부정 비율 판단 근거.  organization의 개수와 동일한 크기를 가진 리스트 형식으로 반환해줘",
        }}
    }} 
    """       
    
    def __init__(self):
        self.client = OpenAI(api_key=Conf.OPENAI_API_KEY)
        pass

    def analysis(self, content, pred_keyword_list, org_name_list, mycontents_logger:logging.Logger = None): 
        new_question = self.question.replace("pred_keywords_from_db", pred_keyword_list).replace("org_name_list_from_db", org_name_list)
        now = datetime.now()
        try:
            completion = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": new_question},
                    {
                        "role": "user",
                        "content": f"{content}",
                    },
                ],
            )
            analysis_data = completion.choices[0].message.content
            #analysis_data logging
            mycontents_logger and mycontents_logger.debug(analysis_data)
            return True, {"success": True, "data": analysis_data, "datetime" : now}

        except Exception as e:
            #trackback logging
            tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            mycontents_logger and mycontents_logger.error(f"Exception occurred: {e}, Args: {e.args}, Traceback: {tb_str}")

            error_data = f"Exception : {e}, Args: {e.args} "
            return False, {"success": False, "data": None , "datetime" : now, "error_data" : error_data}
 
if __name__ == "__main__": 

    pass
