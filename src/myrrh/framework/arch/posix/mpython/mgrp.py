import warnings


from myrrh.core.services.system import ExecutionFailureCauseRVal

from myrrh.core.services.system import AbcRuntime
from collections import namedtuple

from ._mosenv import OsEnv


__mlib__ = "AbcGrp"

struct_group = namedtuple("struct_group", "gr_name gr_passwd gr_gid gr_mem")


class AbcGrp(AbcRuntime):
    __frameworkpath__ = "mpython.mgrp"

    __all__ = ["getgrgid", "getgrnam", "getgrall"]

    struct_group = struct_group

    def __init__(self, system):
        self._os = OsEnv(self)

    def getgrgid(self, gid):
        if not isinstance(gid, int):
            warnings.warn("should be integer", DeprecationWarning)
            gid = int(gid)

        grall = self.getgrall()
        for gr in grall:
            if gr.gr_gid == gid:
                return gr
        raise KeyError("getgrgid(): gid not found: %s" % gid)

    def getgrnam(self, name):
        if not isinstance(name, str):
            raise TypeError("must be string, not %s" % name.__class__.__name__)

        grall = self.getgrall()
        for gr in grall:
            if gr.gr_name == name:
                return gr
        raise KeyError("getgrnam(): name not found: %s" % name)

    def getgrall(self):
        out, err, rval = self.myrrh_os.cmd(b"%(cat)s /etc/group")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()

        grall = []
        for line in out.split(self._os.linesep):
            try:
                line = line.split(":")
                line[2] = int(line[2])
                line[3] = [u for u in line[3].split(",") if len(u)]
                grall.append(self.struct_group(*line))
            except (TypeError, ValueError, IndexError):
                pass

        return grall
