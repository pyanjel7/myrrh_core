import re
import posixpath

from myrrh.core.services.system import AbcMyrrhOs, ExecutionFailureCauseRVal
from myrrh.utils import mshlex
from myrrh.utils import merrno as errno


class MyrrhOs(AbcMyrrhOs):
    _curdirb_ = b"."
    _pardirb_ = b".."
    _extsepb_ = b"."
    _sepb_ = b"/"
    _pathsepb_ = b":"
    _defpathb_ = b":/system/bin"
    _altsepb_ = None
    _devnullb_ = b"/dev/null"
    _linesepb_ = b"\n"

    isabs = staticmethod(posixpath.isabs)  # type: ignore[assignment]
    normpath = staticmethod(posixpath.normpath)  # type: ignore[assignment]
    joinpath = staticmethod(posixpath.join)  # type: ignore[assignment]
    basename = staticmethod(posixpath.basename)  # type: ignore[assignment]
    dirname = staticmethod(posixpath.dirname)  # type: ignore[assignment]

    def _getbinb_(self):
        return {
            b"find": b"/system/bin/find",
            b"ln": b"/system/bin/ln",
            b"chown": b"/system/bin/chown",
            b"chgrp": b"/system/bin/chgrp",
            b"chmod": b"/system/bin/chmod",
            b"mv": b"/system/bin/mv",
            b"realpath": b"command realpath",
            b"touch": b"/system/bin/touch",
            b"cat": b"/system/bin/cat",
            b"pwd": b"command pwd",
            b"sh": b"/system/bin/sh",
            b"set": b"set",
            b"which": b"command -v",
            b"dirname": b"/system/bin/dirname",
            b"id": b"/system/bin/id",
            b"stat": b"/system/bin/stat",
            b"echo": b"print",
            b"truncate": b"/system/bin/truncate",
            b"sleep": b"/system/bin/sleep",
            b"ps": b"/system/bin/ps",
            b"xargs": b"/system/bin/xargs",
            b"getprop": b"/system/bin/getprop",
            b"cp": b"/system/bin/cp",
            b"tar": b"/system/bin/tar",
        }

    def _getdefaultshellb_(self):
        return self.getenvb().get(b"SHELL", self._getbinb_()[b"sh"])

    def _getdefaultshellargsb_(self):
        return (b"-c",)

    def formatshellargs(self, args, *, defaultargs=None):
        if isinstance(args, str):
            args = args.encode()
        return (
            *defaultargs,
            mshlex.list2cmdlineb(args).strip(b'"') if isinstance(args, (list, tuple)) else args,
        )

    def _getdefaultencoding_(self):
        return "utf-8"

    def _fsencoding_(self):
        return "utf-8"

    def _fsencodeerrors_(self):
        return "surrogateescape"

    def sh_escape_bytes(self, string):
        return mshlex.quote(string)

    def _localecode_(self):
        return ""

    def _getcwdb_(self):
        out, err, rval = self.cmdb(b"%(pwd)s")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        return out

    def _getreadonlyenvb_(self):
        return (b"PPID", b"KSH_VERSION", b"PIPESTATUS")

    def _envb_(self):
        out, err, rval = self.cmdb(b"%(set)s")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        env = {k: v for k, v in re.findall(b"(?P<k>[^\\n=]*)=(?P<v>'[^']*'\\n|.*\\n)", out)}
        env = {k: v.rstrip(b"\n") for k, v in env.items()}
        return env

    def _gettmpdirb_(self):
        out, err, rval = self.cmdb(b'%(echo)s "$TMPDIR:$TEMP:$TMP:`[ -d /tmp ] && %(echo)s /tmp`:`[ -d /var/tmp ] && %(echo)s /var/tmp`:`[ -d /usr/tmp ] && %(echo)s /usr/tmp`"')
        ExecutionFailureCauseRVal(self, err, rval, 0).check()

        dirlist = [dir for dir in filter(None, out.split(b":"))]
        return dirlist[0] if dirlist else self._getcwdb_()

    def default_errno_from_msg(self, err):
        err = self.shencode(err)
        return errno.errno_from_msgb(err)

    environkeyformat = None  # type: ignore[assignment]
