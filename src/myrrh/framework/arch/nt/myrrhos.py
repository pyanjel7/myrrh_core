import re
import functools
import ntpath

from myrrh.core.interfaces import IERegistry

from myrrh.core.system import AbcMyrrhOs, ExecutionFailureCauseRVal
from myrrh.utils import merrno
from myrrh.utils.mstring import str2int
from myrrh.utils import mshlex

_error_table = {
    "The system cannot find the path specified.": merrno.ENOENT,
    "File Not Found": merrno.ENOENT,
}


class MyrrhOs(AbcMyrrhOs):

    isabs = staticmethod(ntpath.isabs)  # type: ignore[assignment]
    normpath = staticmethod(ntpath.normpath)  # type: ignore[assignment]
    joinpath = staticmethod(ntpath.join)  # type: ignore[assignment]
    basename = staticmethod(ntpath.basename)  # type: ignore[assignment]
    dirname = staticmethod(ntpath.dirname)  # type: ignore[assignment]

    def formatshellargs(self, args, *, defaultargs=None):
        if isinstance(args, (str, bytes)):
            args = (self.shencode(args),)

        return (*defaultargs, *args)

    def getshellscript(self, script):
        codepage = self.defaultencoding
        codepage = codepage[2:] if codepage.startswith("cp") else "65001"  # default to utf8
        return "%s %s 1>NUL 2>NUL & " % (self.getbin.get("chcp", "chcp"), codepage.encode()) + script

    def sh_escape(self, bytes):
        return mshlex.winshell_escape_for_cmd_exe(bytes)

    def environkeyformat(self, key):
        return key.upper()

    def error_translate(self, error):
        if error:
            errno = _error_table.get(error, merrno.default_errorno)
            if errno == merrno.default_errorno:
                return merrno.errno_from_msg(error)
            return errno
        return merrno.default_errorno

    def syspath(self, path=None):
        if path == "nul":
            return "\\\\.\\nul"

        return super().syspath(path)

    def catalog(self):
        return ["system", "directory", "vars", "session", "shell"]

    def deliver(self, data: dict, name: str):

        match name:

            case "directory":
                item = self._get_item_directory()
                item["tmpdirs"] = data.get("tmpdirs") or self._get_tmpdirs()
                item["encoding"] = data.get("encoding") or f'cp{self._win_os_info.get("CodeSet")}'
                return item

            case "vars":
                return {"defined": data.get("defined") or self._environ, "readonly": []}

            case "system":
                return {
                    "os": "nt",
                    "version": data.get("version") or self._win_os_info.get("Version"),
                    "machine": data.get("machine") or self._environ["PROCESSOR_ARCHITECTURE"],
                    "locale": data.get("locale") or self._get_locale(),
                    "eol": "\r\n",
                    "myrrhos": "myrrh.framework.arch.nt.myrrhos",
                }

            case "session":
                return {
                    "cwd": data.get("cwd") or self._get_cwd(),
                    "login": data.get("login") or self._environ["USERNAME"],
                    "domain": data.get("domain") or self._environ["USERDOMAIN"],
                    "tmpdir": data.get("tmpdir") or self._environ["TEMP"],
                    "homedir": data.get("homedir") or self._environ["USERPROFILE"],
                }

            case "shell":
                return {
                    "encoding": data.get("encoding") or self._get_shell_encoding(),
                    "path": data.get("path") or self._get_shell_path(),
                    "args": ["/C"],
                    "commands": {},
                }

    @functools.cached_property
    def _win_os_info(self):
        o = self.cmd_utf8("wmic os get /all /value")
        return {a[0]: str2int(a[1]) for a in (line.split("=") for line in o.split("\r\n")) if len(a) == 2}

    def _get_item_directory(self):
        return {
            "devnull": "NUL",
            "sep": ntpath.sep,
            "curdir": ntpath.curdir,
            "pardir": ntpath.pardir,
            "extsep": ntpath.extsep,
            "pathsep": ntpath.pathsep,
            "executables": {
                "wmic": "C:\\Windows\\System32\\wbem\\WMIC.exe",
                "chcp": "C:\\Windows\\System32\\chcp.com",
                "set": "set",
                "echo": "echo",
                "where": "C:\\Windows\\System32\\where.exe",
                "setx": "C:\\Windows\\System32\\setx.exe",
                "reg": "C:\\Windows\\System32\\chcp.com 65001 > NUL && C:\\Windows\\System32\\reg.exe",
                "copy": "copy",
                "powershell": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
                "mklink": "mklink",
                "cmd": "C:\\windows\\system32\\cmd.exe",
                "ping": "C:\\Windows\\System32\\ping.exe",
                "move": "move",
                "dir": "dir",
                "cd": "cd",
                "rename": "rename",
                "rmdir": "rmdir",
                "robocopy": "C:\\Windows\\System32\\robocopy.exe",
                "xcopy": "C:\\Windows\\System32\\xcopy.exe",
                "tar": "C:\\Windows\\System32\\tar.exe",
                "mkdir": "mkdir",
                "cscript": "C:\\Windows\\System32\\cscript.exe",
            },
        }

    def _get_locale(self):
        import locale

        return locale.windows_locale.get(self._win_os_info["Locale"], "C")

    def _get_cwd(self):
        out = self.cmd_utf8("echo %CD%")
        return out.strip()

    @functools.cached_property
    def _environ(self):
        out = self.cmd_utf8("set")
        return {k.upper(): v for k, v in re.findall("(?P<k>[^=]*)=(?P<v>[^\\r]*)\\r\\n", out)}

    def _get_tmpdirs(self):
        out = self.cmd_utf8('echo %TMPDIR% && echo %TEMP% && echo %TMP% && (if exist "%SystemDrive%:\\temp" echo %SystemDrive%:\\temp) && (if exist "%SystemDrive%:\\tmp" echo %SystemDrive%:\\tmp)')

        dirlist = [
            dir
            for dir in filter(
                lambda line: line not in ("%TMPDIR%", "%TEMP%", "%TMP%"),
                out.splitlines(),
            )
        ]
        return ntpath.pathsep.join(dirlist)

    def _get_shell_path(self):
        return self._environ().get("ComSpec", "C:\\windows\\system32\\cmd.exe")

    def _get_shell_encoding(self):
        return self._environ().get("ComSpec", "C:\\windows\\system32\\cmd.exe")

    def cmd_utf8(self, cmd: str) -> tuple[str, str, int]:
        out, err, rval = self._delegate_.shell.execute("chcp.com 65001 > NUL && " + cmd)
        ExecutionFailureCauseRVal(self, err.decode("utf8"), rval, 0).check()
        return out.decode("utf8")
