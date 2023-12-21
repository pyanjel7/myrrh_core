from myrrh.core.services.system import ExecutionFailureCauseRVal
from ._mosenv import OsEnv


from myrrh.core.services.system import AbcRuntime
from collections import namedtuple

__mlib__ = "AbcPwd"

struct_passwd = namedtuple("struct_passwd", ("pw_name pw_passwd pw_uid pw_gid pw_gecos pw_dir pw_shell"))


class AbcPwd(AbcRuntime):
    def __init__(self, system):
        super().__init__(system=system)
        self.os = OsEnv(self)

    def getpwuid(self, uid):
        if not isinstance(uid, int):
            raise TypeError("an integer is required")

        pwall = self.getpwall()
        for pw in pwall:
            if pw.pw_uid == uid:
                return pw
        raise KeyError("getpwuid(): uid not found: %s" % uid)

    def getpwnam(self, name):
        if not isinstance(name, str):
            raise TypeError("must be string, not %s" % name.__class__.__name__)

        pwall = self.getpwall()
        for pw in pwall:
            if pw.pw_name == name:
                return pw
        raise KeyError("getpwnam(): name not found: %s" % name)

    def getpwall(self):
        out, err, rval = self.myrrh_os.cmd(b"%(cat)s /etc/passwd")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()

        pwall = []
        for line in out.split(self.os.linesep):
            try:
                line = line.split(":")
                line[2] = int(line[2])
                line[3] = int(line[3])
                pwall.append(self.struct_passwd(*line))
            except (TypeError, ValueError, IndexError):
                pass

        return pwall
