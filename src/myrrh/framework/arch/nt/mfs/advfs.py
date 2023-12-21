import ntpath

from myrrh.utils import mstring
from myrrh.framework.mfs.madvfs import AbcAdvFs
from myrrh.core.services.system import (
    ExecutionFailureCauseRVal,
    ExecutionFailureCauseErr,
)

__mlib__ = "AdvFs"


class AdvFs(AbcAdvFs):
    default_mode = ""

    CHUNK_HEADER_SCRIPT = b"""\
@echo off
set vbscript=%%~F0.vbs
> %%vbscript%% echo pos=0:path="%%~F0"
>> %%vbscript%% echo Dim tStream : Set tStream = CreateObject("ADODB.Stream") : tStream.Open : tStream.LoadFromFile(path) : tStream.LineSeparator = 10 : tStream.CharSet = "utf-8"
>> %%vbscript%% echo do : line = tStream.ReadText(-2) : loop until tStream.EOS or line = "exit /b 0"
>> %%vbscript%% echo Dim s : line = tStream.ReadText(-2) : s = Split(line, ";")
>> %%vbscript%% echo Dim f : line = tStream.ReadText(-2) : f = Split(line, ";")
>> %%vbscript%% echo Dim iStream : Set iStream = CreateObject("ADODB.Stream") : iStream.Type = 1 : iStream.Open : iStream.LoadFromFile(path) : iStream.Position = tStream.Position-2
>> %%vbscript%% echo tStream.Close
>> %%vbscript%% echo For i = 0 to UBound(s)
>> %%vbscript%% echo Dim oStream : Set oStream = CreateObject("ADODB.Stream") : oStream.Type = 1 : oStream.Open
>> %%vbscript%% echo iStream.CopyTo oStream , s(i)
>> %%vbscript%% echo oStream.SaveToFile f(i), 2
>> %%vbscript%% echo oStream.Close
>> %%vbscript%% echo Next
>> %%vbscript%% echo WScript.Quit
%(cscript)s %%vbscript%%
del %%vbscript%%
(goto) 2>nul & del %%~F0 & exit /b %%errorlevel%%
exit /b 0"""

    def chown(self, path, user, group):
        # _, _, rval = self.myrrh_os.shell.execute(['/bin/chown %s:%s %s' % (user, group, path)])
        return True

    def chmod(self, mode, path):
        # _, _, rval = self.myrrh_os.shell.execute(['/bin/chmod %s %s' % (mode, path)])
        return True

    def _localtransfer(self, srcs, dest):
        if len(srcs) > 1:
            # TODO: test and refactoring required
            srcs = b" ".join((b'"%s"' % self.myrrh_os.sh_escape_bytes(s) for s in srcs))
            _, err, rval = self.myrrh_os.cmdb(
                b'if EXIST "%(dest)s\\" ( for %%f in (%(srcs)s) do if EXIST %%f\\ (%(robocopy)s /SL /E /NP %%f %%f) else (%(copy)s /Y /L %%f "%(dest)s" || exit 10) ) else exit 10',
                srcs=srcs,
                dest=self.myrrh_os.sh_escape_bytes(dest),
            )

        else:
            src = srcs[0]
            src = src.replace(b"/", self.myrrh_os._sepb_).replace(b"%", b"%%")
            dest = dest.replace(b"/", self.myrrh_os._sepb_).replace(b"%", b"%%")
            _, err, rval = self.myrrh_os.cmdb(
                b'if NOT EXIST "%(srcs)s\\" ( %(copy)s /Y /L "%(srcs)s" "%(dest)s" || exit 10 ) else if EXIST "%(dest)s\\" ( %(robocopy)s /E /SL /NP "%(srcs)s" "%(dest)s\\%(basename)s" ) else if EXIST "%(dirname)s" ( %(robocopy)s /E /SL /NP "%(srcs)s" "%(dest)s" ) else exit 10',
                srcs=self.myrrh_os.sh_escape_bytes(src),
                basename=self.myrrh_os.sh_escape_bytes(ntpath.basename(src)),
                dirname=self.myrrh_os.sh_escape_bytes(ntpath.dirname(dest) or src),
                dest=self.myrrh_os.sh_escape_bytes(dest),
            )

        err = b"No such file or directory" if rval == 10 else (b"Not a directory" if rval == 16 else err)
        rval = 0 if rval < 10 else 1

        ExecutionFailureCauseRVal(self, err, rval, 0).check()

    def _localmove(self, srcs, dest):
        if len(srcs) > 1:
            srcs = b" ".join((b'"%s"' % self.myrrh_os.sh_escape_bytes(s) for s in srcs))
            _, err, rval = self.myrrh_os.cmdb(
                b'if NOT EXIST "%(dest)s\\" (exit 10) else for %%f in (%(srcs)s) do %(move)s %%f "%(dest)s"',
                srcs=srcs,
                dest=self.myrrh_os.sh_escape_bytes(dest),
            )
        else:
            _, err, rval = self.myrrh_os.cmdb(
                b'%(move)s "%(srcs)s" "%(dest)s"',
                srcs=self.myrrh_os.sh_escape_bytes(srcs[0]),
                dest=self.myrrh_os.sh_escape_bytes(dest),
            )

        ExecutionFailureCauseRVal(self, err, rval, 0).check()

    def _localremove(self, srcs):
        srcs = b" ".join((b'"%s"' % self.myrrh_os.sh_escape_bytes(s) for s in srcs))
        _, err, rval = self.myrrh_os.cmdb(
            b"for %%f in (%(srcs)s) do if EXIST %%f\\ ( %(rmdir)s /Q /S %%f ) else del /F /Q %%f",
            srcs=srcs,
        )

        ExecutionFailureCauseRVal(self, err, rval, 0).check()

    def _chunk_header(self, file_descs):
        szs = b";".join((str(f[2]).encode() for f in file_descs))
        paths = b";".join((self.myrrh_os.p(f[1]) for f in file_descs))
        script = b"\n".join((self.CHUNK_HEADER_SCRIPT % {b"cscript": self.myrrh_os.getbinb[b"cscript"]}).splitlines())
        script = b"\n".join((script, szs, paths)) + b"\n"
        return script

    def _unchunk(self, path):
        path = self.myrrh_os.p(path)
        path_bat = b".".join((path, b"bat"))
        _, e, r = self.myrrh_os.cmdb(
            b'%(move)s "%(path)s" "%(path_bat)s" && "%(path_bat)s"',
            path=self.myrrh_os.sh_escape_bytes(path),
            path_bat=self.myrrh_os.sh_escape_bytes(path_bat),
        )
        ExecutionFailureCauseErr(self, e, b"").check()

    def _write_chunk(self, path, file_descs):
        path = self.myrrh_os.p(path)
        files = b"+".join((b'"%s"' % self.myrrh_os.sh_escape_bytes(self.myrrh_os.p(file)) for file, _, _ in file_descs))
        _, e, r = self.myrrh_os.cmdb(
            b'%(copy)s /B /Y %(files)s "%(path)s"',
            files=files,
            path=self.myrrh_os.sh_escape_bytes(path),
        )
        ExecutionFailureCauseRVal(self, e, r, 0).check()

    def _mkdirs(self, dirs: list):
        cmd = b"for %%d in ( %(dirs)s ) do if NOT EXIST %%d %(mkdir)s %%d"

        dirs = b" ".join((b'"%s\\"' % self.myrrh_os.sh_escape_bytes(d) for d in dirs))

        _, e, r = self.myrrh_os.cmdb(cmd, dirs=dirs)
        ExecutionFailureCauseRVal(self, e, r, 0).check()

    def _scanfiles(self, files):
        """
        return files(path, size)
        """
        files = b" ".join((b'"%s"' % self.myrrh_os.sh_escape_bytes(f) for f in files))
        o, e, r = self.myrrh_os.cmdb(b"for %%f in ( %(files)s ) do @echo %%f;%%~zf", files=files)
        ExecutionFailureCauseRVal(self, e, r, 0).check()

        output = (o.split(b";") for o in o.splitlines())

        files = []
        for path, sz in output:
            files.append(
                (
                    self.myrrh_os.shdecode(path).encode().strip(b'"'),
                    mstring.str2intb(sz),
                )
            )

        return files

    def _scantree(self, path):
        path = self.myrrh_os.p(path)

        o, e, r = self.myrrh_os.cmdb(
            b'for /f "usebackq delims=="  %%f in ( `dir /B /s` ) do @echo %%f;%%~af;%%~zf',
            execute_working_dir=path,
        )
        ExecutionFailureCauseRVal(self, e, r, 0).check()

        output = (o.split(b";") for o in o.splitlines())

        dirs = []
        files = []
        for path, ty, sz in output:
            if ty and ty[0] == ord(b"d"):
                dirs.append(self.myrrh_os.shdecode(path).encode())
            else:
                files.append((self.myrrh_os.shdecode(path).encode(), mstring.str2intb(sz)))

        return dirs, files
