import os
import errno
import genericpath
import stat
import typing

import warnings
import functools

from os import PathLike
from collections import namedtuple


from myrrh.core.interfaces import abstractmethod
from myrrh.core.services.system import (
    MOsError,
    MIOException,
    AbcRuntime,
    ImplPropertyClass,
)

from . import mimportlib

__mlib__ = "AbcOsFs"

_stat_named_tuple_field_names = (
    "st_mode",
    "st_ino",
    "st_dev",
    "st_nlink",
    "st_uid",
    "st_gid",
    "st_size",
    "st_atime",
    "st_mtime",
    "st_ctime",
)
_stat_named_tuple_kfield_names = ("st_atime_ns", "st_ctime_ns", "st_mtime_ns")

StatNamedTuple = typing.NamedTuple(  # type: ignore[name-match]
    "stat_result",
    (
        ("st_mode", int),
        ("st_ino", int),
        ("st_dev", int),
        ("st_nlink", int),
        ("st_uid", int),
        ("st_gid", int),
        ("st_size", int),
        ("st_atime", int),
        ("st_mtime", int),
        ("st_ctime", int),
    ),
)


class stat_result(StatNamedTuple):
    def __new__(cls, *fields, **kfields):
        fields_extra = {}

        if len(fields) == 2:
            kfields = fields[1]
            fields = fields[0]

        for k, v in kfields.items():
            if k not in StatNamedTuple._fields:
                fields_extra[k] = v

        if fields:
            stat = super().__new__(cls, *fields[:10])

        elif kfields:
            stat = super().__new__(
                cls,
                **dict(
                    filter(
                        lambda item: item[0] in _stat_named_tuple_field_names,
                        kfields.items(),
                    )
                ),
            )

        for k, v in fields_extra.items():
            super().__setattr__(stat, k, v)

        return stat

    def __setattr__(self, k, v):
        raise AttributeError


statvfs_result = namedtuple(
    "statvfs_result",
    "f_bsize f_frsize f_blocks f_bfree f_bavail f_files f_ffree f_favail f_flag f_namemax",
)


class AbcOsFs(AbcRuntime):
    __frameworkpath__ = "mpython._mosfs"

    __all__ = [
        "mkdir",
        "rmdir",
        "makedirs",
        "unlink",
        "removedirs",
        "exits",
        "lexists",
        "isfile",
        "isdir",
        "islink",
        "getsize",
        "getmtime",
        "getatime",
        "getctime",
        "abspath",
        "expanduser",
        "relpath",
        "splitext",
        "walk",
        "access",
        "chdir",
        "getcwd",
        "listdir",
        "rename",
        "stat",
        "lstat",
        "chown",
        "chmod",
        "normcase",
        "isabs",
        "join",
        "splitdrice",
        "split",
        "basename",
        "dirname",
        "ismount",
        "normpath",
        "realpath",
        "utime",
        "curdir",
        "pardir",
        "extsep",
        "sep",
        "pathsep",
        "altsep",
        "defpath",
        "devnull",
        "scandir",
    ]

    default_mode = -1

    statvfs_result = statvfs_result

    from os import R_OK, X_OK, W_OK, F_OK

    from genericpath import commonprefix  # type: ignore[misc]

    commonprefix = staticmethod(commonprefix)

    @property
    def altsep(self):
        return self.myrrh_os.fsdecode(self.myrrh_os.altsepb)

    @property
    def curdir(self):
        return self.myrrh_os.fsdecode(self.myrrh_os.curdirb)

    @property
    def pardir(self):
        return self.myrrh_os.fsdecode(self.myrrh_os.pardirb)

    @property
    def sep(self):
        return self.myrrh_os.fsdecode(self.myrrh_os.sepb)

    @property
    def extsep(self):
        return self.myrrh_os.fsdecode(self.myrrh_os.extsepb)

    @property
    def pathsep(self):
        return self.myrrh_os.fsdecode(self.myrrh_os.pathsepb)

    @property
    def defpath(self):
        return self.myrrh_os.fsdecode(self.myrrh_os.defpathb)

    @defpath.setter
    def defpath(self, value):
        self.myrrh_os.defpathb = self.myrrh_os.fsencode(value)

    @property
    def devnull(self):
        return self.myrrh_os.fsdecode(self.myrrh_os.devnullb)

    def fspath(self, *a, **kwa):
        return self.myrrh_os._fspath_(*a, **kwa)

    class DirEntry(PathLike):
        __path__: str | None = None

        def __fspath__(self):
            return self.__path__

        @functools.cached_property
        def __lstat__(self):
            return self.lstat(self.__path__)

        def __stat__(self, follow_symlinks=True):
            return self.__fstat__ if follow_symlinks else self.__lstat__

        def __init__(self, name, fspath, stat, lstatmethod):
            self.__name__ = name
            self.__path__ = fspath
            self.__fstat__ = stat
            self.lstat = lstatmethod

        def __repr__(self):
            if isinstance(self.__name__, bytes):
                return b"<DirEntry '%s'>" % self.__name__
            return "<DirEntry '%s'>" % self.__name__

        @property
        def name(self):
            return self.__name__

        @property
        def path(self):
            return self.__path__

        def inode(self):
            return self.__fstat__.st_ino

        def is_dir(self, *, follow_symlinks=True):
            return stat.S_ISDIR(self.__stat__(follow_symlinks).st_mode)

        def is_file(self, *, follow_symlinks=True):
            return stat.S_ISREG(self.__stat__(follow_symlinks).st_mode)

        def is_symlink(self):
            try:
                return stat.S_ISLNK(self.__lstat__.st_mode)
            except FileNotFoundError:
                pass

            return False

        def stat(self, *, follow_symlinks=True):
            return self.__stat__(follow_symlinks)

    _os = mimportlib.module_property("_osenv")

    def mkdir(self, path, mode=0o777):
        path = self.myrrh_os.p(path)

        if path.endswith((self.myrrh_os.sepb, b"/")):
            path = path[:-1]

        if self.myrrh_os.fs.exist(path):
            MOsError(self, errno=errno.EEXIST, args=(path,)).raised()

        dirname = self.dirname(path)

        if dirname != b"" and not self.isdir(dirname):
            MOsError(self, errno=errno.ENOENT, args=(dirname,)).raised()

        try:
            self.myrrh_os.fs.mkdir(path)
        except Exception as e:
            MIOException(self, strerror="operation failed", exc=e, filename=path).raised()

        self.chmod(path, mode, _trusted=True)

    def rmdir(self, path):
        _path = self.myrrh_os.p(path)
        try:
            self.myrrh_os.fs.rmdir(_path)
        except UnicodeDecodeError:
            raise
        except Exception as e:
            if not self.isdir(path):
                MOsError(self, errno.ENOTDIR, "Not a directory", args=(path,)).raised()

            MIOException(self, strerror="operation failed", exc=e, filename=path).raised()

    def makedirs(self, path, mode=0o777, exist_ok=False):
        path = self.myrrh_os.p(path)

        if not exist_ok and self.myrrh_os.fs.exist(path):
            MOsError(self, errno=errno.EEXIST).raised()
        try:
            self.myrrh_os.fs.mkdir(path)
        except Exception as e:
            MIOException(self, strerror="operation failed", exc=e, filename=path).raised()

        try:
            self.chmod(path, mode, _trusted=True)
        except PermissionError:
            pass

    def unlink(self, path, *, dir_fd=None):
        return self.remove(path, dir_fd=dir_fd)

    def remove(self, path, *, dir_fd=None):
        _path = self.myrrh_os.p(path, dir_fd=dir_fd)
        try:
            self.myrrh_os.fs.rm(_path)
        except UnicodeDecodeError:
            raise
        except Exception as e:
            MIOException(self, strerror="operation failed", exc=e, filename=path).raised()

    def removedirs(self, name):
        try:
            rmdir = self.myrrh_os.fs.rmdir
            path = self
            rmdir(self.myrrh_os.p(name))
            head, tail = path.split(name)
            if not tail:
                head, tail = path.split(head)
            while head and tail:
                try:
                    rmdir(self.myrrh_os.p(head))
                except Exception:
                    break
                head, tail = path.split(head)
        except Exception as e:
            MIOException(self, strerror="operation failed", exc=e, filename=path).raised()

    def exists(self, path):
        path = self.myrrh_os.p(path)
        return len(path) != 0 and self.myrrh_os.fs.exist(path)

    def lexists(self, path):
        try:
            self.lstat(path)
        except (MOsError, FileNotFoundError):
            return False

        return True

    def isfile(self, path):
        path = self.myrrh_os.p(path)

        if len(path) == 0 or not self.myrrh_os.fs.exist(path):
            return False

        try:
            st = self.stat(path)
        except (MOsError, FileNotFoundError):
            return False

        return stat.S_ISREG(st.st_mode)

    def isdir(self, path):
        path = self.myrrh_os.p(path)

        if len(path) == 0 or not self.myrrh_os.fs.exist(path):
            return False

        isdir = self.myrrh_os.fs.is_container(path)

        if not isdir:
            try:
                st = self.stat(path)
            except (MOsError, FileNotFoundError):
                return False

            isdir = stat.S_ISDIR(st.st_mode)

        return isdir

    def islink(self, path):
        try:
            st = self.lstat(path)
        except (MOsError, FileNotFoundError):
            return False
        return stat.S_ISLNK(st.st_mode)

    def getsize(self, filename):
        filename = self.myrrh_os.p(filename)
        return self.stat(filename).st_size

    def getmtime(self, filename):
        filename = self.myrrh_os.p(filename)
        return self.stat(filename).st_mtime

    def getatime(self, filename):
        filename = self.myrrh_os.p(filename)
        return self.stat(filename).st_atime

    def getctime(self, filename):
        filename = self.myrrh_os.p(filename)
        return self.stat(filename).st_ctime

    def abspath(self, path):
        _cast_ = self.myrrh_os.fdcast(path)
        return _cast_(self.myrrh_os.getpathb(path))

    def expanduser(self, path):
        _cast_ = self.myrrh_os.fdcast(path)
        _path = self.myrrh_os.p(path)
        if not _path.startswith(b"~"):
            return path
        home = self.myrrh_os.p(self._os.gethome())
        _path = _path[2:] if _path.startswith(b"~/") else _path[1:]
        return _cast_(self.join(home, _path))

    @abstractmethod
    def expandvars(self, path):
        ...

    def relpath(self, path, start=None):
        _cast_ = self.myrrh_os.fdcast(path)
        path = self.myrrh_os.p(path)
        start = self.myrrh_os.p(start)
        sep = self.myrrh_os.sepb
        pardir = self.myrrh_os.pardirb
        curdir = self.myrrh_os.curdirb

        if start is None:
            start = curdir

        if not path:
            raise ValueError("no path specified")

        start_list = [x for x in self.abspath(start).split(sep) if x]
        path_list = [x for x in self.abspath(path).split(sep) if x]

        i = len(self.commonprefix([start_list, path_list]))

        rel_list = [pardir] * (len(start_list) - i) + path_list[i:]
        if not rel_list:
            return _cast_(curdir)

        return _cast_(self.join(*rel_list))

    def splitext(self, path):
        _cast_ = self.myrrh_os.fdcast(path)
        return genericpath._splitext(
            path,
            _cast_(self.myrrh_os.sepb),
            _cast_(self.myrrh_os.altsepb),
            _cast_(self.myrrh_os.extsepb),
        )

    def access(self, path, mode):
        path = self.myrrh_os.p(path)
        mode |= self.F_OK  # unused warning disable

        try:
            st_r = self.stat(path)
        except MOsError:
            return False

        uid = self._os.geteuid()
        gids = self._os.getgroups()

        result = (
            (not ((mode & self.R_OK) == self.R_OK) or ((st_r.st_mode & stat.S_IRUSR) == stat.S_IRUSR and (st_r.st_uid == uid)) or ((st_r.st_mode & stat.S_IRGRP) == stat.S_IRGRP and (st_r.st_gid in gids)) or (st_r.st_mode & stat.S_IROTH) == stat.S_IROTH)
            and (not ((mode & self.W_OK) == self.W_OK) or ((st_r.st_mode & stat.S_IWUSR) == stat.S_IWUSR and (st_r.st_uid == uid)) or ((st_r.st_mode & stat.S_IWGRP) == stat.S_IWGRP and (st_r.st_uid in gids)) or (st_r.st_mode & stat.S_IWOTH) == stat.S_IWOTH)
            and (not ((mode & self.X_OK) == self.X_OK) or ((st_r.st_mode & stat.S_IXUSR) == stat.S_IXUSR and (st_r.st_uid == uid)) or ((st_r.st_mode & stat.S_IXGRP) == stat.S_IXGRP and (st_r.st_uid in gids)) or (st_r.st_mode & stat.S_IXOTH) == stat.S_IXOTH)
        )
        return result

    def chdir(self, path):
        _cast_ = self.myrrh_os.fdcast(path)
        bpath = self.myrrh_os.p(path)

        if self.isdir(bpath):
            self.myrrh_os.cwdb = self.abspath(bpath)
            return

        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), _cast_(path))

    def getcwd(self):
        return self.myrrh_os.fsdecode(self.myrrh_os.getpathb())

    def getcwdb(self):
        return self.myrrh_os.getpathb()

    @abstractmethod
    def link(self, src, dst, *, src_dir_fd=None, dst_dir_fd=None, follow_symlinks=True):
        ...

    def isabs(self, path):
        return self.myrrh_os.isabs(path)

    def join(self, *path):
        return self.myrrh_os.joinpath(*path)

    def fsencode(self, filename):
        filename = self.myrrh_os._fspath_(filename)

        _fsencoding = self.myrrh_os.fsencoding
        _fserrors = self.myrrh_os.fsencodeerrors

        if isinstance(filename, bytes):
            return filename
        elif isinstance(filename, (str,)):
            return filename.encode(_fsencoding, _fserrors)
        else:
            raise TypeError("expect bytes or str, not %s" % type(filename).__name__)

    def fsdecode(self, filename):
        filename = self.myrrh_os._fspath_(filename)

        _fsencoding = self.myrrh_os.fsencoding
        _fserrors = self.myrrh_os.fsencodeerrors

        if isinstance(filename, (str,)):
            return filename
        elif isinstance(filename, bytes):
            return filename.decode(_fsencoding, _fserrors)
        else:
            raise TypeError("expect bytes or str, not %s" % type(filename).__name__)

    def normpath(self, path):
        return self.myrrh_os.normpath(path)

    @abstractmethod
    def listdir(self, path="."):
        ...

    @abstractmethod
    def rename(self, src, dst):
        ...

    @abstractmethod
    def replace(self, src, dst, *, src_dir_fd=None, dst_dir_fd=None):
        ...

    @abstractmethod
    def _scandir_list(self, path="."):
        ...

    class scandir(metaclass=ImplPropertyClass):
        def __init__(self, path="."):
            if path == "":
                raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)

            self._entries = self._scandir_list(path)
            self._iter = iter(self._entries)

        def __enter__(self):
            return self

        def __exit__(self, type, value, traceback):
            pass

        def __iter__(self):
            return self

        def __next__(self):
            return next(self._iter)

        def close(self):
            if self._entries:
                del self._entries
            self._entries = None

    def stat_float_times(self, _):
        warnings.warn("stat_float_times deprecated => ignored", DeprecationWarning)

    @abstractmethod
    def _stat(self, path, *, dir_fd=None, follow_symlinks=True):
        pass

    def stat(self, path, *, dir_fd=None, follow_symlinks=True):
        _path = self.myrrh_os.f(path, dir_fd=dir_fd)

        if len(_path) == 0:
            MOsError(self, errno.ENOENT, os.strerror(errno.ENOENT), args=(path,)).raised()

        if not self.myrrh_os.fs.exist(_path):
            MOsError(self, errno.ENOENT, os.strerror(errno.ENOENT), args=(path,)).raised()

        return self._stat(path, follow_symlinks=follow_symlinks)

    def fstatvfs(self, fd):
        return self.statvfs(fd)

    @abstractmethod
    def _statvfs(self, path):
        pass

    def statvfs(self, path):
        _path = self.myrrh_os.f(path)

        if len(_path) == 0:
            MOsError(self, errno.ENOENT, os.strerror(errno.ENOENT), args=(path,)).raised()

        if not self.myrrh_os.fs.exist(_path):
            MOsError(self, errno.ENOENT, os.strerror(errno.ENOENT), args=(path,)).raised()

        return self._statvfs(path)

    @abstractmethod
    def _lstat(self, path, *, dir_fd=None):
        pass

    def lstat(self, path, *, dir_fd=None):
        _path = self.myrrh_os.f(path, dir_fd=dir_fd)

        if len(_path) == 0:
            MOsError(self, errno.ENOENT, os.strerror(errno.ENOENT), args=(path,)).raised()

        if not self.myrrh_os.fs.exist(_path):
            MOsError(self, errno.ENOENT, os.strerror(errno.ENOENT), args=(path,)).raised()

        return self._lstat(path, dir_fd=dir_fd)

    @abstractmethod
    def chown(self, path, uid, gid, *, dir_fd=None, follow_symlinks=True, _trusted=False):
        ...

    @abstractmethod
    def chmod(self, path, mode, *, dir_fd=None, follow_symlinks=True, _trusted=False):
        ...

    def lchmod(self, path, mode):
        return self.chmod(path, mode, follow_symlinks=False)

    @abstractmethod
    def normcase(self, path):
        ...

    @abstractmethod
    def splitdrive(self, path):
        ...

    @abstractmethod
    def split(self, path):
        ...

    def basename(self, path):
        return self.myrrh_os.basename(path)

    def dirname(self, path):
        return self.myrrh_os.dirname(path)

    @abstractmethod
    def ismount(self, path):
        ...

    @abstractmethod
    def realpath(self, path):
        ...

    @abstractmethod
    def _utime(self, path, times=None, *, ns=None, dir_fd=None, follow_symlinks=True):
        pass

    def utime(self, path, times=None, *, ns=None, dir_fd=None, follow_symlinks=True):
        if ns is not None and not (isinstance(ns, tuple) or len(ns) != 2):
            raise TypeError("utime: 'ns' must be a tuple of two ints")

        if times is not None and ns is not None:
            raise ValueError("utime: you may specify either 'times' or 'ns' but not both")

        self._utime(path, times=times, ns=ns, dir_fd=dir_fd, follow_symlinks=follow_symlinks)

    @abstractmethod
    def samefile(self, path1, path2):
        ...

    def sameopenfile(self, fp1, fp2):
        return self.samefile(self.myrrh_os.f(fp1), self.myrrh_os.f(fp2))

    @property
    @abstractmethod
    def _umask(self):
        ...

    @abstractmethod
    def umask(self, mask):
        ...

    @abstractmethod
    def truncate(self, path, length):
        ...

    # this function is distributed under the terms of PSF licence.
    # updated to work with myrrh API.
    # original version : see os module source code
    def walk(self, top, topdown=True, onerror=None, followlinks=False):
        scandir = self.scandir
        path = self
        walk = self.walk

        dirs = []
        nondirs = []
        walk_dirs = []

        try:
            top = self.myrrh_os._fspath_(top)
            scandir_it = scandir(top)
        except OSError as error:
            if onerror is not None:
                onerror(error)
            return

        with scandir_it:
            while True:
                try:
                    try:
                        entry = next(scandir_it)
                    except StopIteration:
                        break
                except OSError as error:
                    if onerror is not None:
                        onerror(error)
                    return

                try:
                    is_dir = entry.is_dir()
                except OSError:
                    # If is_dir() raises an OSError, consider that the entry is not
                    # a directory, same behaviour than os.path.isdir().
                    is_dir = False

                if is_dir:
                    dirs.append(entry.name)
                else:
                    nondirs.append(entry.name)

                if not topdown and is_dir:
                    # Bottom-up: recurse into sub-directory, but exclude symlinks to
                    # directories if followlinks is False
                    if followlinks:
                        walk_into = True
                    else:
                        try:
                            is_symlink = entry.is_symlink()
                        except OSError:
                            # If is_symlink() raises an OSError, consider that the
                            # entry is not a symbolic link, same behaviour than
                            # os.path.islink().
                            is_symlink = False
                        walk_into = not is_symlink

                    if walk_into:
                        walk_dirs.append(entry.path)

        # Yield before recursion if going top down
        if topdown:
            yield top, dirs, nondirs

            # Recurse into sub-directories
            islink, join = path.islink, path.join
            for dirname in dirs:
                new_path = join(top, dirname)
                # Issue #23605: os.path.islink() is used instead of caching
                # entry.is_symlink() result during the loop on os.scandir() because
                # the caller can replace the directory entry during the "yield"
                # above.
                if followlinks or not islink(new_path):
                    yield from walk(new_path, topdown, onerror, followlinks)
        else:
            # Recurse into sub-directories
            for new_path in walk_dirs:
                yield from walk(new_path, topdown, onerror, followlinks)
            # Yield after recursion if going bottom up
            yield top, dirs, nondirs
