from abc import abstractmethod
import errno
import stat

from myrrh.framework.mpython import mbuiltins

from myrrh.core.services.system import (
    ExecutionFailureCauseRVal,
    MOsError,
    AbcRuntimeDelegate,
)
from myrrh.core.interfaces import ABC

from myrrh.framework.mpython._mosfs import AbcOsFs, stat_result

__mlib__ = "OsFs"


def _stat_out_to_struct(out):
    stat_list = [int(v, 0) for v in out.strip().split(b",")]
    stat_list[-3] = float(stat_list[-3])
    stat_list[-2] = float(stat_list[-2])
    stat_list[-1] = float(stat_list[-1])
    return stat_result(
        stat_list,
        {
            "st_atime_ns": stat_list[-3] * 1000000000,
            "st_mtime_ns": stat_list[-2] * 1000000000,
            "st_ctime_ns": stat_list[-1] * 1000000000,
        },
    )


def _statvfs_out_to_struct(out):
    stat_list = [int(v, 0) for v in out.strip().split(b",")]
    return OsFs.statvfs_result(*stat_list)


class _interface(ABC):
    import posixpath as local_path

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
    def samestat(self, s1, s2):
        ...

    @abstractmethod
    def expandvars(self, path):
        ...


class OsFs(_interface, AbcOsFs, AbcRuntimeDelegate):
    _umask = 0o022

    __delegated__ = {_interface: _interface.local_path}
    __delegate_check_type__ = False

    def __init__(self, *a, **kwa):
        mod = mbuiltins.wrap_module(self.local_path, self, {"os": self})

        self.__delegate__(_interface, mod)

    def link(self, src, dst, *, src_dir_fd=None, dst_dir_fd=None, follow_symlinks=True):
        _src = self.myrrh_os.p(src, dir_fd=src_dir_fd)
        _dst = self.myrrh_os.p(dst, dir_fd=dst_dir_fd)

        _, err, rval = self.myrrh_os.cmd(
            b"%(ln)s %(follow)s %(src)s %(dst)s",
            follow=b"" if follow_symlinks else b"-n",
            src=self.myrrh_os.sh_escape_bytes(_src),
            dst=self.myrrh_os.sh_escape_bytes(_dst),
        )
        ExecutionFailureCauseRVal(
            self,
            err,
            rval,
            0,
            src,
            error_translate=self.myrrh_os.default_errno_from_msg,
        ).check()

    def chown(self, path, uid, gid, *, dir_fd=None, follow_symlinks=True, _trusted=False):
        _path = self.myrrh_os.p(path, dir_fd=dir_fd)

        if not isinstance(uid, int):
            raise TypeError("invalid user type")
        if not isinstance(gid, int):
            raise TypeError("invalid group type")

        if uid == -1 and gid == -1:
            return

        exe = b"%(chown)s" if (uid != -1) else b"%(chgrp)s"
        symlink = b"" if follow_symlinks else b"-h"
        user = b"'%i'" % uid if uid != -1 else b""
        group = b"'%i'" % gid if gid != -1 else b""

        _, err, rval = self.myrrh_os.cmdb(
            b"%s %s %s%s%s %s"
            % (
                exe,
                symlink,
                user,
                b":" if uid != -1 and gid != -1 else b"",
                group,
                self.myrrh_os.sh_escape_bytes(_path),
            )
        )
        ExecutionFailureCauseRVal(
            self,
            err,
            rval,
            0,
            path,
            error_translate=self.myrrh_os.default_errno_from_msg,
        ).check()

    def chmod(self, path, mode, *, dir_fd=None, follow_symlinks=True, _trusted=False):
        # follow_symlinks is ignore
        _path = self.myrrh_os.p(path, dir_fd=dir_fd)
        mode = stat.S_IMODE(mode)
        _, err, rval = self.myrrh_os.cmdb(
            b"%(chmod)s %(mode)o %(path)s",
            mode=mode,
            path=self.myrrh_os.sh_escape_bytes(_path),
        )
        ExecutionFailureCauseRVal(
            self,
            err,
            rval,
            0,
            path,
            error_translate=self.myrrh_os.default_errno_from_msg,
        ).check()

    def rename(self, src, dst, *, src_dir_fd=None, dst_dir_fd=None):
        _src = self.myrrh_os.p(src, dir_fd=src_dir_fd)
        _dst = self.myrrh_os.p(dst, dir_fd=dst_dir_fd)

        _, err, rval = self.myrrh_os.cmdb(
            b"%(mv)s %(src)s %(dst)s",
            src=self.myrrh_os.sh_escape_bytes(_src),
            dst=self.myrrh_os.sh_escape_bytes(_dst),
        )
        ExecutionFailureCauseRVal(
            self,
            err,
            rval,
            0,
            src,
            error_translate=self.myrrh_os.default_errno_from_msg,
        ).check()

    def replace(self, src, dst, *args, src_dir_fd=None, dst_dir_fd=None):
        self.rename(src, dst, *args, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    def listdir(self, path="."):
        _cast_ = self.myrrh_os.fdcast(path)
        _path = self.myrrh_os.f(path)

        if not self.isdir(path):
            if not self.exists(path):
                MOsError(self, errno.ENOENT, "No such file or directory", args=(path,)).raised()
            MOsError(self, errno.ENOTDIR, "Not a directory", args=(path,)).raised()
        out, err, rval = self.myrrh_os.cmdb(
            b"%(find)s %(path)s/ -maxdepth 1 -mindepth 1 ! -path %(path)s -perm /777 -print",
            path=self.myrrh_os.sh_escape_bytes(_path),
        )
        ExecutionFailureCauseRVal(
            self,
            err,
            rval,
            0,
            path,
            error_translate=self.myrrh_os.default_errno_from_msg,
        ).check()
        return [_cast_(self.myrrh_os.basename(f.strip())) for f in out.split(self.myrrh_os.linesepb) if len(f) != 0]

    def _scandir_list(self, path="."):
        _cast_ = self.myrrh_os.fdcast(path)
        _path = self.myrrh_os.p(path)
        command = b"%(find)s %(path)s -maxdepth 1 ! -path %(path)s -exec %(stat)s -L -c %%n,0x%%f,%%i,%%d,%%h,%%u,%%g,%%s,%%X,%%Y,%%Z {} \\; || %(stat)s -L -c %%n,0x%%f,%%i,%%d,%%h,%%u,%%g,%%s,%%X,%%Y,%%Z %(path)s"
        out, err, rval = self.myrrh_os.cmdb(command, path=self.myrrh_os.sh_escape_bytes(_path))
        ExecutionFailureCauseRVal(
            self,
            err,
            rval,
            0,
            path,
            error_translate=self.myrrh_os.default_errno_from_msg,
        ).check()

        result = []
        out = [o.split(b",", 1) for o in filter(None, out.split(b"\n"))]
        for name, fstat in out:
            fname = self.myrrh_os.basename(name)
            fpath = self.myrrh_os.joinpath(_path, fname)
            fstat = _stat_out_to_struct(fstat)
            fmode = stat.filemode(fstat.st_mode)
            if "r" in fmode or "w" in fmode or "x" in fmode:
                result.append(self.DirEntry(_cast_(fname), _cast_(fpath), fstat, self.lstat))

        return result

    def _stat(self, path, *, dir_fd=None, follow_symlinks=True):
        _path = self.myrrh_os.f(path, dir_fd=dir_fd)

        command = b"%(stat)s %(follow)s -c 0x%%f,%%i,%%d,%%h,%%u,%%g,%%s,%%X,%%Y,%%Z %(path)s"

        out, err, rval = self.myrrh_os.cmdb(
            command,
            follow=b"-L" if follow_symlinks else b"",
            path=self.myrrh_os.sh_escape_bytes(_path),
        )
        ExecutionFailureCauseRVal(
            self,
            err,
            rval,
            0,
            path,
            error_translate=self.myrrh_os.default_errno_from_msg,
        ).check()
        return _stat_out_to_struct(out)

    def _lstat(self, path, *, dir_fd=None):
        return self._stat(path, dir_fd=dir_fd, follow_symlinks=False)

    def _statvfs(self, path):
        _path = self.myrrh_os.f(path)

        command = b"%(stat)s -f -c %%s,%%S,%%b,%%f,%%a,%%c,%%d,%%d,-1,%%l %(path)s"
        out, err, rval = self.myrrh_os.cmdb(command, path=self.myrrh_os.sh_escape_bytes(_path))
        ExecutionFailureCauseRVal(
            self,
            err,
            rval,
            0,
            path,
            error_translate=self.myrrh_os.default_errno_from_msg,
        ).check()

        return _statvfs_out_to_struct(out)

    def realpath(self, path):
        _cast_ = self.myrrh_os.fdcast(path)
        path = self.myrrh_os.p(path)

        out, err, rval = self.myrrh_os.cmdb(b"%(realpath)s %(path)s", path=self.myrrh_os.sh_escape_bytes(path))
        ExecutionFailureCauseRVal(self, err, rval, 0, error_translate=self.myrrh_os.default_errno_from_msg).check()

        return _cast_(out.strip())

    def ismount(self, path):
        path = self.myrrh_os.p(path)
        # copy from posixpath
        if self.islink(path):
            # A symlink can never be a mount point
            return False
        try:
            s1 = self._lstat(path)
            s2 = self._lstat(self.myrrh_os.joinpath(path, self.myrrh_os.pardirb))
        except ExecutionFailureCauseRVal:
            return False  # It doesn't exist -- so not a mount point :-)
        dev1 = s1.st_dev
        dev2 = s2.st_dev
        if dev1 != dev2:
            return True  # path/.. on a different device as path
        ino1 = s1.st_ino
        ino2 = s2.st_ino
        if ino1 == ino2:
            return True  # path/.. is the same i-node as path
        return False

    def _utime(self, path, times=None, *, ns=None, dir_fd=None, follow_symlinks=True):
        _path = self.myrrh_os.f(path, dir_fd=dir_fd)

        if times is None and ns is None:
            _, err, rval = self.myrrh_os.cmdb(
                b"%(touch)s -c -a -m %(follow)s %(path)s",
                follow=b"-h" if follow_symlinks else b"",
                path=self.myrrh_os.sh_escape_bytes(_path),
            )

        else:
            atime, mtime = times or (t * 1e-9 for t in ns)
            _, err, rval = self.myrrh_os.cmdb(
                b"%(touch)s -c %(follow)s -a -d @%(atime)i %(path)s && %(touch)s -c %(follow)s -m -d @%(mtime)i %(path)s",
                follow=b"-h" if follow_symlinks else b"",
                atime=atime,
                mtime=mtime,
                path=self.myrrh_os.sh_escape_bytes(_path),
            )

        ExecutionFailureCauseRVal(
            self,
            err,
            rval,
            0,
            path,
            error_translate=self.myrrh_os.default_errno_from_msg,
        ).check()

    def umask(self, mask):
        last_mask = self._umask
        self._umask = mask
        return last_mask

    def truncate(self, path, length):
        _path = self.myrrh_os.p(path)
        _, err, rval = self.myrrh_os.cmdb(
            b"%(stat)s %(path)s > /dev/null && %(truncate)s -c -s %(length)i %(path)s",
            length=length,
            path=self.myrrh_os.sh_escape_bytes(_path),
        )
        ExecutionFailureCauseRVal(
            self,
            err,
            rval,
            0,
            path,
            error_translate=self.myrrh_os.default_errno_from_msg,
        ).check()

    def samefile(self, path1, path2):
        stat1 = self.stat(path1)
        stat2 = self.stat(path2)

        return self.samestat(stat1, stat2)

    @property
    def environ(self):
        return self.myrrh_os.getenv()
