import typing

from myrrh.core.interfaces import abstractmethod, ABC
from myrrh.core.services.system import AbcRuntimeDelegate

from . import mbuiltins

__mlib__ = "AbcGlob"


class _interface(ABC):
    import glob as local_glob

    @abstractmethod
    def glob(self, pathname, *, root_dir=None, dir_fd=None, recursive=False, include_hidden=False) -> list[typing.AnyStr]:
        ...

    @abstractmethod
    def iglob(self, pathname, *, root_dir=None, dir_fd=None, recursive=False, include_hidden=False) -> typing.Iterator[typing.AnyStr]:
        ...

    @abstractmethod
    def has_magic(self, s) -> bool:
        ...

    @abstractmethod
    def escape(self, pathname) -> str:
        ...

    @abstractmethod
    def glob0(dirname, pattern) -> list:
        ...

    @abstractmethod
    def glob1(dirname, pattern) -> list:
        ...


class AbcGlob(_interface, AbcRuntimeDelegate):
    __frameworkpath__ = "mpython.mglob"

    __all__ = ["glob", "iglob", "escape"]

    __doc__ = _interface.local_glob.__doc__

    __delegated__ = {_interface: _interface.local_glob}
    __delegate_check_type__ = False

    def __init__(self, *a, **kwa):
        mod = mbuiltins.wrap_module(self.local_glob, self)

        self.__delegate__(_interface, mod)
