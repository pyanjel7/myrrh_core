from myrrh.framework.mpython._mosprocess import AbcOsProcess

__mlib__ = "OsProcess"


class OsProcess(AbcOsProcess):
    CTRL_BREAK_EVENT = 1
    CTRL_C_EVENT = 0
