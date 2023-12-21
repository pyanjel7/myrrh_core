from myrrh.core.services.system import ExecutionFailureCauseRVal

from myrrh.framework.mpython.msys import AbcSys

__mlib__ = "Sys"


class Sys(AbcSys):
    __executable: bytes | None = None
    _abiflags = ""

    @property
    def _executable(self):
        rval = 1
        err = "python unavailable on android system"
        ExecutionFailureCauseRVal(self, err, rval, 0).check()

    @property
    def _platform(self):
        return "android"

    @property
    def abiflags(self):
        return self._get_sys_attr("abiflags")

    @property
    def _maxsize(self):
        return self.myrrh_os.fs.MAX_FILE_SIZE
