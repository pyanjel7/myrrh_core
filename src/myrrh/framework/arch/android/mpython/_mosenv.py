import functools

from myrrh.core.services.system import ExecutionFailureCauseRVal

from myrrh.framework.mpython._mosenv import AbcOsEnv

__mlib__ = "OsEnv"


class OsEnv(AbcOsEnv):
    name = "posix"
    linesep = "\n"

    def __init__(self, system):
        super(AbcOsEnv, self).__init__(system=system)
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
        return self.cfg.system.uid or 0

    def getegid(self):
        return self.cfg.system.gid or 0

    def getuid(self):
        return self.geteuid()

    def getgid(self):
        return self.getegid()

    def getgroups(self):
        return self.cfg.system.groups or [0]

    @functools.cache
    def cpu_count(self):
        out, err, rval = self.myrrh_os.cmdb(b"%(cat)s  /proc/cpuinfo")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        s = 0
        c = 0
        while s > -1:
            c += 1
            s = out.find(b"processor", s + len(b"processor"))
        return None if c == 0 else c
