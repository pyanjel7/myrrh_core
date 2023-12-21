from myrrh.core.services.system import ExecutionFailureCauseRVal

from myrrh.framework.mpython.msys import AbcSys

__mlib__ = "Sys"


class Sys(AbcSys):
    __executable: bytes | None = None
    _abiflags = ""

    @property
    def _executable(self):
        if not self.__executable:
            for exe in (
                b"python3.7",
                b"python3.6",
                b"python3.5",
                b"python3.4",
                b"python3",
                b"python",
            ):
                self.__executable, err, rval = self.myrrh_os.cmdb(b"%(which)s %(exe)s", exe=exe)
                if rval == 0:
                    break
            else:
                ExecutionFailureCauseRVal(self, err, rval, 0).check()
        return self.__executable

    @property
    def _platform(self):
        return "linux"

    @property
    def abiflags(self):
        return self._get_sys_attr("abiflags")
