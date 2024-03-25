import functools

from myrrh.core.system import ExecutionFailureCauseRVal

from myrrh.framework.mpython._mosenv import AbcOsEnv

__mlib__ = "OsEnv"


class OsEnv(AbcOsEnv):
    name = "posix"
    linesep = "\n"

    def __init__(self, system):
        super(AbcOsEnv, self).__init__(system=system)
        self._path = None

    def putenv(self, varname, value):
        _, err, rval = self.myrrh_os.cmd(
            '%(echo)s "export %(varname)s=%(value)s" >> $HOME/.profile',
            varname=self.myrrh_os.sh_escape(varname),
            value=self.myrrh_os.sh_escape(value),
        )
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        _, err, rval = self.myrrh_os.cmd(
            '%(echo)s "export %(varname)s=%(value)s" >> $HOME/.bashrc',
            varname=self.myrrh_os.sh_escape(varname),
            value=self.myrrh_os.sh_escape(value),
        )
        ExecutionFailureCauseRVal(self, err, rval, 0).check()

    def unsetenv(self, varname):
        _, err, rval = self.myrrh_os.cmd(
            rb'%(sed)s -i /"%(varname)s=.*"/d $HOME/.profile',
            varname=self.myrrh_os.sh_escape(varname),
        )
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        _, err, rval = self.myrrh_os.cmd(
            rb'%(sed)s -i /"%(varname)s=.*"/d $HOME/.bashrc',
            varname=self.myrrh_os.sh_escape(varname),
        )
        ExecutionFailureCauseRVal(self, err, rval, 0).check()

    def gethome(self):
        out, err, rval = self.myrrh_os.cmd("%(echo)s $HOME")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        return out.strip()

    def gettemp(self):
        out, err, rval = self.myrrh_os.cmd("%(dirname)s `mktemp -u`")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        return out.strip()

    def getlogin(self):
        out, err, rval = self.myrrh_os.cmd("%(echo)s $USER")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        return out.strip()

    def geteuid(self):
        return self.reg.system.uid or 0

    def getegid(self):
        return self.reg.system.gid or 0

    def getuid(self):
        return self.geteuid()

    def getgid(self):
        return self.getegid()

    def getgroups(self):
        return self.reg.system.groups or [0]

    @functools.cache
    def cpu_count(self):
        out, err, rval = self.myrrh_os.cmd("%(cat)s  /proc/cpuinfo")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        s = 0
        c = 0
        while s > -1:
            c += 1
            s = out.find("processor", s + len("processor"))
        return None if c == 0 else c
