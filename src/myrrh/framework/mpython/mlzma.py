import typing
import io

from myrrh.core.interfaces import abstractmethod, ABC
from myrrh.core.services.system import AbcRuntimeDelegate

from . import mbuiltins

__mlib__ = "AbcLzma"


class _interface(ABC):
    import lzma as local_lzma

    @property
    @abstractmethod
    def LZMACompressor(self) -> local_lzma.LZMACompressor:
        ...

    @property
    @abstractmethod
    def LZMADecompressor(self) -> local_lzma.LZMADecompressor:
        ...

    @property
    @abstractmethod
    def LZMAFile(self) -> local_lzma.LZMAFile:
        ...

    @property
    @abstractmethod
    def LZMAError(self) -> local_lzma.LZMAError:
        ...

    @property
    @abstractmethod
    def _MODE_CLOSED(self):
        return self.local_lzma._MODE_CLOSED

    @property
    @abstractmethod
    def _MODE_READ(self):
        return self.local_lzma._MODE_READ

    @property
    @abstractmethod
    def _MODE_WRITE(self):
        return self.local_lzma._MODE_WRITE

    @property
    @abstractmethod
    def CHECK_NONE(self):
        return self.local_lzma.CHECK_NONE

    @property
    @abstractmethod
    def CHECK_CRC32(self):
        return self.local_lzma.CHECK_CRC32

    @property
    @abstractmethod
    def CHECK_CRC64(self):
        return self.local_lzma.CHECK_CRC64

    @property
    @abstractmethod
    def CHECK_SHA256(self):
        return self.local_lzma.CHECK_SHA256

    @property
    @abstractmethod
    def CHECK_ID_MAX(self):
        return self.local_lzma.CHECK_ID_MAX

    @property
    @abstractmethod
    def CHECK_UNKNOWN(self):
        return self.local_lzma.CHECK_UNKNOWN

    @property
    @abstractmethod
    def FILTER_LZMA1(self):
        return self.local_lzma.FILTER_LZMA1

    @property
    @abstractmethod
    def FILTER_LZMA2(self):
        return self.local_lzma.FILTER_LZMA2

    @property
    @abstractmethod
    def FILTER_DELTA(self):
        return self.local_lzma.FILTER_DELTA

    @property
    @abstractmethod
    def FILTER_X86(self):
        return self.local_lzma.FILTER_X86

    @property
    @abstractmethod
    def FILTER_IA64(self):
        return self.local_lzma.FILTER_IA64

    @property
    @abstractmethod
    def FILTER_ARM(self):
        return self.local_lzma.FILTER_ARM

    @property
    @abstractmethod
    def FILTER_ARMTHUMB(self):
        return self.local_lzma.FILTER_ARMTHUMB

    @property
    @abstractmethod
    def FILTER_POWERPC(self):
        return self.local_lzma.FILTER_POWERPC

    @property
    @abstractmethod
    def FILTER_SPARC(self):
        return self.local_lzma.FILTER_SPARC

    @property
    @abstractmethod
    def FORMAT_AUTO(self):
        return self.local_lzma.FORMAT_AUTO

    @property
    @abstractmethod
    def FORMAT_XZ(self):
        return self.local_lzma.FORMAT_XZ

    @property
    @abstractmethod
    def FORMAT_ALONE(self):
        return self.local_lzma.FORMAT_ALONE

    @property
    @abstractmethod
    def FORMAT_RAW(self):
        return self.local_lzma.FORMAT_RAW

    @property
    @abstractmethod
    def MF_HC3(self):
        return self.local_lzma.MF_HC3

    @property
    @abstractmethod
    def MF_HC4(self):
        return self.local_lzma.MF_HC4

    @property
    @abstractmethod
    def MF_BT2(self):
        return self.local_lzma.MF_BT2

    @property
    @abstractmethod
    def MF_BT3(self):
        return self.local_lzma.MF_BT3

    @property
    @abstractmethod
    def MF_BT4(self):
        return self.local_lzma.MF_BT4

    @property
    @abstractmethod
    def MODE_FAST(self):
        return self.local_lzma.MODE_FAST

    @property
    @abstractmethod
    def MODE_NORMAL(self):
        return self.local_lzma.MODE_NORMAL

    @property
    @abstractmethod
    def PRESET_DEFAULT(self):
        return self.local_lzma.PRESET_DEFAULT

    @property
    @abstractmethod
    def PRESET_EXTREME(self):
        return self.local_lzma.PRESET_EXTREME

    @abstractmethod
    def open(self, filename, mode="rb", *, format=None, check=-1, preset=None, filters=None, encoding=None, errors=None, newline=None) -> io.TextIOWrapper | local_lzma.LZMAFile:
        ...

    @abstractmethod
    def compress(self, data, format=local_lzma.FORMAT_XZ, check=-1, preset=None, filters=None) -> typing.Any:
        ...

    @abstractmethod
    def decompress(self, data, format=local_lzma.FORMAT_AUTO, memlimit=None, filters=None) -> typing.Any:
        ...

    @abstractmethod
    def is_check_supported(self, check) -> bool:
        ...

    @abstractmethod
    def _decode_filter_properties(self, filter, data) -> typing.Any:
        ...

    @abstractmethod
    def _encode_filter_properties(self, filter, data) -> typing.Any:
        ...


class AbcLzma(_interface, AbcRuntimeDelegate):
    __frameworkpath__ = "mpython.mlzma"

    __all__ = [
        "CHECK_NONE",
        "CHECK_CRC32",
        "CHECK_CRC64",
        "CHECK_SHA256",
        "CHECK_ID_MAX",
        "CHECK_UNKNOWN",
        "FILTER_LZMA1",
        "FILTER_LZMA2",
        "FILTER_DELTA",
        "FILTER_X86",
        "FILTER_IA64",
        "FILTER_ARM",
        "FILTER_ARMTHUMB",
        "FILTER_POWERPC",
        "FILTER_SPARC",
        "FORMAT_AUTO",
        "FORMAT_XZ",
        "FORMAT_ALONE",
        "FORMAT_RAW",
        "MF_HC3",
        "MF_HC4",
        "MF_BT2",
        "MF_BT3",
        "MF_BT4",
        "MODE_FAST",
        "MODE_NORMAL",
        "PRESET_DEFAULT",
        "PRESET_EXTREME",
        "LZMACompressor",
        "LZMADecompressor",
        "LZMAFile",
        "LZMAError",
        "open",
        "compress",
        "decompress",
        "is_check_supported",
    ]

    __doc__ = _interface.local_lzma.__doc__

    __delegated__ = {_interface: _interface.local_lzma}
    __delegate_check_type__ = False

    def __init__(self, *a, **kwa):
        mod = mbuiltins.wrap_module(self.local_lzma, self)

        self.__delegate__(_interface, mod)
