import typing

from io import TextIOWrapper

from myrrh.core.interfaces import abstractmethod, ABC
from myrrh.core.services.system import AbcRuntimeDelegate

from . import mbuiltins

__mlib__ = "AbcBz2"


class _interface(ABC):
    import bz2 as local_bz2

    @property
    @abstractmethod
    def BZ2Compressor(self) -> local_bz2.BZ2Compressor:
        ...

    @property
    @abstractmethod
    def BZ2Decompressor(self) -> local_bz2.BZ2Decompressor:
        ...

    @property
    @abstractmethod
    def BZ2File(self) -> local_bz2.BZ2File:
        ...

    @property
    @abstractmethod
    def _MODE_CLOSED(self):
        return self.local_bz2._MODE_CLOSED

    @property
    @abstractmethod
    def _MODE_READ(self):
        return self.local_bz2._MODE_READ

    @property
    @abstractmethod
    def _MODE_WRITE(self):
        return self.local_bz2._MODE_WRITE

    @abstractmethod
    def open(
        self,
        filename,
        mode="rb",
        compresslevel=9,
        encoding=None,
        errors=None,
        newline=None,
    ) -> TextIOWrapper | local_bz2.BZ2File:
        ...

    @abstractmethod
    def compress(self, data, compresslevel=9) -> typing.Any:
        ...

    @abstractmethod
    def decompress(self, data) -> typing.Any:
        ...


class AbcBz2(_interface, AbcRuntimeDelegate):
    __frameworkpath__ = "mpython.mbz2"

    __all__ = [
        "BZ2File",
        "BZ2Compressor",
        "BZ2Decompressor",
        "open",
        "compress",
        "decompress",
    ]

    __doc__ = _interface.local_bz2.__doc__

    __delegated__ = {_interface: _interface.local_bz2}
    __delegate_check_type__ = False

    def __init__(self, *a, **kwa):
        mod = mbuiltins.wrap_module(self.local_bz2, self)

        self.__delegate__(_interface, mod)
