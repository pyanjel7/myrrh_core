from myrrh.utils.mstring import str2int
from myrrh.core.services.system import ExecutionFailureCauseRVal

from myrrh.framework.mpython._mosenv import AbcOsEnv

__mlib__ = "OsEnv"


class OsEnv(AbcOsEnv):
    name = "nt"
    linesep = "\r\n"

    def putenv(self, varname, value):
        _, err, rval = self.myrrh_os.cmdb(
            b'%(setx)s "%(varname)s" "%(value)s"',
            varname=self.myrrh_os.sh_escape_bytes(varname),
            value=self.myrrh_os.sh_escape_bytes(value),
        )
        ExecutionFailureCauseRVal(self, err, rval, 0).check()

    def unsetenv(self, varname):
        _, err, rval = self.myrrh_os.cmdb(
            rb'%(reg)s DELETE HKCU\Environment /F /V "%(varname)s"',
            varname=self.myrrh_os.sh_escape_bytes(varname),
        )
        ExecutionFailureCauseRVal(self, err, rval, 0).check()

    def gethome(self):
        out, err, rval = self.myrrh_os.cmd(b"%(echo)s %%HOMEDRIVE%%%%HOMEPATH%%")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        return out.strip()

    def gettemp(self):
        out, err, rval = self.myrrh_os.cmd(b"%(echo)s %%TEMP%%")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        return out.strip()

    def getlogin(self):
        out, err, rval = self.myrrh_os.cmd(b"%(echo)s %%USERNAME%%@%%USERDOMAIN%%")
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
        out, err, rval = self.myrrh_os.cmd(b"%(wmic)s cpu get NumberOfCores")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        out = out.split("\r\n")
        return str2int(out[1])
