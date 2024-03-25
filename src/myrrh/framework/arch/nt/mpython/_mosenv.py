from myrrh.utils.mstring import str2int
from myrrh.core.system import ExecutionFailureCauseRVal

from myrrh.framework.mpython._mosenv import AbcOsEnv

__mlib__ = "OsEnv"


class OsEnv(AbcOsEnv):
    name = "nt"
    linesep = "\r\n"

    def putenv(self, varname, value):
        _, err, rval = self.myrrh_os.cmd(
            '%(setx)s "%(varname)s" "%(value)s"',
            varname=self.myrrh_os.sh_escape(varname),
            value=self.myrrh_os.sh_escape(value),
        )
        ExecutionFailureCauseRVal(self, err, rval, 0).check()

    def unsetenv(self, varname):
        _, err, rval = self.myrrh_os.cmd(
            rb'%(reg)s DELETE HKCU\Environment /F /V "%(varname)s"',
            varname=self.myrrh_os.sh_escape(varname),
        )
        ExecutionFailureCauseRVal(self, err, rval, 0).check()

    def gethome(self):
        out, err, rval = self.myrrh_os.cmd("%(echo)s %%HOMEDRIVE%%%%HOMEPATH%%")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        return out.strip()

    def gettemp(self):
        out, err, rval = self.myrrh_os.cmd("%(echo)s %%TEMP%%")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        return out.strip()

    def getlogin(self):
        out, err, rval = self.myrrh_os.cmd("%(echo)s %%USERNAME%%@%%USERDOMAIN%%")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        return out.strip()

    def geteuid(self):
        return 0

    def getegid(self):
        return 0

    def getuid(self):
        return 0

    def getgid(self):
        return 0

    def getgroups(self):
        return [0]

    def cpu_count(self):
        out, err, rval = self.myrrh_os.cmd("%(wmic)s cpu get NumberOfCores")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        out = out.split("\r\n")
        return str2int(out[1])
