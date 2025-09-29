class SendResult:
    def __init__(self, sendType: str, receiver: str, isSuccess: bool, message: dict[str, str], sendIds: list[str]):
        self.sendType = sendType
        self.reciever = receiver
        self.isSuccess = isSuccess
        self.message = message
        self.sendIds = sendIds