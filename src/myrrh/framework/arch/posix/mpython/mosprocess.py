import posix

from myrrh.framework.mpython._mosprocess import AbcOsProcess

__mlib__ = "OsProcess"


class OsProcess(AbcOsProcess):
    SIGKILL = 9
    WIFSTOPPED = posix.WIFSTOPPED
    WSTOPSIG = posix.WSTOPSIG
    WNOHANG = posix.WNOHANG
