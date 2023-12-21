import time
import stat
import os
import re
import sys
import calendar

from myrrh.utils.mstring import str2int

from myrrh.core.services.system import (
    ExecutionFailureCauseRVal,
    ExecutionFailureCauseErr,
    _mlib_,
)
from myrrh.core.interfaces import ABCDelegation, ABC, abstractmethod

from myrrh.framework.mpython import mbuiltins
from myrrh.framework.mpython._mosfs import AbcOsFs, stat_result

__mlib__ = "OsFs"


class _interface(ABC):
    import ntpath as local_path

    @abstractmethod
    def normcase(self, s):
        ...

    @abstractmethod
    def splitdrive(self, p):
        ...

    @abstractmethod
    def split(self, p):
        ...

    @abstractmethod
    def expandvars(self, path):
        ...

    @abstractmethod
    def _get_bothseps(self, path):
        ...


class OsFs(_interface, AbcOsFs, ABCDelegation):
    _umask = 0o000
    _epochdelta = 0 if sys.version_info >= (3, 6) else 3600
    _PATHEXT = {b".COM", b".EXE", b".BAT", b".CMD", b".VBS", b".JS", b".WS", b".MSC"}

    __delegated__ = {_interface: _interface.local_path}
    __delegate_check_type__ = False

    def __init__(self, *a, **kwa):
        mod = mbuiltins.wrap_module(self.local_path, self, {"os": self})

        self.__delegate__(_interface, mod)

    def ismount(self, mount):
        mount = self.myrrh_os.p(mount)
        return re.match(b"([a-zA-Z]:$)|(//.*)", mount) is not None

    def _wmidatetoiso(self, str):
        str = self.fsdecode(str)
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

        cmd, _dst = (b'%(rename)s "%(src)s" "%(dst)s"', self.myrrh_os.basename(_dst)) if samepath else (b'%(move)s /Y "%(src)s" "%(dst)s"', _dst)

        _, err, rval = self.myrrh_os.cmd(
            cmd,
            src=self.myrrh_os.sh_escape_bytes(_src),
            dst=self.myrrh_os.sh_escape_bytes(_dst),
        )

        ExecutionFailureCauseRVal(self, err, rval, 0, src).check()

    def listdir(self, path="."):
        _cast_ = self.myrrh_os.fdcast(path)
        path = self.myrrh_os.normpath(path)

        _path = self.myrrh_os.p(path)

        out, err, rval = self.myrrh_os.cmdb(
            b'if exist "%(path)s\\"  ( %(dir)s /B "%(path)s" ) else if exist "%(path)s" (exit 20) else ( exit 2 )',
            path=self.myrrh_os.sh_escape_bytes(_path),
        )

        ExecutionFailureCauseRVal(self, err, rval, 0, _cast_(path), errno=rval).check()
        return [_cast_(self.myrrh_os.shdecode(f)) for f in [f.strip() for f in out.split(self.myrrh_os.linesepb)] if f != self.myrrh_os.curdirb and f != self.myrrh_os.pardirb and len(f) != 0]

    def _scandir_list(self, path="."):
        # wmic output always in os encoding

        _cast_ = self.myrrh_os.fdcast(path)
        _path = self.myrrh_os.p(path)
        _abspath = self.abspath(_path)
        wmicpath = _abspath.replace(b"\\", b"\\\\").replace(b"'", b"\\'").replace(b'"', b'\\"')

        drive, wmicpath = self.splitdrive(wmicpath)
        wmicpath = b"" if wmicpath == b"\\\\" else wmicpath
        out, err, rval = self.myrrh_os.cmd(
            b"%(dir)s /B \"%(path)s\" && %(echo)s \"OOO___:__OOOO\" && %(wmic)s fsdir where \"path='%(wmicpath)s\\\\' and drive='%(drive)s'\" get %(property)s /value && %(wmic)s datafile where \"path='%(wmicpath)s\\\\' and drive='%(drive)s'\" get %(property)s /value",
            path=self.myrrh_os.sh_escape_bytes(_path),
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

        out_dir, out_wmi = out.split(b'"OOO___:__OOOO"', 1)
        real_file_name = {o.lower(): o for o in out_dir.split(b"\r\n")}

        # utf16 hack
        if b"\x00" in out_wmi:
            out_wmi = out_wmi.replace(b"\x00", b"")

        out_wmi = re.split(b"[\\r\\n]{4,}", out_wmi)

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
        return self._PATHEXT.union(p.upper() for p in (self.myrrh_os.getenvb().get(b"PATHEXT", b"").split(self.myrrh_os.pathsepb)))

    _stat_property = b"name,filesize,readable,writeable,filetype,creationdate,lastaccessed,lastmodified,archive,compressed,encrypted,hidden,system"

    def _stat_out_to_struct(self, out):
        if b"\x00" in out:
            out = out.lstrip().rstrip(b"\x00")
            out = self.myrrh_os.shencode(out.decode("utf-16-be"))

        out_stat = {a[0]: a[1].strip() for a in (line.split(b"=", 1) for line in out.split(b"\r\n")) if len(a) == 2}

        mode = stat.S_IFDIR if out_stat.get(b"FileType", b"") in (b"File Folder", b"Local Disk") else stat.S_IFREG
        path = out_stat.get(b"Name", b"myrrh_unexpected_error???????")
        # read GR
        if out_stat.get(b"Readable", b"TRUE") == b"TRUE":
            access_mask_win = stat.S_IRUSR
        if out_stat.get(b"Writeable", b"TRUE") == b"TRUE":
            access_mask_win += stat.S_IWUSR
        _, ext = self.splitext(path)
        if ext.upper() in self._pathext:
            access_mask_win += stat.S_IXUSR

        mode += (stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH) if (access_mask_win & stat.S_IRUSR) == stat.S_IRUSR or (access_mask_win & stat.S_IFDIR) == stat.S_IFDIR else 0
        mode += (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH) if (access_mask_win & stat.S_IWUSR) == stat.S_IWUSR or (access_mask_win & stat.S_IFDIR) == stat.S_IFDIR else 0
        mode += (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH) if (access_mask_win & stat.S_IXUSR) == stat.S_IXUSR or (mode & stat.S_IFDIR) == stat.S_IFDIR else 0

        file_size = out_stat.get(b"FileSize", b"")
        if file_size == b"":
            file_size = b"0"
        creation_date = out_stat.get(b"CreationDate", b"")
        if creation_date == b"":
            creation_date = b"19700101010000.000000+000"
        last_accessed = out_stat.get(b"LastAccessed", b"")
        if last_accessed == b"":
            last_accessed = creation_date
        last_modified = out_stat.get(b"LastModified", b"")
        if last_modified == b"":
            last_modified = creation_date

        def mktime(date):
            date = time.strptime(self._wmidatetoiso(date), "%Y%m%d%H%M%S.%f%z")
            date = calendar.timegm(date) - self._epochdelta
            return date, date * 1000000000

        creation_date, creation_date_ns = mktime(creation_date)
        last_accessed, last_accessed_ns = mktime(last_accessed)
        last_modified, last_modified_ns = mktime(last_modified)

        st_file_attributes = (
            (stat.FILE_ATTRIBUTE_ARCHIVE if out_stat.get(b"Archive", b"FALSE") == b"TRUE" else 0)
            | (stat.FILE_ATTRIBUTE_COMPRESSED if out_stat.get(b"Compressed", b"FALSE") == b"TRUE" else 0)
            | (stat.FILE_ATTRIBUTE_ENCRYPTED if out_stat.get(b"Encrypted", b"FALSE") == b"TRUE" else 0)
            | (stat.FILE_ATTRIBUTE_HIDDEN if out_stat.get(b"Hidden", b"FALSE") == b"TRUE" else 0)
            | (stat.FILE_ATTRIBUTE_READONLY if out_stat.get(b"Readable", b"FALSE") == b"TRUE" else 0)
            | (stat.FILE_ATTRIBUTE_SYSTEM if out_stat.get(b"System", b"FALSE") == b"TRUE" else 0)
            | (stat.FILE_ATTRIBUTE_DIRECTORY if out_stat.get(b"FileType", b"") in (b"File Folder", b"Local Disk") else stat.FILE_ATTRIBUTE_NORMAL)
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

        if _path == b"\\\\.\\nul":
            return stat_result(8192, 0, 0, 0, 0, 0, 0, 0, 0, 0)

        if self.ismount(_path):
            out, err, rval = self.myrrh_os.cmdb(b'%(dir)s /o:d /b "%(path)s"', path=self.myrrh_os.sh_escape_bytes(_path))
            ExecutionFailureCauseRVal(self, err, rval, _path, 0).check()
            ExecutionFailureCauseErr(self, err, "").check()
            if out == "":
                return stat_result((0, 0, 0, 0, 0, 0, 0, 0, 0, 0), {})
            _path = self.myrrh_os.joinpath(_path, out.split(self.myrrh_os.sepb)[0])  # get first

        out, err, rval = self.myrrh_os.cmdb(
            b'if EXIST "%(path)s\\" ( %(wmic)s fsdir where "name=\'%(wmicpath)s\'" get %(property)s /value ) else if EXIST "%(path)s" ( %(wmic)s datafile where "name=\'%(wmicpath)s\'" get %(property)s /value ) else exit 2',
            path=self.myrrh_os.sh_escape_bytes(_path),
            wmicpath=self.myrrh_os.sh_escape_bytes(_path).replace(b"\\", b"\\\\").replace(b"'", b"\\'").replace(b'"', b'\\"'),
            property=self._stat_property,
        )

        ExecutionFailureCauseRVal(self, err, rval, 0, path, errno=rval).check()
        ExecutionFailureCauseErr(self, err, b"").check()

        _, result = self._stat_out_to_struct(out)
        return result

    def _lstat(self, path, *, dir_fd=None):
        return self.stat(path, dir_fd=dir_fd, follow_symlinks=False)

    def _statvfs(self, path):
        _path = self.myrrh_os.f(path)
        _path = self.abspath(_path)

        drive = self.splitdrive(_path)

        out, err, rval = self.myrrh_os.cmdb(b"%(wmic)s volume where driveletter='%(drive)s' get /value", drive=drive[0])
        ExecutionFailureCauseRVal(self, err, rval, 0, _path).check()
        ExecutionFailureCauseErr(self, err, b"").check()

        _stat = {a[0]: str2int(a[1], -1) for a in (line.split(b"=") for line in out.split(b"\r\n")) if len(a) == 2}

        block_sz = _stat[b"BlockSize"]
        blocks = _stat[b"Capacity"] / block_sz
        bfree = _stat[b"FreeSpace"] / block_sz
        namemax = _stat[b"MaximumFileNameLength"]

        return OsFs.statvfs_result(block_sz, block_sz, blocks, bfree, bfree, -1, -1, -1, -1, namemax)

    def realpath(self, path):
        path = self.myrrh_os.p(path)
        path = self.myrrh_os.normpath(path)

        dirname = self.myrrh_os.dirname(path)
        basename = self.myrrh_os.basename(path)

        out, err, rval = self.myrrh_os.cmd(
            b'%(cd)s /D "%(dirname)s" && FOR %%f in (%(basename)s) do @%(echo)s %%~ff ',
            dirname=b"." if len(dirname) == 0 else dirname,
            basename=basename,
        )
        ExecutionFailureCauseRVal(self, err, rval, 0, path).check()

        return out

    def expanduser(self, path):
        path = self.myrrh_os._fspath_(path)
        if isinstance(path, bytes):
            tilde = b"~"
        else:
            tilde = "~"
        if not path.startswith(tilde):
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

        if isinstance(path, bytes):
            userhome = os.fsencode(userhome)

        if i != 1:  # ~user
            userhome = self.myrrh_os._joinpath__(self.myrrh_os.__m_dirname_(userhome), path[1:i])

        return userhome + path[i:]

    def replace(self, src, dst, *args, src_dir_fd=None, dst_dir_fd=None):
        self.rename(src, dst, *args, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    def _utime(self, path, times=None, *, ns=None, dir_fd=None, follow_symlinks=True):
        _path = self.myrrh_os.f(path, dir_fd=dir_fd)

        if times is None and ns is None:
            _, err, rval = self.myrrh_os.cmdb(b'%(copy)s /b "%(path)s"+,,', path=self.myrrh_os.sh_escape_bytes(_path))
        else:
            atime, mtime = times or (t * 1e-9 for t in ns)
            atime, mtime = time.gmtime(atime + self._epochdelta), time.gmtime(mtime + self._epochdelta)
            atime = b"%i/%i/%i %i:%i:%i" % (
                atime.tm_year,
                atime.tm_mon,
                atime.tm_mday,
                atime.tm_hour,
                atime.tm_min,
                atime.tm_sec,
            )
            mtime = b"%i/%i/%i %i:%i:%i" % (
                mtime.tm_year,
                mtime.tm_mon,
                mtime.tm_mday,
                mtime.tm_hour,
                mtime.tm_min,
                mtime.tm_sec,
            )

            _, err, rval = self.myrrh_os.cmdb(
                b"%(powershell)s set-itemproperty '%(path)s' -name LastAccessTime -Value '%(atime)s' ",
                atime=atime,
                path=self.myrrh_os.sh_escape_bytes(_path),
            )
            ExecutionFailureCauseRVal(self, err, rval, 0, path).check()
            _, err, rval = self.myrrh_os.cmdb(
                b"%(powershell)s set-itemproperty '%(path)s' -name LastWriteTime -Value '%(mtime)s' ",
                mtime=mtime,
                path=self.myrrh_os.sh_escape_bytes(_path),
            )

        ExecutionFailureCauseRVal(self, err, rval, 0, path).check()

    def link(self, src, dst, *, src_dir_fd=None, dst_dir_fd=None, follow_symlinks=True):
        _src = self.myrrh_os.p(src, dir_fd=src_dir_fd)
        _dst = self.myrrh_os.p(dst, dir_fd=dst_dir_fd)

        _, err, rval = self.myrrh_os.cmd(
            b'%(mklink)s "%(dst)s" "%(src)s"',
            dst=self.myrrh_os.sh_escape_bytes(_dst),
            src=self.myrrh_os.sh_escape_bytes(_src),
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
