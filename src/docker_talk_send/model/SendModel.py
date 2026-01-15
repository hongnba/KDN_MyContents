from datetime import date


class SendModel:
    def __init__(
        self, 
        mber_telno: str = None,
        send_type: str = None,
        reserved_send_yn: str = None,
        reserved_dt: date = None,
        template_msg: str = None,
        template_code: str = None,
        img_url: str = None,
        button_url: str = None,
    ):
        self.mber_telno = mber_telno
        self.send_type = send_type
        self.reserved_send_yn = reserved_send_yn
        self.reserved_dt = reserved_dt
        self.template_msg = template_msg
        self.template_code = template_code
        self.img_url = img_url
        self.button_url = button_url