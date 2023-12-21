import re
import functools

from myrrh.core.services.system import AbcMyrrhOs, ExecutionFailureCauseRVal
from myrrh.utils import merrno
from myrrh.utils.mstring import str2int
from myrrh.utils import mshlex

_error_table = {
    b"The system cannot find the path specified.": merrno.ENOENT,
    b"File Not Found": merrno.ENOENT,
}


class MyrrhOs(AbcMyrrhOs):
    _curdirb_ = b"."
    _pardirb_ = b".."
    _extsepb_ = b"."
    _sepb_ = b"\\"
    _pathsepb_ = b";"
    _altsepb_ = b"/"
    _defpathb_ = b".;C:\\bin"
    _devnullb_ = b"nul"
    _linesepb_ = b"\r\n"

    import ntpath

    isabs = staticmethod(ntpath.isabs)  # type: ignore[assignment]
    normpath = staticmethod(ntpath.normpath)  # type: ignore[assignment]
    joinpath = staticmethod(ntpath.join)  # type: ignore[assignment]
    basename = staticmethod(ntpath.basename)  # type: ignore[assignment]
    dirname = staticmethod(ntpath.dirname)  # type: ignore[assignment]

    __fsencoding = "utf-8"
    __encoding = "utf-8"

    def _getbinb_(self):
        return {
            b"wmic": rb"C:\Windows\System32\wbem\WMIC.exe",
            b"chcp": rb"C:\Windows\System32\chcp.com",
            b"chcp_utf8": rb"C:\Windows\System32\chcp.com 65001 > NUL &&",
            b"set": b"set",
            b"echo": b"echo",
            b"where": rb"C:\Windows\System32\where.exe",
            b"setx": rb"C:\Windows\System32\setx.exe",
            b"reg": rb"C:\Windows\System32\reg.exe",
            b"reg_utf8": rb"C:\Windows\System32\chcp.com 65001 > NUL && C:\Windows\System32\reg.exe",
            b"copy": b"copy",
            b"powershell": rb"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
            b"mklink": b"mklink",
            b"cmd": rb"C:\windows\system32\cmd.exe",
            b"ping": rb"C:\Windows\System32\ping.exe",
            b"move": b"move",
            b"dir": b"dir",
            b"cd": b"cd",
            b"rename": b"rename",
            b"rmdir": b"rmdir",
            b"robocopy": rb"C:\Windows\System32\robocopy.exe",
            b"xcopy": rb"C:\Windows\System32\xcopy.exe",
            b"tar": rb"C:\Windows\System32\tar.exe",
            b"mkdir": b"mkdir",
            b"cscript": rb"C:\Windows\System32\cscript.exe",
        }

    @functools.cached_property
    def _wininfo(self):
        out, err, rval = self.cmd(b"%(wmic)s os get /all /value")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()

        return {a[0]: str2int(a[1]) for a in (line.split("=") for line in out.split("\r\n")) if len(a) == 2}

    def _getdefaultencoding_(self):
        cp = 0
        try:
            out, err, rval = self.cmdb(b"%(wmic)s os get CodeSet /value")
            ExecutionFailureCauseRVal(self, err, rval, 0).check()
            cp = re.search(rb"\d+", out).group().decode("utf8")  # default to utf8
            cp = str2int(cp)
        except Exception:
            pass

        return "cp%s" % cp if cp != 0 else self.__encoding

    def _localecode_(self):
        import locale

        return locale.windows_locale.get(self._wininfo["Locale"], "C")

    def _fsencoding_(self):
        return self.__fsencoding

    def _fsencodeerrors_(self):
        return "surrogatepass"

    def _getcwdb_(self):
        out, err, rval = self.cmdb(b"%(echo)s %%CD%%")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        return out

    def _envb_(self):
        out, err, rval = self.cmdb(b"%(set)s")
        ExecutionFailureCauseRVal(self, err, rval, 0).check()
        return {k.upper(): v for k, v in re.findall(b"(?P<k>[^=]*)=(?P<v>[^\\r]*)\\r\\n", out)}

    def _gettmpdirb_(self):
        out, err, rval = self.cmdb(b'%(echo)s %%TMPDIR%%&&%(echo)s %%TEMP%%&& %(echo)s %%TMP%% && (if exist "%%SystemDrive%%:\\temp" echo %%SystemDrive%%:\\temp) && (if exist "%%SystemDrive%%:\\tmp" echo %%SystemDrive%%:\\tmp)')
        ExecutionFailureCauseRVal(self, err, rval, 0).check()

        dirlist = [
            dir
            for dir in filter(
                lambda line: line not in (b"%TMPDIR%", b"%TEMP%", b"%TMP%"),
                out.splitlines(),
            )
        ]
        return dirlist[0] if dirlist else self._getcwdb_()

    def _getreadonlyenvb_(self):
        return []

    def _getdefaultshellb_(self):
        return self.getenvb().get(b"ComSpec", self._getbinb_()[b"cmd"])

    def _getdefaultshellargsb_(self):
        return (b"/c",)

    def formatshellargs(self, args, *, defaultargs=None):
        if isinstance(args, (str, bytes)):
            args = (self.shencode(args),)

        return (*defaultargs, *args)

    def getshellscriptb(self, script):
        codepage = self.defaultencoding
        codepage = codepage[2:] if codepage.startswith("cp") else "65001"  # default to utf8
        return b"%s %s 1>NUL 2>NUL & " % (self.getbinb.get(b"chcp", b"chcp"), codepage.encode()) + script

    def sh_escape_bytes(self, bytes):
        return mshlex.winshell_escape_for_cmd_exe_b(bytes)

    def environkeyformat(self, key):
        return key.upper()

    def error_translate(self, error):
        if error:
            error = self.shencode(error)
            errno = _error_table.get(error, merrno.default_errorno)
            if errno == merrno.default_errorno:
                return merrno.errno_from_msgb(error)
            return errno
        return merrno.default_errorno

    def syspathb(self, path=None):
        if path == b"nul":
            return b"\\\\.\\nul"

        return super().syspathb(path)
