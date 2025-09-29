class Singleton(object):
    def __new__(cls):
        if not hasattr(cls, "instance"):
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self) -> bool:
        cls = type(self)
        if not hasattr(cls, "is_initialized"):
            cls.is_initialized = True
            return False
        return True


if __name__ == "__main__":

    class Test(Singleton):
        def __init__(self):
            if super().__init__():
                return
            print("초기화")

        def test(self):
            print("Test")

    t = Test()
    t = Test()
    t = Test()
    t = Test()
    t = Test()
    t = Test()
