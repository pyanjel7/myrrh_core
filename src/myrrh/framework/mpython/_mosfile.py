import errno
import array
import os

from myrrh.core.services.system import MIOException, AbcRuntime

from . import mimportlib

__mlib__ = "AbcOsFile"


class AbcOsFile(AbcRuntime):
    __frameworkpath__ = "mpython._mosfile"

    __all__ = [
        "SEEK_SET",
        "SEEK_CUR",
        "SEEK_END",
        "O_RDONLY",
        "O_WRONLY",
        "O_BINARY" "O_RDWR",
        "O_APPEND",
        "O_CREAT",
        "O_TRUNC",
        "O_EXCL",
        "fdopen",
        "close",
        "closerange",
        "dup",
        "dup2",
        "fchmod",
        "fchown",
        "fdatasync",
        "fstat",
        "fsync",
        "ftruncate",
        "isatty",
        "lseek",
        "open",
        "read",
        "write",
        "set_inheritable",
        "get_inheritable",
    ]

    _BUFFER_SZ = 8192

    from os import O_WRONLY, O_RDWR, O_APPEND, O_CREAT, O_TRUNC, O_EXCL, O_RDONLY

    try:
        from os import O_BINARY
    except ImportError:
        pass

    O_TEMPORARY = 64

    osfs = mimportlib.module_property("_osfs")

    def _fs_stream(self, fd):
        return self.myrrh_syscall.gethandle(fd, True)

    def close(self, fd):
        return self.myrrh_syscall.close(fd)

    def closerange(self, fd_low, fd_high):
        for fd in range(fd_low, fd_high):
            try:
                self.close(fd)
            except OSError:
                pass

    def dup(self, fd):
        return self.myrrh_syscall.dup(fd)

    def dup2(self, fd, fd2, inheritable=True):
        return self.myrrh_syscall.dup2(fd, fd2)

    def fchmod(self, fd, mode):
        return self.osfs.chmod(self._fs_stream(fd).path, mode)

    def fchown(self, fd, uid, gid):
        return self.osfs.chown(self._fs_stream(fd).path, uid, gid)

    def fdatasync(self, fd):
        return self.fsync(fd)

    def fstat(self, fd):
        handle = self._fs_stream(fd)
        try:
            stat = handle.stat()
        except NotImplementedError:
            stat = self.osfs.stat(handle.path)

        stat = os.stat_result(
            (
                stat.st_mode,
                stat.st_ino,
                stat.st_dev,
                stat.st_nlink,
                stat.st_uid,
                stat.st_gid,
                stat.st_size,
                stat.st_atime,
                stat.st_mtime,
                stat.st_ctime,
            )
            + (0,) * (os.stat_result.n_fields - 10)
        )
        return stat

    def fsync(self, fd):
        try:
            return self._fs_stream(fd).sync()
        except (IOError, OSError):
            raise
        except Exception as e:
            MIOException(self, exc=e).raised()

    def ftruncate(self, fd, length):
        try:
            return self._fs_stream(fd).truncate(length)
        except (IOError, OSError):
            raise
        except Exception as e:
            MIOException(self, exc=e).raised()

    def isatty(self, fd):
        return False

    def lseek(self, fd, pos, how):
        try:
            return self._fs_stream(fd).seek(pos, how)

        except (IOError, OSError, OverflowError, ValueError):
            raise
        except Exception as e:
            MIOException(self, exc=e).raised()

    def open(self, path, flags, mode=0o777, *, dir_fd=None) -> int:
        file = self.myrrh_os.p(path, dir_fd=dir_fd)

        if b"\0" in file:
            raise ValueError("embedded null character")

        mode = mode & ~self.osfs._umask
        abspath = self.myrrh_os.getpathb(file)

        if b"\x00" in abspath:
            raise ValueError("embedded null byte")

        # check file
        if (self.O_CREAT & flags) == 0:
            if not self.osfs.exists(abspath):
                MIOException(self, errno.ENOENT, filename=path).raised()
        else:
            if (self.O_EXCL & flags) != 0:
                if self.osfs.exists(abspath):
                    MIOException(self, errno.EEXIST, filename=path).raised()

        wiring = self.myrrh_syscall.Wiring.OFF
        if flags & self.O_RDWR:
            wiring |= self.myrrh_syscall.Wiring.INOUT
        if flags & self.O_WRONLY:
            wiring |= self.myrrh_syscall.Wiring.OUT
        else:
            wiring |= self.myrrh_syscall.Wiring.IN

        if not flags & self.O_APPEND:
            wiring |= self.myrrh_syscall.Wiring.RESET

        if flags & self.O_CREAT:
            wiring |= self.myrrh_syscall.Wiring.CREATE

        try:
            hint = self.myrrh_syscall.open_file(abspath, wiring, extras={"mode": mode, "flags": flags})
        except (IOError, OSError) as e:
            MIOException(self, errno=e.errno, filename=path, exc=e).raised()
        except Exception as e:
            MIOException(self, exc=e, filename=path).raised()

        return hint

    def read(self, fd, n):
        try:
            return self._fs_stream(fd).read(n)
        except (IOError, OSError):
            raise
        except Exception as e:
            MIOException(self, exc=e).raised()

    def write(self, fd, str):
        if isinstance(str, memoryview):
            str = str.tobytes()

        if isinstance(str, (bytearray, array.array)):
            str = bytes(str)

        if not isinstance(str, bytes):
            raise TypeError("a bytes-like object is required, not 'str'")

        try:
            return self._fs_stream(fd).write(str)
        except (IOError, OSError):
            raise
        except Exception as e:
            MIOException(self, exc=e).raised()

    # stub
    def set_inheritable(self, fd, inheritable):
        self._fs_stream(fd)

    def get_inheritable(self, fd):
        self._fs_stream(fd)
        return False
