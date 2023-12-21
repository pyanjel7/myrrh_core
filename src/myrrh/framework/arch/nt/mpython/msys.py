from collections import namedtuple

from myrrh.core.services.system import ExecutionFailureCauseRVal

from myrrh.framework.mpython.msys import AbcSys

__mlib__ = "Sys"


class Sys(AbcSys):
    __executable: bytes | None = None

    __all__ = AbcSys.__all__ + [
        "getwindowsversion",
    ]

    def _enablelegacywindowsfsencoding(self):
        self.myrrh_os.fsencoding = "mbcs"

    @property
    def _platform(self):
        return "win32"

    @property
    def _executable(self):
        if self.__executable is None:
            self.__executable, err, rval = self.myrrh_os.cmdb(b"%(where)s python")
            self.__executable = self.__executable.split(b"\r\n")[0] if self.__executable else self.__executable
            ExecutionFailureCauseRVal(self, err, rval, 0).check()

        return self.__executable

    def getwindowsversion(self):
        major, minor, build = (int(v) for v in self.myrrh_os._wininfo["Version"].split("."))
        version = namedtuple(
            "sys_getwindowsversion",
            "major minor build platform service_pack service_pack_major service_pack_minor suite_mast product_type platform_version",
        )

        return version(
            major,
            minor,
            build,
            2,
            self.myrrh_os._wininfo["CSDVersion"],
            self.myrrh_os._wininfo["ServicePackMajorVersion"],
            self.myrrh_os._wininfo["ServicePackMinorVersion"],
            self.myrrh_os._wininfo["OSProductSuite"],
            self.myrrh_os._wininfo["ProductType"],
            (major, minor, build),
        )
