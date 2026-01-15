
class ErrorHandler:
    def __init__(self, processor=None):
        self.processor = processor  # 다음 핸들러를 가리킴

    def handle(self, error):
        if self.processor:
            return self.processor.handle(error)
        return "No handler available"
    def set_processor(self, processor):
        self.processor = processor


class OpenAPIErrorHandler(ErrorHandler):
    def handle(self,error):
        if error == 404:
            return "존재하지 않는 검색 api입니다,."
        if error == 500:
            return "시스템 에러."
        if error == 400:
            return "잘못된 요청변수 입니다."
        if error == 401:
            return "인증 실패 에러."
        if error == 405:
            return "허용되지 않은 메서드."
        if error == 429:
            return "오픈 api 호출 허용량 초과." 
        else : 
            return "Unknown 에러"
 

class SeleniumErrorHandler(ErrorHandler):
    def handle(self,error:Exception): 
        return "Selenium 크롤링 실패 에러"