import os

from myrrh.core.system import AbcRuntime


class Ansimap(AbcRuntime):
    CSI = {
        "H": "\033[A",
        "P": "\033[B",
        "M": "\033[C",
        "K": "\033[D",
        "I": "\033[S",
        "Q": "\033[T",
        "R": "\033[1P",
        "S": "\x7F",
        "G": "\033[H",
        "O": "\033[F",
    }

    def __init__(self, iterator, abortkey=None):
        self.map = self.__wintoposix if os.name == "nt" else self.__ident
        self.__iter = iterator
        self.__abortkey = abortkey
        self.__keys = []

    def __iter__(self):
        return self

    def __next__(self):
        return self.map()

    def __call__(self):
        return self.map()

    def __ident(self):
        if len(self.__keys) == 0:
            k = next(self.__iter)
            self.__keys.extend(k)

        k = self.__keys.pop(0)

        if k == self.__abortkey:
            raise StopIteration

        return k

    def __wintoposix(self):
        if len(self.__keys) == 0:
            k = next(self.__iter)
            self.__keys.extend(k)

        k = self.__keys.pop(0)
        ordk = ord(k)
        if ordk == 224:
            k = next(self.__iter)
            self.__keys += list(Ansimap.CSI.get(k, "\0"))
            k = chr(self.__keys.pop(0)).encode()

        if ordk == 0:
            next(self.__iter)
            k = ""

        if k == "\r":
            k = "\n"
        if k == self.__abortkey:
            raise StopIteration

        return k
