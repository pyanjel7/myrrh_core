import typing

from myrrh.core.interfaces import abstractmethod, ABC
from myrrh.core.services.system import AbcRuntimeDelegate

from . import mbuiltins

__mlib__ = "AbcIo"


class io:
    import io

    RawIOBase = io.RawIOBase
    IOBase = io.IOBase
    BufferedIOBase = io.BufferedIOBase
    TextIOBase = io.TextIOBase

    __all__ = [
        "BlockingIOError",
        "open",
        "open_code",
        "IOBase",
        "RawIOBase",
        "FileIO",
        "BytesIO",
        "StringIO",
        "BufferedIOBase",
        "BufferedReader",
        "BufferedWriter",
        "BufferedRWPair",
        "BufferedRandom",
        "TextIOBase",
        "TextIOWrapper",
        "UnsupportedOperation",
        "SEEK_SET",
        "SEEK_CUR",
        "SEEK_END",
    ]

    SEEK_SET = io.SEEK_SET
    SEEK_CUR = io.SEEK_CUR
    SEEK_END = io.SEEK_END

    UnsupportedOperation = io.UnsupportedOperation


class msvcrt:
    setmode: None = None


class _interface(ABC):
    import _pyio as local_io

    @property
    @abstractmethod
    def IOBase(self) -> local_io.IOBase:
        ...

    @property
    @abstractmethod
    def RawIOBase(self) -> local_io.RawIOBase:
        ...

    @property
    @abstractmethod
    def FileIO(self) -> local_io.FileIO:
        ...

    @property
    @abstractmethod
    def BytesIO(self) -> local_io.BytesIO:
        ...

    @property
    @abstractmethod
    def StringIO(self) -> local_io.StringIO:
        ...

    @property
    @abstractmethod
    def BufferedIOBase(self) -> local_io.BufferedIOBase:
        ...

    @property
    @abstractmethod
    def BufferedReader(self) -> local_io.BufferedReader:
        ...

    @property
    @abstractmethod
    def BufferedWriter(self) -> local_io.BufferedWriter:
        ...

    @property
    @abstractmethod
    def BufferedRWPair(self) -> local_io.BufferedRWPair:
        ...

    @property
    @abstractmethod
    def BufferedRandom(self) -> local_io.BufferedRandom:
        ...

    @property
    @abstractmethod
    def TextIOBase(self) -> local_io.TextIOBase:
        ...

    @property
    @abstractmethod
    def TextIOWrapper(self) -> local_io.TextIOWrapper:
        ...

    @property
    @abstractmethod
    def UnsupportedOperation(self) -> local_io.UnsupportedOperation:
        ...

    @property
    @abstractmethod
    def IncrementalNewlineDecoder(self) -> local_io.IncrementalNewlineDecoder:
        ...

    @property
    @abstractmethod
    def BlockingIOError(self) -> local_io.BlockingIOError:
        ...

    @property
    @abstractmethod
    def SEEK_SET(self):
        return self.local_io.SEEK_SET

    @property
    @abstractmethod
    def SEEK_CUR(self):
        return self.local_io.SEEK_CUR

    @property
    @abstractmethod
    def SEEK_END(self):
        return self.local_io.SEEK_END

    @property
    @abstractmethod
    def DEFAULT_BUFFER_SIZE(self):
        return self.local_io.DEFAULT_BUFFER_SIZE

    @abstractmethod
    def open(
        self,
        file,
        mode="r",
        buffering=-1,
        encoding=None,
        errors=None,
        newline=None,
        closefd=True,
        opener=None,
    ) -> typing.Any:
        ...

    @abstractmethod
    def open_code(self, path: str):
        return self.local_io.open_code("")

    @abstractmethod
    def text_encoding(self, encoding, stacklevel=2) -> typing.Any | typing.Literal["utf-8", "locale"]:
        ...


class AbcIo(_interface, AbcRuntimeDelegate):
    __frameworkpath__ = "mpython.mio"

    __all__ = _interface.local_io.__all__

    __doc__ = _interface.local_io.__doc__

    __delegated__ = {_interface: _interface.local_io}
    __delegate_check_type__ = False

    def __init__(self, *a, **kwa):
        mod = mbuiltins.wrap_module(self.local_io, self, {"io": io, "msvcrt": msvcrt})

        _test_valid_size_type = list()
        BufferedReader = mod.BufferedReader

        class BufferedReaderFix(mod.BufferedReader):
            def read(self, size=None):
                _test_valid_size_type[size:]
                data = BufferedReader.read(self, size)
                return data

        mod.BufferedReader = BufferedReaderFix

        self.__delegate__(_interface, mod)
