import os
import typing

from myrrh.core.interfaces import abstractmethod, ABC
from myrrh.core.services.system import AbcRuntimeDelegate

from . import mbuiltins
from . import mimportlib

__mlib__ = "AbcShutil"


class _interface(ABC):
    import shutil as local_shutil

    @property
    @abstractmethod
    def Error(self) -> local_shutil.Error:
        ...

    @property
    @abstractmethod
    def SpecialFileError(
        self,
    ) -> local_shutil.SpecialFileError:
        ...

    @property
    @abstractmethod
    def ReadError(self) -> local_shutil.ReadError:
        ...

    @property
    @abstractmethod
    def RegistryError(self) -> local_shutil.RegistryError:
        ...

    @property
    @abstractmethod
    def ExecError(self) -> local_shutil.ExecError:
        ...

    @property
    @abstractmethod
    def SameFileError(self) -> local_shutil.SameFileError:
        ...

    @property
    @abstractmethod
    def _GiveupOnFastCopy(self):
        return self.local_shutil._GiveupOnFastCopy

    @property
    @abstractmethod
    def _use_fd_functions(self):
        ...

    @property
    @abstractmethod
    def _ZLIB_SUPPORTED(self):
        ...

    @property
    @abstractmethod
    def _BZ2_SUPPORTED(self):
        ...

    @property
    @abstractmethod
    def _LZMA_SUPPORTED(self):
        ...

    @property
    @abstractmethod
    def _get_uid(self):
        ...

    @property
    @abstractmethod
    def _get_gid(self):
        ...

    @abstractmethod
    def copyfileobj(self, fsrc, fdst, length=0) -> None:
        ...

    @abstractmethod
    def copyfile(self, src, dst, *, follow_symlinks=True) -> typing.Any:
        ...

    @abstractmethod
    def copymode(self, src, dst, *, follow_symlinks=True) -> None:
        ...

    @abstractmethod
    def copystat(self, src, dst, *, follow_symlinks=True) -> None:
        ...

    @abstractmethod
    def copy(self, src, dst, *, follow_symlinks=True) -> typing.Any:
        ...

    @abstractmethod
    def copy2(self, src, dst, *, follow_symlinks=True) -> typing.Any:
        ...

    @abstractmethod
    def copytree(
        self,
        src,
        dst,
        symlinks=False,
        ignore=None,
        copy_function=copy2,
        ignore_dangling_symlinks=False,
        dirs_exist_ok=False,
    ) -> typing.Any:
        ...

    @abstractmethod
    def move(self, src, dst, copy_function=copy2) -> typing.Any:
        ...

    @abstractmethod
    def rmtree(self, path, ignore_errors=False, onerror=None, *, dir_fd=None) -> None:
        ...

    @abstractmethod
    def make_archive(
        self,
        base_name,
        format,
        root_dir=None,
        base_dir=None,
        verbose=0,
        dry_run=0,
        owner=None,
        group=None,
        logger=None,
    ) -> str:
        ...

    @abstractmethod
    def get_archive_formats(self) -> list[tuple[str, str]]:
        ...

    @abstractmethod
    def register_archive_format(
        self,
        name: str,
        function: typing.Callable[..., object],
        extra_args: typing.Sequence[tuple[str, typing.Any] | list],
        description: str = ...,
    ) -> None:
        ...

    @abstractmethod
    def unregister_archive_format(self, name: str) -> None:
        ...

    @abstractmethod
    def get_unpack_formats(self) -> list[tuple[str, list[str], str]]:
        ...

    @abstractmethod
    def register_unpack_format(
        self,
        name: str,
        extensions: list[str],
        function: typing.Callable[..., object],
        extra_args: typing.Sequence[tuple[str, typing.Any]],
        description: str = "",
    ) -> None:
        ...

    @abstractmethod
    def unregister_unpack_format(
        self,
        name: str,
        extensions: list[str],
        function: typing.Callable[..., object],
        extra_args: typing.Sequence[tuple[str, typing.Any]],
        description: str = ...,
    ) -> None:
        ...

    @abstractmethod
    def unpack_archive(self, filename, extract_dir=None, format=None) -> None:
        ...

    @abstractmethod
    def ignore_patterns(
        *patterns,
    ) -> typing.Callable[[typing.Any, list[str]], set[str]]:
        ...

    @abstractmethod
    def chown(self, path, user=None, group=None) -> None:
        ...

    @abstractmethod
    def which(self, cmd, mode=os.F_OK | os.X_OK, path=None) -> typing.Any:
        ...

    @abstractmethod
    def get_terminal_size(self, fallback=(80, 24)) -> os.terminal_size:
        ...

    # for test_shutil
    @abstractmethod
    def open(self):
        ...

    @abstractmethod
    def _copyfileobj_readinto(self):
        ...

    @abstractmethod
    def _destinsrc(self):
        ...


class AbcShutil(_interface, AbcRuntimeDelegate):
    __frameworkpath__ = "mpython.mshutil"

    __all__ = [
        "copyfileobj",
        "copyfile",
        "copymode",
        "copystat",
        "copy",
        "copy2",
        "copytree",
        "move",
        "rmtree",
        "Error",
        "SpecialFileError",
        "ExecError",
        "make_archive",
        "get_archive_formats",
        "register_archive_format",
        "unregister_archive_format",
        "get_unpack_formats",
        "register_unpack_format",
        "unregister_unpack_format",
        "unpack_archive",
        "ignore_patterns",
        "chown",
        "which",
        "get_terminal_size",
        "SameFileError",
        "disk_usage",
    ]

    os = mimportlib.module_property("os")

    __delegated__ = {_interface: _interface.local_shutil}
    __delegate_check_type__ = False

    def __init__(self, *a, **kwa):
        mod = mbuiltins.wrap_module(self.local_shutil, self)

        # tune module
        mod.disk_usage = self._myrrh_disk_usage

        mod._HAS_FCOPYFILE = False

        self.__delegate__(_interface, mod)

    def _myrrh_disk_usage(self, path):
        """Return disk usage statistics about the given path.

        Returned value is a named tuple with attributes 'total', 'used' and
        'free', which are the amount of total, used and free space, in bytes.
        """
        _ntuple_diskusage = self._ntuple_diskusage
        os = self.os

        st = os.statvfs(path)
        free = st.f_bavail * st.f_frsize
        total = st.f_blocks * st.f_frsize
        used = (st.f_blocks - st.f_bfree) * st.f_frsize
        return _ntuple_diskusage(total, used, free)

    def _myrrh__unpack_zipfile(self, filename, extract_dir):
        """Unpack zip `filename` to `extract_dir`"""
        raise NotImplementedError

    def _myrrh__make_zipfile(
        self,
        base_name,
        base_dir,
        verbose=0,
        dry_run=0,
        logger=None,
        owner=None,
        group=None,
        root_dir=None,
    ):
        """Create a zip file from all the files under 'base_dir'.

        The output zip file will be named 'base_name' + ".zip".  Returns the
        name of the output zip file.
        """
        raise NotImplementedError
