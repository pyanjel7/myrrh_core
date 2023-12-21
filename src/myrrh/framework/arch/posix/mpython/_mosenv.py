import functools

from myrrh.framework.mpython._mosenv import AbcOsEnv
from myrrh.core.services.system import ExecutionFailureCauseRVal

__mlib__ = "OsEnv"


class OsEnv(AbcOsEnv):
    name = "posix"
    linesep = "\n"

    __all__ = AbcOsEnv.__all__
    __all__.extend(["uname"])

    def __init__(self, *a, **kwa):
        self._path = None

    def putenv(self, varname, value):
        _, err, rval = self.myrrh_os.cmdb(
            b'%(echo)s "export %(varname)s=%(value)s" >> $HOME/.profile',
            varname=self.myrrh_os.sh_escape_bytes(varname),
            value=self.myrrh_os.sh_escape_bytes(value),
        )
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        _, err, rval = self.myrrh_os.cmdb(
            b'%(echo)s "export %(varname)s=%(value)s" >> $HOME/.bashrc',
            varname=self.myrrh_os.sh_escape_bytes(varname),
            value=self.myrrh_os.sh_escape_bytes(value),
        )
        ExecutionFailureCauseRVal(self, err, rval, 0).check()

    def unsetenv(self, varname):
        _, err, rval = self.myrrh_os.cmdb(
            rb'%(sed)s -i /"%(varname)s=.*"/d $HOME/.profile',
            varname=self.myrrh_os.sh_escape_bytes(varname),
        )
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        _, err, rval = self.myrrh_os.cmdb(
            rb'%(sed)s -i /"%(varname)s=.*"/d $HOME/.bashrc',
            varname=self.myrrh_os.sh_escape_bytes(varname),
        )
        ExecutionFailureCauseRVal(self, err, rval, 0).check()

    def gethome(self):
        out, err, rval = self.myrrh_os.cmd(b"%(echo)s $HOME")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        return out.strip()

    def gettemp(self):
        out, err, rval = self.myrrh_os.cmd(b"%(dirname)s `mktemp -u`")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        return out.strip()

    def getlogin(self):
        out, err, rval = self.myrrh_os.cmd(b"%(echo)s $USER")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        return out.strip()

    def geteuid(self):
        out, err, rval = self.myrrh_os.cmdb(b"%(id)s -u")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        return int(out.strip())

    def getegid(self):
        out, err, rval = self.myrrh_os.cmdb(b"%(id)s -g")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        return int(out.strip())

    def getuid(self):
        out, err, rval = self.myrrh_os.cmdb(b"%(id)s -u -r")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        return int(out.strip())

    def getgid(self):
        out, err, rval = self.myrrh_os.cmdb(b"%(id)s -g -r")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        return int(out.strip())

    def getgroups(self):
        out, err, rval = self.myrrh_os.cmdb(b"%(id)s -G")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        return [int(g) for g in out.strip().split(b" ")]

    def cpu_count(self):
        out, err, rval = self.myrrh_os.cmdb(b"%(cat)s  /proc/cpuinfo")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        s = 0
        c = 0
        while s > -1:
            c += 1
            s = out.find(b"processor", s + len(b"processor"))
        return None if c == 0 else c

    @functools.cached_property
    def _uname(self):
        out, err, rval = self.myrrh_os.cmd(b"for p in -s -n -r -v -m; do %(uname)s $p; done")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()

        infos = out.splitlines()
        if len(infos) != self.uname_result.n_fields:
            return self.uname_result([""] * self.uname_result.n_fields)

        return self.uname_result(infos)

    def uname(self):
        return self._uname
