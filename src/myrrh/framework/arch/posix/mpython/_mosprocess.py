from myrrh.framework.mpython._mosprocess import AbcOsProcess

__mlib__ = "OsProcess"


class OsProcess(AbcOsProcess):
    SIGKILL = 9
    WNOHANG = 1

    def WTERMSIG(self, status: int) -> int:
        return status & 0x7F

    def WIFSTOPPED(self, status: int) -> bool:
        return (status & 0xFF) == 0x7F

    def WSTOPSIG(self, status: int) -> int:
        return (status & 0xFF00) >> 8
