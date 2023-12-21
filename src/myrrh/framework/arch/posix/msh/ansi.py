import os

from myrrh.core.services.system import AbcRuntime


class Ansimap(AbcRuntime):
    CSI = {
        b"H": b"\033[A",
        b"P": b"\033[B",
        b"M": b"\033[C",
        b"K": b"\033[D",
        b"I": b"\033[S",
        b"Q": b"\033[T",
        b"R": b"\033[1P",
        b"S": b"\x7F",
        b"G": b"\033[H",
        b"O": b"\033[F",
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
