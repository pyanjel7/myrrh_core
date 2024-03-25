import functools
import re
from functools import cached_property
import posixpath

from myrrh.utils import mshlex
from myrrh.utils import merrno as errno

from myrrh.core.system import AbcMyrrhOs, ExecutionFailureCauseRVal


class MyrrhOs(AbcMyrrhOs):

    isabs = staticmethod(posixpath.isabs)  # type: ignore[assignment]
    normpath = staticmethod(posixpath.normpath)  # type: ignore[assignment]
    joinpath = staticmethod(posixpath.join)  # type: ignore[assignment]
    basename = staticmethod(posixpath.basename)  # type: ignore[assignment]
    dirname = staticmethod(posixpath.dirname)  # type: ignore[assignment]

    _std_bins = {
        "find": "/usr/bin/find",
        "ln": "/bin/ln",
        "chown": "/bin/chown",
        "chgrp": "/bin/chgrp",
        "chmod": "/bin/chmod",
        "mv": "/bin/mv",
        "realpath": "/usr/bin/realpath",
        "touch": "/usr/bin/touch",
        "cat": "/bin/cat",
        "pwd": "/bin/pwd",
        "sh": "/bin/sh",
        "set": "set",
        "which": "/usr/bin/which",
        "dirname": "/usr/bin/dirname",
        "id": "/usr/bin/id",
        "stat": "/usr/bin/stat",
        "echo": "/bin/echo",
        "truncate": "/usr/bin/truncate",
        "sleep": "/bin/sleep",
        "ps": "/bin/ps",
        "xargs": "/usr/bin/xargs",
        "cp": "/bin/cp",
        "tar": "/bin/tar",
        "mkdir": "/bin/mkdir",
        "rm": "/bin/rm",
    }

    _system_defaults = {
        "os": "posix",
        "encoding": "utf-8",
        "eol": "\n",
    }

    def formatshellargs(self, args, *, defaultargs=None):
        if isinstance(args, str):
            args = args.encode()
        return (
            *defaultargs,
            mshlex.list2cmdline(args).strip('"') if isinstance(args, (list, tuple)) else args,
        )

    def sh_escape(self, string):
        return mshlex.quote(string)

    @cached_property
    def _errno_localized_mapping(self):
        return errno.errno_create_localized_mapping(self.getdefaultlocale()[0])

    def default_errno_from_msg(self, err):
        err = self.shencode(err)
        return errno.errno_from_msg(err, map=self._errno_localized_mapping)

    environkeyformat = None  # type: ignore[assignment]
    error_translate = default_errno_from_msg

    def catalog(self):
        return ["system", "directory", "vars", "session", "shell"]

    def deliver(self, data: dict, name: str):

        match name:
            case "directory":
                item = self._get_item_directory()
                item["executables"] = data.get("executables") or self._get_executables()
                item["tmpdirs"] = data.get("tmpdirs") or self._get_tmpdirs()
                return item

            case "vars":
                return {
                    "defined": data.get("defined") or self._environ,
                    "readonly": ["PPID", "SHELLOPTS"],
                }

            case "system":
                sys = dict(self._system_defaults)
                sys.update(
                    {
                        "locale": data.get("locale") or self._get_locale(),
                        "myrrhos": "myrrh.framework.arch.posix.myrrhos",
                    }
                )
                return sys

            case "session":
                return {
                    "cwd": data.get("cwd") or self._get_cwd(),
                    "tmpdir": "/tmp",
                }

            case "shell":
                return {
                    "encoding": "utf-8",
                    "path": data.get("path") or self._get_shell(),
                    "args": ["-c"],
                    "commands": {},
                }

    def _get_item_directory(self):
        return {
            "devnull": "/dev/null",
            "sep": posixpath.sep,
            "curdir": posixpath.curdir,
            "pardir": posixpath.pardir,
            "extsep": posixpath.extsep,
            "pathsep": posixpath.pathsep,
        }

    def _get_executables(self):
        self._bin_dict = self._std_bins
        out, _, rval = self.cmd_utf8("for p in /bin/* /usr/bin/*; do echo $p; done")
        if not rval:
            bin = {self.basename(b): b for b in out.split()}
            self._bin_dict.update(bin)

        return self._bin_dict

    def _get_tmpdirs(self):
        out, err, rval = self.cmd_utf8('%(echo)s "$TMPDIR:$TEMP:$TMP:`[ -d /tmp ] && %(echo)s /tmp`:`[ -d /var/tmp ] && %(echo)s /var/tmp`:`[ -d /usr/tmp ] && %(echo)s /usr/tmp`"')
        ExecutionFailureCauseRVal(self, err, rval, 0).check()

        dirlist = [dir for dir in filter(None, out.split(":"))]
        return dirlist

    @functools.cached_property
    def _environ(self):
        out, err, rval = self.cmd_utf8("set")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        env = {k: v for k, v in re.findall("(?P<k>[^\\n=]*)=(?P<v>'[^']*'\\n|.*\\n)", out)}
        env = {k: v.rstrip("\n") for k, v in env.items()}
        env = {k: v[1:-1] if len(v) > 2 and v[:1] == "'" and v[-1:] == "'" else v for k, v in env.items()}  # PIF! PIF patch
        return env

    def _get_locale(self):
        out, err, rval = self.cmd_utf8("%(echo)s $LANG")
        ExecutionFailureCauseRVal(self, err, rval, 0, errno=errno.EFAULT).check()  # avoid translate error

        return out.split(".")[0]
    
    def _get_cwd(self):
        out, err, rval = self.cmd_utf8("%(pwd)s")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        return out

    def _get_shell(self):
        return self._environ.get("SHELL", "/bin/sh")

    def cmd_utf8(self, cmd: str) -> tuple[str, str, int]:
        out, err, rval = self._delegate_.shell.execute(cmd)
        ExecutionFailureCauseRVal(self, err.decode("utf8"), rval, 0).check()
        return out.decode("utf8")
