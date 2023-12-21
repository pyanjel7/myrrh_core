from myrrh.core.services.system import AbcRuntime


class Ansimap(AbcRuntime):
    CSI = {"\r": "\r\n"}

    def __init__(self, control, iterator, abortkey=None):
        self.map = self.__posixtowin
        self.__iter = iterator
        self.__abortkey = abortkey
        self.__keys = []

    def __iter__(self):
        return self

    def __next__(self):
        return self.map()

    def __call__(self):
        return self.map()

    def __posixtowin(self):
        if len(self.__keys) == 0:
            k = next(self.__iter)
            self.__keys.extend(self.CSI.get(k, k))

        return self.__keys.pop(0)
