import openai
import ksubscribe_share.config as Conf

class GPTSummarize:

    # GPT-4o API 설정
    openai.api_key = Conf.OPENAI_API_KEY

    def summarize_chunk(chunk):
        """
        각 청크를 GPT-4o API에 보내 요약
        """
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "주어진 텍스트를 간결하고 핵심적으로 요약해주세요."},
                    {"role": "user", "content": chunk},
                ],
            )
            return response["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"Error during summarization: {e}")
            return None
        
        