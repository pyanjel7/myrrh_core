import time
import stat
import os
import re
import sys
import calendar

from myrrh.utils.mstring import str2int

from myrrh.core.system import (
    ExecutionFailureCauseRVal,
    ExecutionFailureCauseErr,
    _mlib_,
)
from myrrh.utils.delegation import ABCDelegation, ABC, abstractmethod

from myrrh.framework.mpython import mbuiltins
from myrrh.framework.mpython._mosfs import AbcOsFs, stat_result

__mlib__ = "OsFs"


class _interface(ABC):
    import ntpath as local_path

    @abstractmethod
    def normcase(self, s): ...

    @abstractmethod
    def splitdrive(self, p): ...

    @abstractmethod
    def split(self, p): ...

    @abstractmethod
    def expandvars(self, path): ...

    @abstractmethod
    def _get_bothseps(self, path) -> str | bytes: ...


class OsFs(_interface, AbcOsFs, ABCDelegation):
    _umask = 0o000
    _epochdelta = 0 if sys.version_info >= (3, 6) else 3600
    _PATHEXT = {".COM", ".EXE", ".BAT", ".CMD", ".VBS", ".JS", ".WS", ".MSC"}

    __delegated__ = {_interface: _interface.local_path}
    __delegate_check_type__ = False

    def __init__(self, *a, **kwa):
        mod = mbuiltins.wrap_module(self.local_path, self, {"os": self})

        self.__delegate__(_interface, mod)

    def ismount(self, mount):
        mount = self.myrrh_os.p(mount)
        return re.match("([a-zA-Z]:$)|(//.*)", mount) is not None

    def _wmidatetoiso(self, str):
        str = self.sdecode(str)
        date = re.match(r"(\d+.\d+)([+|-])(\d+|\*+)", str)
        if date is None:
            date = re.match(r"(\d+.\d+)([+|-])(\d+|\*+)", "197603090000.000000+000")
        date = date.groups()
        tz = str2int(date[2], 0)
        return "%s%s%02d%02d" % (date[0], date[1], tz // 60, tz % 60)

    def chown(self, path, uid, gid, *, dir_fd=None, follow_symlinks=True, _trusted=False):
        if _trusted:
            return

        if not isinstance(uid, int):
            raise TypeError("invalid user type")
        if not isinstance(gid, int):
            raise TypeError("invalid group type")

        if uid == -1 and gid == -1:
            return

        self._stat(path)

    def chmod(self, path, mode, *, dir_fd=None, follow_symlinks=True, _trusted=False):
        if _trusted:
            return

        self._stat(path)

    def rename(self, src, dst, *, src_dir_fd=None, dst_dir_fd=None):
        _src = self.myrrh_os.p(src, dir_fd=src_dir_fd)
        _dst = self.myrrh_os.p(dst, dir_fd=dst_dir_fd)

        _src = self.abspath(_src)
        _dst = self.abspath(_dst)

        samepath = _src.lower() == _dst.lower()

        cmd, _dst = ('%(rename)s "%(src)s" "%(dst)s"', self.myrrh_os.basename(_dst)) if samepath else ('%(move)s /Y "%(src)s" "%(dst)s"', _dst)

        _, err, rval = self.myrrh_os.cmd(
            cmd,
            src=self.myrrh_os.sh_escape(_src),
            dst=self.myrrh_os.sh_escape(_dst),
        )

        ExecutionFailureCauseRVal(self, err, rval, 0, src).check()

    def listdir(self, path="."):
        _cast_ = self.myrrh_os.fdcast(path)
        path = self.myrrh_os.normpath(path)

        _path = self.myrrh_os.p(path)

        out, err, rval = self.myrrh_os.cmd(
            'if exist "%(path)s\\"  ( %(dir)s /B "%(path)s" ) else if exist "%(path)s" (exit 20) else ( exit 2 )',
            path=self.myrrh_os.sh_escape(_path),
        )

        ExecutionFailureCauseRVal(self, err, rval, 0, _cast_(path), errno=rval).check()
        return [_cast_(f) for f in [f.strip() for f in out.split(self.myrrh_os.linesep)] if f != self.myrrh_os.curdir and f != self.myrrh_os.pardir and len(f) != 0]

    def _scandir_list(self, path="."):
        # wmic output always in os encoding

        _cast_ = self.myrrh_os.fdcast(path)
        _path = self.myrrh_os.p(path)
        _abspath = self.abspath(_path)
        wmicpath = _abspath.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')

        drive, wmicpath = self.splitdrive(wmicpath)
        wmicpath = "" if wmicpath == "\\\\" else wmicpath
        out, err, rval = self.myrrh_os.cmd(
            "%(dir)s /B \"%(path)s\" && %(echo)s \"OOO___:__OOOO\" && %(wmic)s fsdir where \"path='%(wmicpath)s\\\\' and drive='%(drive)s'\" get %(property)s /value && %(wmic)s datafile where \"path='%(wmicpath)s\\\\' and drive='%(drive)s'\" get %(property)s /value",
            path=self.myrrh_os.sh_escape(_path),
            drive=drive,
            wmicpath=wmicpath,
            property=self._stat_property,
        )
        ExecutionFailureCauseRVal(self, err, rval, 0, path).check()

        # try translate to utf8 bytes
        try:
            out = out.encode()
            err = err.encode()
        except ValueError:
            pass

        out_dir, out_wmi = out.split('"OOO___:__OOOO"', 1)
        real_file_name = {o.lower(): o for o in out_dir.split("\r\n")}

        # utf16 hack
        if "\x00" in out_wmi:
            out_wmi = out_wmi.replace("\x00", "")

        out_wmi = re.split("[\\r\\n]{4,}", out_wmi)

        result = []
        for stat_ in (s for s in out_wmi if s.strip()):
            fpath, stat_ = self._stat_out_to_struct(stat_)
            fname = self.myrrh_os.basename(fpath)
            # find real name
            for fn_lower, fn in real_file_name.items():
                if fname == fn_lower:
                    fname = fn
                    break
            else:
                fn_lower = ""

            if fn_lower:
                real_file_name.pop(fn_lower)

            fpath = self.myrrh_os.joinpath(_path, fname)
            result.append(self.DirEntry(_cast_(fname), _cast_(fpath), stat_, self.lstat))

        return result

    def isdir(self, path):
        path = self.myrrh_os.p(path)

        if len(path) == 0:
            return False

        return self.myrrh_os.fs.is_container(path)

    def isfile(self, path):
        path = self.myrrh_os.p(path)

        if len(path) == 0:
            return False

        return self.myrrh_os.fs.exist(path) and not self.myrrh_os.fs.is_container(path)

    @property
    def _pathext(self):
        return self._PATHEXT.union(p.upper() for p in (self.myrrh_os.getenv().get("PATHEXT", "").split(self.myrrh_os.pathsep)))

    _stat_property = "name,filesize,readable,writeable,filetype,creationdate,lastaccessed,lastmodified,archive,compressed,encrypted,hidden,system"

    def _stat_out_to_struct(self, out):
        if "\x00" in out:
            out = out.lstrip().rstrip("x00")
            out = self.myrrh_os.shencode(out.decode("utf-16-be"))

        out_stat = {a[0]: a[1].strip() for a in (line.split("=", 1) for line in out.split("\r\n")) if len(a) == 2}

        mode = stat.S_IFDIR if out_stat.get("FileType", "") in ("File Folder", "Local Disk") else stat.S_IFREG
        path = out_stat.get("Name", "myrrh_unexpected_error???????")
        # read GR
        if out_stat.get("Readable", "TRUE") == "TRUE":
            access_mask_win = stat.S_IRUSR
        if out_stat.get("Writeable", "TRUE") == "TRUE":
            access_mask_win += stat.S_IWUSR
        _, ext = self.splitext(path)
        if ext.upper() in self._pathext:
            access_mask_win += stat.S_IXUSR

        mode += (stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH) if (access_mask_win & stat.S_IRUSR) == stat.S_IRUSR or (access_mask_win & stat.S_IFDIR) == stat.S_IFDIR else 0
        mode += (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH) if (access_mask_win & stat.S_IWUSR) == stat.S_IWUSR or (access_mask_win & stat.S_IFDIR) == stat.S_IFDIR else 0
        mode += (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH) if (access_mask_win & stat.S_IXUSR) == stat.S_IXUSR or (mode & stat.S_IFDIR) == stat.S_IFDIR else 0

        file_size = out_stat.get("FileSize", "")
        if file_size == "":
            file_size = "0"
        creation_date = out_stat.get("CreationDate", "")
        if creation_date == "":
            creation_date = "19700101010000.000000+000"
        last_accessed = out_stat.get("LastAccessed", "")
        if last_accessed == "":
            last_accessed = creation_date
        last_modified = out_stat.get("LastModified", "")
        if last_modified == "":
            last_modified = creation_date

        def mktime(date):
            date = time.strptime(self._wmidatetoiso(date), "%Y%m%d%H%M%S.%f%z")
            date = calendar.timegm(date) - self._epochdelta
            return date, date * 1000000000

        creation_date, creation_date_ns = mktime(creation_date)
        last_accessed, last_accessed_ns = mktime(last_accessed)
        last_modified, last_modified_ns = mktime(last_modified)

        st_file_attributes = (
            (stat.FILE_ATTRIBUTE_ARCHIVE if out_stat.get("Archive", "FALSE") == "TRUE" else 0)
            | (stat.FILE_ATTRIBUTE_COMPRESSED if out_stat.get("Compressed", "FALSE") == "TRUE" else 0)
            | (stat.FILE_ATTRIBUTE_ENCRYPTED if out_stat.get("Encrypted", "FALSE") == "TRUE" else 0)
            | (stat.FILE_ATTRIBUTE_HIDDEN if out_stat.get("Hidden", "FALSE") == "TRUE" else 0)
            | (stat.FILE_ATTRIBUTE_READONLY if out_stat.get("Readable", "FALSE") == "TRUE" else 0)
            | (stat.FILE_ATTRIBUTE_SYSTEM if out_stat.get("System", "FALSE") == "TRUE" else 0)
            | (stat.FILE_ATTRIBUTE_DIRECTORY if out_stat.get("FileType", "") in ("File Folder", "Local Disk") else stat.FILE_ATTRIBUTE_NORMAL)
        )

        result = stat_result(
            (
                mode,
                0,
                0,
                0,
                0,
                0,
                int(file_size, 10),
                last_accessed,
                last_modified,
                creation_date,
            ),
            {
                "st_file_attributes": st_file_attributes,
                "st_atime_ns": last_accessed_ns,
                "st_mtime_ns": last_modified_ns,
                "st_ctime_ns": creation_date_ns,
            },
        )

        return path, result

    # TODO: rewrite stat for optimization and correct file links management
    def _stat(self, path, *, dir_fd=None, follow_symlinks=True):
        _path = self.myrrh_os.f(path, dir_fd=dir_fd)
        _path = self.abspath(_path)

        if _path == "\\\\.\\nul":
            return stat_result(8192, 0, 0, 0, 0, 0, 0, 0, 0, 0)

        if self.ismount(_path):
            out, err, rval = self.myrrh_os.cmd('%(dir)s /o:d /b "%(path)s"', path=self.myrrh_os.sh_escape(_path))
            ExecutionFailureCauseRVal(self, err, rval, _path, 0).check()
            ExecutionFailureCauseErr(self, err, "").check()
            if out == "":
                return stat_result((0, 0, 0, 0, 0, 0, 0, 0, 0, 0), {})
            _path = self.myrrh_os.joinpath(_path, out.split(self.myrrh_os.sepb)[0])  # get first

        out, err, rval = self.myrrh_os.cmd(
            'if EXIST "%(path)s\\" ( %(wmic)s fsdir where "name=\'%(wmicpath)s\'" get %(property)s /value ) else if EXIST "%(path)s" ( %(wmic)s datafile where "name=\'%(wmicpath)s\'" get %(property)s /value ) else exit 2',
            path=self.myrrh_os.sh_escape(_path),
            wmicpath=self.myrrh_os.sh_escape(_path).replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"'),
            property=self._stat_property,
        )

        ExecutionFailureCauseRVal(self, err, rval, 0, path, errno=rval).check()
        ExecutionFailureCauseErr(self, err, "").check()

        _, result = self._stat_out_to_struct(out)
        return result

    def _lstat(self, path, *, dir_fd=None):
        return self.stat(path, dir_fd=dir_fd, follow_symlinks=False)

    def _statvfs(self, path):
        _path = self.myrrh_os.f(path)
        _path = self.abspath(_path)

        drive = self.splitdrive(_path)

        out, err, rval = self.myrrh_os.cmd("%(wmic)s volume where driveletter='%(drive)s' get /value", drive=drive[0])
        ExecutionFailureCauseRVal(self, err, rval, 0, _path).check()
        ExecutionFailureCauseErr(self, err, "").check()

        _stat = {a[0]: str2int(a[1], -1) for a in (line.split("=") for line in out.split("\r\n")) if len(a) == 2}

        block_sz = _stat["BlockSize"]
        blocks = _stat["Capacity"] / block_sz
        bfree = _stat["FreeSpace"] / block_sz
        namemax = _stat["MaximumFileNameLength"]

        return OsFs.statvfs_result(block_sz, block_sz, blocks, bfree, bfree, -1, -1, -1, -1, namemax)

    def realpath(self, path):
        path = self.myrrh_os.p(path)
        path = self.myrrh_os.normpath(path)

        dirname = self.myrrh_os.dirname(path)
        basename = self.myrrh_os.basename(path)

        out, err, rval = self.myrrh_os.cmd(
            '%(cd)s /D "%(dirname)s" && FOR %%f in (%(basename)s) do @%(echo)s %%~ff ',
            dirname="." if len(dirname) == 0 else dirname,
            basename=basename,
        )
        ExecutionFailureCauseRVal(self, err, rval, 0, path).check()

        return out

    def expanduser(self, path):
        path = self.myrrh_os._fspath_(path)
        if not path.startswith("~"):
            return path
        i, n = 1, len(path)
        while i < n and path[i] not in self._get_bothseps(path):
            i += 1

        if "HOME" in os.environ:
            userhome = os.environ["HOME"]
        elif "USERPROFILE" in os.environ:
            userhome = os.environ["USERPROFILE"]
        elif "HOMEPATH" not in os.environ:
            return path
        else:
            try:
                drive = os.environ["HOMEDRIVE"]
            except KeyError:
                drive = ""
            userhome = self.myrrh_os.joinpath(drive, os.environ["HOMEPATH"])

        if i != 1:  # ~user
            userhome = self.myrrh_os._joinpath__(self.myrrh_os.__m_dirname_(userhome), path[1:i])

        return userhome + path[i:]

    def replace(self, src, dst, *args, src_dir_fd=None, dst_dir_fd=None):
        self.rename(src, dst, *args, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    def _utime(self, path, times=None, *, ns=None, dir_fd=None, follow_symlinks=True):
        _path = self.myrrh_os.f(path, dir_fd=dir_fd)

        if times is None and ns is None:
            _, err, rval = self.myrrh_os.cmd('%(copy)s /b "%(path)s"+,,', path=self.myrrh_os.sh_escape(_path))
        else:
            atime, mtime = times or (t * 1e-9 for t in ns)
            atime, mtime = time.gmtime(atime + self._epochdelta), time.gmtime(mtime + self._epochdelta)
            atime = "%i/%i/%i %i:%i:%i" % (
                atime.tm_year,
                atime.tm_mon,
                atime.tm_mday,
                atime.tm_hour,
                atime.tm_min,
                atime.tm_sec,
            )
            mtime = "%i/%i/%i %i:%i:%i" % (
                mtime.tm_year,
                mtime.tm_mon,
                mtime.tm_mday,
                mtime.tm_hour,
                mtime.tm_min,
                mtime.tm_sec,
            )

            _, err, rval = self.myrrh_os.cmd(
                "%(powershell)s set-itemproperty '%(path)s' -name LastAccessTime -Value '%(atime)s' ",
                atime=atime,
                path=self.myrrh_os.sh_escape(_path),
            )
            ExecutionFailureCauseRVal(self, err, rval, 0, path).check()
            _, err, rval = self.myrrh_os.cmd(
                "%(powershell)s set-itemproperty '%(path)s' -name LastWriteTime -Value '%(mtime)s' ",
                mtime=mtime,
                path=self.myrrh_os.sh_escape(_path),
            )

        ExecutionFailureCauseRVal(self, err, rval, 0, path).check()

    def link(self, src, dst, *, src_dir_fd=None, dst_dir_fd=None, follow_symlinks=True):
        _src = self.myrrh_os.p(src, dir_fd=src_dir_fd)
        _dst = self.myrrh_os.p(dst, dir_fd=dst_dir_fd)

        _, err, rval = self.myrrh_os.cmd(
            '%(mklink)s "%(dst)s" "%(src)s"',
            dst=self.myrrh_os.sh_escape(_dst),
            src=self.myrrh_os.sh_escape(_src),
        )
        ExecutionFailureCauseRVal(self, err, rval, 0, src).check()

    def umask(self, mask):
        return 0o000 & mask

    def truncate(self, path, length):
        from myrrh.framework.mpython import _mosfile

        mf = _mlib_(_mosfile)(self)
        fd = mf.dup(path) if (isinstance(path, int)) else mf.open(path, mf.O_APPEND)
        try:
            mf.ftruncate(fd, length)
        finally:
            mf.close(fd)

    def samefile(self, path1, path2):
        return self.normcase(self.abspath(path1)) == self.normcase(self.abspath(path2))

    @property
    def environ(self):
        return self.myrrh_os.getenv()
