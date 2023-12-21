import re
from functools import cached_property

from myrrh.utils import mshlex
from myrrh.utils import merrno as errno

from myrrh.core.services.system import AbcMyrrhOs, ExecutionFailureCauseRVal


class MyrrhOs(AbcMyrrhOs):
    _curdirb_ = b"."
    _pardirb_ = b".."
    _extsepb_ = b"."
    _sepb_ = b"/"
    _pathsepb_ = b":"
    _defpathb_ = b":/bin:/usr/bin"
    _altsepb_ = None
    _devnullb_ = b"/dev/null"
    _linesepb_ = b"\n"

    import posixpath

    isabs = staticmethod(posixpath.isabs)  # type: ignore[assignment]
    normpath = staticmethod(posixpath.normpath)  # type: ignore[assignment]
    joinpath = staticmethod(posixpath.join)  # type: ignore[assignment]
    basename = staticmethod(posixpath.basename)  # type: ignore[assignment]
    dirname = staticmethod(posixpath.dirname)  # type: ignore[assignment]

    _bin_dict: dict[bytes, bytes] | None = None
    _std_dict = {
        b"find": b"/usr/bin/find",
        b"ln": b"/bin/ln",
        b"chown": b"/bin/chown",
        b"chgrp": b"/bin/chgrp",
        b"chmod": b"/bin/chmod",
        b"mv": b"/bin/mv",
        b"realpath": b"/usr/bin/realpath",
        b"touch": b"/usr/bin/touch",
        b"cat": b"/bin/cat",
        b"pwd": b"/bin/pwd",
        b"sh": b"/bin/sh",
        b"set": b"set",
        b"which": b"/usr/bin/which",
        b"dirname": b"/usr/bin/dirname",
        b"id": b"/usr/bin/id",
        b"stat": b"/usr/bin/stat",
        b"echo": b"/bin/echo",
        b"truncate": b"/usr/bin/truncate",
        b"sleep": b"/bin/sleep",
        b"ps": b"/bin/ps",
        b"xargs": b"/usr/bin/xargs",
        b"cp": b"/bin/cp",
        b"tar": b"/bin/tar",
        b"mkdir": b"/bin/mkdir",
        b"rm": b"/bin/rm",
    }

    def _getbinb_(self):
        self._bin_dict = dict(self._std_dict)
        out, _, rval = self._delegate_.shell.execute(b"for p in /bin/* /usr/bin/*; do echo $p; done")
        if not rval:
            bin = {self.basename(b): b for b in out.split()}
            self._bin_dict.update(bin)

        return self._bin_dict

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
        # return '%s' % string.replace('"', r'\"')

    def _localecode_(self):
        out, err, rval = self.cmd(b"%(echo)s $LANG")
        ExecutionFailureCauseRVal(self, err, rval, 0, errno=errno.EFAULT).check()  # avoid translate error

        return out.split(".")[0]

    def _getcwdb_(self):
        out, err, rval = self.cmdb(b"%(pwd)s")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        return out

    def _gettmpdirb_(self):
        out, err, rval = self.cmdb(b'%(echo)s "$TMPDIR:$TEMP:$TMP:`[ -d /tmp ] && %(echo)s /tmp`:`[ -d /var/tmp ] && %(echo)s /var/tmp`:`[ -d /usr/tmp ] && %(echo)s /usr/tmp`"')
        ExecutionFailureCauseRVal(self, err, rval, 0).check()

        dirlist = [dir for dir in filter(None, out.split(b":"))]
        return dirlist[0] if dirlist else self._getcwdb_()

    def _getreadonlyenvb_(self):
        return (b"PPID", b"SHELLOPTS")

    def _envb_(self):
        out, err, rval = self._delegate_.shell.execute(b"set")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        env = {k: v for k, v in re.findall(b"(?P<k>[^\\n=]*)=(?P<v>'[^']*'\\n|.*\\n)", out)}
        env = {k: v.rstrip(b"\n") for k, v in env.items()}
        env = {k: v[1:-1] if len(v) > 2 and v[:1] == b"'" and v[-1:] == b"'" else v for k, v in env.items()}  # PIF! PIF patch
        return env

    @cached_property
    def _errno_localized_mapping(self):
        return errno.errno_create_localized_mapping(self.getdefaultlocale()[0])

    def default_errno_from_msg(self, err):
        err = self.shencode(err)
        return errno.errno_from_msgb(err, map=self._errno_localized_mapping)

    environkeyformat = None  # type: ignore[assignment]
    error_translate = default_errno_from_msg
