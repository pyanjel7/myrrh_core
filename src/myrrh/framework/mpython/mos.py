import builtins

from myrrh.core.services.system import ImplPropertyClass, _mlib_, AbcRuntimeDelegate

from . import _mosenv, _mosfs, _mosfile, _mosprocess, mimportlib, msys
from myrrh.framework.mfs import madvfs


__mlib__ = "AbcOs"


class AbcOs(_mlib_(_mosenv), _mlib_(_mosfile), _mlib_(_mosfs), _mlib_(_mosprocess), AbcRuntimeDelegate):  # type: ignore[misc]
    __frameworkpath__ = "mpython.mos"

    __delegated__ = (
        _mlib_(_mosenv),
        _mlib_(_mosfile),
        _mlib_(_mosfs),
        _mlib_(_mosprocess),
    )

    import os as local_os
    import stat as st

    from myrrh.core.services.system import MOsError
    from ._mosfs import stat_result

    osenv = mimportlib.module_property(_mosenv)
    osfs = mimportlib.module_property(_mosfs)
    osfile = mimportlib.module_property(_mosfile)
    osprocess = mimportlib.module_property(_mosprocess)
    sys = mimportlib.module_property(msys)

    advfs = mimportlib.module_property(madvfs)

    def __init__(self, system=None):
        self.__delegate__(_mlib_(_mosenv), self.osenv)
        self.__delegate__(_mlib_(_mosfs), self.osfs)
        self.__delegate__(_mlib_(_mosfile), self.osfile)
        self.__delegate__(_mlib_(_mosprocess), self.osprocess)

        self.__all__ = self.osenv.__all__

        self.PathLike = self.local_os.PathLike

        self.path = self.osfs
        self.sys.modules["os.path"] = self.path

        if hasattr(self.osenv, "uname"):
            self.uname = self.osenv.uname

        self.supports_bytes_environ = self.name != "nt"
        self.__all__.extend(["supports_bytes_environ"])

        self.__all__.extend(["path", "fsencode", "fsdecode", "scandir"])

        # complete os API
        self.error = self.MOsError
        self.__all__.extend(["error"])

        # local forward
        self.strerror = self.local_os.strerror
        self.local_os.File = builtins.open

        # file object creation
        self.File = self.FileObject

        self.__all__.append("fdopen")
        # os.popen
        # os.tempfile
        # os.popen2
        # os.popen3
        # os.popen4

        self.__all__.extend(
            [
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
                "SEEK_SET",
                "SEEK_CUR",
                "SEEK_END",
                "open",
                "read",
                "write",
                "set_inheritable",
                "get_inheritable",
                "O_RDONLY",
                "O_WRONLY",
                "O_RDWR",
                "O_APPEND",
                "O_CREAT",
                "O_TRUNC",
                "O_EXCL",
            ]
        )

        # file management
        self.__all__.extend(
            [
                "access",
                "R_OK",
                "X_OK",
                "W_OK",
                "F_OK",
                "chdir",
                "getcwd",
                "chmod",
                "chown",
                "listdir",
                "mkdir",
                "makedirs",
                "remove",
                "removedirs",
                "rename",
                "replace",
                "rmdir",
                "stat",
                "lstat",
                "stat_result",
                "unlink",
                "walk",
                "utime",
            ]
        )

        # process management
        self.__all__.extend(
            [
                "P_NOWAIT",
                "P_WAIT",
                "SIGABRT",
                "SIGFPE",
                "SIGILL",
                "SIGINT",
                "SIGSEGV",
                "SIGTERM",
                "WNOHANG",
                "WIFSTOPPED",
                "WSIGTERM",
                "kill",
                "spawnl",
                "spawnle",
                "spawnv",
                "spawnve",
                "system",
                "waitpid",
                "waitstatus_to_exitcode",
                "popen",
            ]
        )

        # miscellaneous system information
        self.__all__.extend(
            [
                "altsep",
                "curdir",
                "pardir",
                "sep",
                "extsep",
                "pathsep",
                "defpath",
                "devnull",
            ]
        )

        # local_os wrapper
        self.getpid = self.local_os.getpid
        self.__all__.append("getpid")

        _set = set()
        _set.add("access")
        _set.add("chmod")
        _set.add("chown")
        _set.add("stat")
        _set.add("utime")
        _set.add("link")
        _set.add("mkdir")
        _set.add("mkfifo")
        _set.add("mknod")
        _set.add("open")
        _set.add("readlink")
        _set.add("rename")
        _set.add("symlink")
        _set.add("unlink")
        _set.add("rmdir")
        _set.add("utime")
        self.supports_dir_fd = _set

        _set = set()
        _set.add("access")
        self.supports_effective_ids = _set

        _set = set()
        _set.add("chdir")
        _set.add("chmod")
        _set.add("chown")
        _set.add("listdir")
        _set.add("execve")
        _set.add("stat")  # fstat always works
        _set.add("lstat")
        _set.add("truncate")
        _set.add("utime")
        _set.add("utime")
        _set.add("pathconf")
        self.supports_fd = _set

        _set = set()
        _set.add("access")

        _set.add("chmod")
        _set.add("chown")
        _set.add("stat")
        _set.add("chflags")
        _set.add("chmod")
        _set.add("link")
        _set.add("utime")
        _set.add("stat")
        _set.add("utime")
        self.supports_follow_symlinks = _set

        del _set

    def _fwalk(self, top=".", topdown=True, onerror=None, *, follow_symlinks=False, dir_fd=None):
        fspath = self.myrrh_os._fspath_
        open = self.open
        O_RDONLY = self.O_RDONLY
        _fwalk = self.__fwalk
        st = self.st
        stat = self.stat
        close = self.close
        path = self.path

        if not isinstance(top, int) or not hasattr(top, "__index__"):
            top = fspath(top)
        # Note: To guard against symlink races, we use the standard
        # lstat()/open()/fstat() trick.
        orig_st = stat(top, follow_symlinks=False, dir_fd=dir_fd)
        topfd = open(top, O_RDONLY, dir_fd=dir_fd)
        try:
            if follow_symlinks or (st.S_ISDIR(orig_st.st_mode) and path.samestat(orig_st, stat(topfd))):
                yield from _fwalk(topfd, top, topdown, onerror, follow_symlinks)
        finally:
            close(topfd)

    def __fwalk(self, topfd, toppath, topdown, onerror, follow_symlinks):
        # Note: This uses O(depth of the directory tree) file descriptors: if
        # necessary, it can be adapted to only require O(1) FDs, see issue
        # #13734.
        listdir = self.listdir
        st = self.st
        stat = self.stat
        O_RDONLY = self.O_RDONLY
        path = self.path
        close = self.close
        names = listdir(topfd)
        dirs, nondirs = [], []
        open = self.open
        for name in names:
            try:
                # Here, we don't use AT_SYMLINK_NOFOLLOW to be consistent with
                # walk() which reports symlinks to directories as directories.
                # We do however check for symlinks before recursing into
                # a subdirectory.
                if st.S_ISDIR(stat(name, dir_fd=topfd).st_mode):
                    dirs.append(name)
                else:
                    nondirs.append(name)
            except OSError:
                try:
                    # Add dangling symlinks, ignore disappeared files
                    if st.S_ISLNK(stat(name, dir_fd=topfd, follow_symlinks=False).st_mode):
                        nondirs.append(name)
                except OSError:
                    continue

        if topdown:
            yield toppath, dirs, nondirs, topfd

        for name in dirs:
            try:
                orig_st = stat(name, dir_fd=topfd, follow_symlinks=follow_symlinks)
                dirfd = open(name, O_RDONLY, dir_fd=topfd)
            except OSError as err:
                if onerror is not None:
                    onerror(err)
                continue
            try:
                if follow_symlinks or path.samestat(orig_st, stat(dirfd)):
                    dirpath = path.join(toppath, name)
                    yield from self.__fwalk(dirfd, dirpath, topdown, onerror, follow_symlinks)
            finally:
                close(dirfd)

        if not topdown:
            yield toppath, dirs, nondirs, topfd

    class FileObject(metaclass=ImplPropertyClass):
        def __new__(self, *a, **kwa):
            import mlib

            with mlib.mlib_select(self.__rself__):
                from mlib.py import io
            return io.open(*a, **kwa)

    def fdopen(self, fd, mode="r", buffering=-1):
        return self.FileObject(fd, mode=mode, buffering=buffering)

    def popen(self, cmd, mode="r", buffering=-1):
        import mlib

        with mlib.mlib_select(self):
            from mlib.py import io
            from mlib.py import subprocess

        _wrap_close = self._wrap_close

        if not isinstance(cmd, str):
            raise TypeError("invalid cmd type (%s, expected string)" % type(cmd))
        if mode not in ("r", "w"):
            raise ValueError("invalid mode %r" % mode)
        if buffering == 0 or buffering is None:
            raise ValueError("popen() does not support unbuffered streams")

        if mode == "r":
            proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, bufsize=buffering)
            return _wrap_close(io.TextIOWrapper(proc.stdout), proc)
        else:
            proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, bufsize=buffering)
            return _wrap_close(io.TextIOWrapper(proc.stdin), proc)
