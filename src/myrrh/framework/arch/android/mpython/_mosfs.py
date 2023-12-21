import errno
import stat
import time
import os
from myrrh.core.services.system import ExecutionFailureCauseRVal, MOsError, supportedif

from myrrh.framework.mpython._mosfs import AbcOsFs, stat_result
import posixpath

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


class OsFs(AbcOsFs):
    normcase = staticmethod(posixpath.normcase)
    splitdrive = staticmethod(posixpath.splitdrive)
    split = staticmethod(posixpath.split)
    samestat = staticmethod(posixpath.samestat)

    _umask = 0o022
    _epochdelta = 3600 if os.name == "nt" else 0

    def link(self, src, dst, *, src_dir_fd=None, dst_dir_fd=None, follow_symlinks=True):
        _src = self.myrrh_os.p(src, dir_fd=src_dir_fd)
        _dst = self.myrrh_os.p(dst, dir_fd=dst_dir_fd)

        _, err, rval = self.myrrh_os.cmd(
            b"%(ln)s %(follow)s %(src)s %(dst)s",
            follow=b"" if follow_symlinks else b"-n",
            src=self.myrrh_os.sh_escape_bytes(_src),
            dst=self.myrrh_os.sh_escape_bytes(_dst),
        )
        ExecutionFailureCauseRVal(self, err, rval, 0, src, error_translate=self._os.default_errno_from_msg).check()

    def chown(self, path, uid, gid, *, dir_fd=None, follow_symlinks=True, _trusted=False):
        _path = self.myrrh_os.p(path, dir_fd=dir_fd)

        if not isinstance(uid, int):
            raise TypeError("invalid user type")
        if not isinstance(gid, int):
            raise TypeError("invalid group type")

        if uid == -1 and gid == -1:
            return

        exe = b"%(chown)s" if uid != -1 else b"%(chgrp)s"
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
        ExecutionFailureCauseRVal(self, err, rval, 0, path, error_translate=self._os.default_errno_from_msg).check()

    def chmod(self, path, mode, *, dir_fd=None, follow_symlinks=True, _trusted=False):
        # follow_symlinks is ignore
        _path = self.myrrh_os.p(path, dir_fd=dir_fd)
        mode = stat.S_IMODE(mode)
        _, err, rval = self.myrrh_os.cmdb(
            b"%(chmod)s %(mode)o %(path)s",
            mode=mode,
            path=self.myrrh_os.sh_escape_bytes(_path),
        )
        ExecutionFailureCauseRVal(self, err, rval, 0, path, error_translate=self._os.default_errno_from_msg).check()

    def rename(self, src, dst, *, src_dir_fd=None, dst_dir_fd=None):
        _src = self.myrrh_os.p(src, dir_fd=src_dir_fd)
        _dst = self.myrrh_os.p(dst, dir_fd=dst_dir_fd)

        _, err, rval = self.myrrh_os.cmdb(
            b"%(mv)s %(src)s %(dst)s",
            src=self.myrrh_os.sh_escape_bytes(_src),
            dst=self.myrrh_os.sh_escape_bytes(_dst),
        )
        ExecutionFailureCauseRVal(self, err, rval, 0, src, error_translate=self._os.default_errno_from_msg).check()

    def replace(self, src, dst, *args, src_dir_fd=None, dst_dir_fd=None):
        self.rename(src, dst, *args, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    def listdir(self, path="."):
        _cast_ = self.myrrh_os.fdcast(path)
        _path = self.myrrh_os.f(path)

        if not self.isdir(path):
            if not self.exists(path):
                MOsError(self, errno.ENOENT, "No such file or directory", args=(path,)).raised()
            MOsError(self, errno.ENOTDIR, "Not a directory", args=(path,)).raised()

        paths = self.myrrh_os.fs.list(_path)

        return [self.myrrh_os.basename(_cast_(f.strip())) for f, _ in paths]

    def _scandir_list(self, path="."):
        _cast_ = self.myrrh_os.fdcast(path)
        _path = self.myrrh_os.p(path)

        files = self.myrrh_os.fs.list(_path)

        result = []
        for file, idx in files:
            if files.readable(idx) or files.writeable(idx) or files.executable(idx):
                fname = self.myrrh_os.basename(file)
                fpath = self.join(_path, fname)
                result.append(self.DirEntry(_cast_(fname), _cast_(fpath), self._stat(fpath), self.lstat))

        return result

    def _stat(self, path, *, dir_fd=None, follow_symlinks=True):
        _path = self.myrrh_os.f(path, dir_fd=dir_fd)
        try:
            stat = self.myrrh_os.fs.stat(_path)
        except OSError as err:
            err.filename = path
            raise err

        return stat_result(**stat._asdict())

    def _lstat(self, path, *, dir_fd=None):
        return self._stat(path, dir_fd=dir_fd, follow_symlinks=False)

    @supportedif(lambda self: b"statvfs" in self.myrrh_os.getbinb, "need statvfs tool")
    def _statvfs(self, path):
        _path = self.myrrh_os.f(path)

        command = b" if [ -e %(path)s ] ; then %(stat)s -f -c %%s,%%S,%%b,%%f,%%a,%%c,%%d,%%d,-1,%%l  %(path)s; else ls %(path)s; fi"
        out, err, rval = self.myrrh_os.cmdb(command, path=self.myrrh_os.sh_escape_bytes(_path))
        ExecutionFailureCauseRVal(self, err, rval, 0, path, error_translate=self._os.default_errno_from_msg).check()

        return _statvfs_out_to_struct(out)

    def realpath(self, path):
        _cast_ = self.myrrh_os.fdcast(path)
        path = self.myrrh_os.p(path)

        out, err, rval = self.myrrh_os.cmdb(b"%(realpath)s %(path)s", path=self.myrrh_os.sh_escape_bytes(path))
        ExecutionFailureCauseRVal(self, err, rval, 0, error_translate=self._os.default_errno_from_msg).check()

        return _cast_(out.strip())

    def ismount(self, path):
        path = self.myrrh_os.p(path)
        # copy from posixpath
        if self.islink(path):
            # A symlink can never be a mount point
            return False
        try:
            s1 = self.lstat(path)
            s2 = self.lstat(self.join(path, self.myrrh_os.pardirb))
        except ExecutionFailureCauseRVal:
            return False  # It doesn't exist -- so not a mount point:-)
        dev1 = s1.st_dev
        dev2 = s2.st_dev
        if dev1 != dev2:
            return True  # path/.. on a different device as path
        ino1 = s1.st_ino
        ino2 = s2.st_ino
        if ino1 == ino2:
            return True  # path/.. is the same i-node as path
        return False

    def __utime_toolbox(self, bpath, times, follow_symlinks):
        if times is None:
            _, err, rval = self.myrrh_os.cmdb(
                b"%(touch)s %(symlink)s -a -m %(path)s",
                symlink="-l" if follow_symlinks else b"",
                path=self.myrrh_os.sh_escape_bytes(bpath),
            )

        else:
            atime, mtime = times
            atime = self.myrrh_os.shencode(time.strftime("%Y%m%d.%H%M%S", time.localtime(atime)))
            mtime = self.myrrh_os.shencode(time.strftime("%Y%m%d.%H%M%S", time.localtime(mtime)))

            _, err, rval = self.myrrh_os.cmdb(
                b"%(touch)s %(follow)s -a -t %(atime)s %(path)s && %(touch)s %(follow)s -m -t %(mtime)s %(path)s",
                follow=b"-l" if follow_symlinks else b"",
                atime=atime,
                mtime=mtime,
                path=self.myrrh_os.sh_escape_bytes(bpath),
            )
        return err, rval

    def __utime_toybox(self, bpath, times, follow_symlinks):
        if times is None:
            _, err, rval = self.myrrh_os.cmdb(
                b"%(touch)s %(follow)s -c -a %(path)s",
                follow=b"" if follow_symlinks else b"-h",
                path=self.myrrh_os.sh_escape_bytes(bpath),
            )

        else:
            atime, mtime = times
            atime = atime and self.myrrh_os.shencode(time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(atime)))
            mtime = mtime and self.myrrh_os.shencode(time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(mtime)))

            cmd = b" && ".join(
                filter(
                    None,
                    [
                        atime and b"%(touch)s %(follow)s -c -a -d %(atime)s %(path)s",
                        mtime and b"%(touch)s %(follow)s -m -d %(mtime)s %(path)s",
                    ],
                )
            )

            _, err, rval = self.myrrh_os.cmdb(
                cmd,
                follow=b"" if follow_symlinks else b"-h",
                atime=atime,
                mtime=mtime,
                path=self.myrrh_os.sh_escape_bytes(bpath),
            )
        return err, rval

    def _utime(self, path, times=None, *, ns=None, dir_fd=None, follow_symlinks=True):
        _path = self.myrrh_os.f(path, dir_fd=dir_fd)

        if times or ns:
            atime, mtime = times or (t * 1e-9 for t in ns)
            atime, mtime = (
                atime and atime + self._epochdelta,
                mtime and mtime + self._epochdelta,
            )

        if self.myrrh_os.getbinb[b"touch"].startswith(b"/system/bin/toolbox"):
            _utime_cmd = self.__utime_toolbox
        else:
            _utime_cmd = self.__utime_toybox

        err, rval = _utime_cmd(_path, (atime, mtime), follow_symlinks=follow_symlinks)

        ExecutionFailureCauseRVal(self, err, rval, 0, path, error_translate=self._os.default_errno_from_msg).check()

    def umask(self, mask):
        last_mask = self._umask
        self._umask = mask
        return last_mask

    def truncate(self, path, length):
        _path = self.myrrh_os.p(path)
        if length:
            _, err, rval = self.myrrh_os.cmdb(
                b"%(dd)s  bs=%(length)d count=1 skip=2 seek=1 of=%(path)s if=%(path)s\n",
                length=length,
                path=self.myrrh_os.sh_escape_bytes(_path),
            )
        else:
            _, err, rval = self.myrrh_os.cmdb(
                b'%(sh)s -c "exec 1>%(path)s"',
                path=self.myrrh_os.sh_escape_bytes(_path),
            )

        ExecutionFailureCauseRVal(self, err, rval, 0, path, error_translate=self._os.default_errno_from_msg).check()

    def samefile(self, path1, path2):
        stat1 = self.stat(path1)
        stat2 = self.stat(path2)

        return self.samestat(stat1, stat2) and (self.normcase(self.abspath(path1)) == self.normcase(self.abspath(path2)))
