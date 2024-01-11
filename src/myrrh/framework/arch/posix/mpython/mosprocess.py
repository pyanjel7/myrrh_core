from myrrh.framework.mpython._mosprocess import AbcOsProcess

__mlib__ = "OsProcess"


class OsProcess(AbcOsProcess):
    SIGKILL = 9

    @staticmethod
    def WIFSTOPPED(status: int) -> int:
        return ((status & 0xFF) == 0x7F) and 1 or 0

    @staticmethod
    def WSTOPSIG(self, status: int) -> int:
        return (status & 0xFF00) >> 8

    WNOHANG = 1
