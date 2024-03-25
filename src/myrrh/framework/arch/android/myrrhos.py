import re
import posixpath

from myrrh.core.system import AbcMyrrhOs, ExecutionFailureCauseRVal
from myrrh.utils import mshlex
from myrrh.utils import merrno as errno


class MyrrhOs(AbcMyrrhOs):

    isabs = staticmethod(posixpath.isabs)  # type: ignore[assignment]
    normpath = staticmethod(posixpath.normpath)  # type: ignore[assignment]
    joinpath = staticmethod(posixpath.join)  # type: ignore[assignment]
    basename = staticmethod(posixpath.basename)  # type: ignore[assignment]
    dirname = staticmethod(posixpath.dirname)  # type: ignore[assignment]

    def _getbin_(self):
        return {
            "find": "/system/bin/find",
            "ln": "/system/bin/ln",
            "chown": "/system/bin/chown",
            "chgrp": "/system/bin/chgrp",
            "chmod": "/system/bin/chmod",
            "mv": "/system/bin/mv",
            "realpath": "command realpath",
            "touch": "/system/bin/touch",
            "cat": "/system/bin/cat",
            "pwd": "command pwd",
            "sh": "/system/bin/sh",
            "set": "set",
            "which": "command -v",
            "dirname": "/system/bin/dirname",
            "id": "/system/bin/id",
            "stat": "/system/bin/stat",
            "echo": "print",
            "truncate": "/system/bin/truncate",
            "sleep": "/system/bin/sleep",
            "ps": "/system/bin/ps",
            "xargs": "/system/bin/xargs",
            "getprop": "/system/bin/getprop",
            "cp": "/system/bin/cp",
            "tar": "/system/bin/tar",
        }

    def _getdefaultshell_(self):
        return self.getenv().get("SHELL", self._getbin_()["sh"])

    def _getdefaultshellargs_(self):
        return ("-c",)

    def formatshellargs(self, args, *, defaultargs=None):
        return (
            *defaultargs,
            mshlex.list2cmdline(args).strip('"') if isinstance(args, (list, tuple)) else args,
        )

    def _getdefaultencoding_(self):
        return "utf-8"

    def _fsencoding_(self):
        return "utf-8"

    def _fsencodeerrors_(self):
        return "surrogateescape"

    def sh_escape(self, string: str):
        return mshlex.quote(string)

    def _locale_(self):
        return ""

    def _getcwd_(self):
        out, err, rval = self.cmd("%(pwd)s")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        return out

    def _getreadonlyenv_(self):
        return ("PPID", "KSH_VERSION", "PIPESTATUS")

    def _env_(self):
        out, err, rval = self.cmd("%(set)s")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        env = {k: v for k, v in re.findall("(?P<k>[^\\n=]*)=(?P<v>'[^']*'\\n|.*\\n)", out)}
        env = {k: v.rstrip("\n") for k, v in env.items()}
        return env

    def _gettmpdir_(self):
        out, err, rval = self.cmd('%(echo)s "$TMPDIR:$TEMP:$TMP:`[ -d /tmp ] && %(echo)s /tmp`:`[ -d /var/tmp ] && %(echo)s /var/tmp`:`[ -d /usr/tmp ] && %(echo)s /usr/tmp`"')
        ExecutionFailureCauseRVal(self, err, rval, 0).check()

        dirlist = [dir for dir in filter(None, out.split(":"))]
        return dirlist[0] if dirlist else self._getcwdb_()

    def default_errno_from_msg(self, err):
        err = self.shencode(err)
        return errno.errno_from_msg(err)

    environkeyformat = None  # type: ignore[assignment]
