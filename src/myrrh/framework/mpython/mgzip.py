from myrrh.core.interfaces import abstractmethod, ABC
from myrrh.core.services.system import AbcRuntimeDelegate

from . import mbuiltins

__mlib__ = "AbcGzip"


class _interface(ABC):
    import gzip as local_gzip

    @property
    @abstractmethod
    def BadGzipFile(self) -> local_gzip.BadGzipFile:
        ...

    @property
    @abstractmethod
    def GzipFile(self) -> local_gzip.GzipFile:
        ...

    @property
    @abstractmethod
    def _COMPRESS_LEVEL_BEST(self):
        return self.local_gzip._COMPRESS_LEVEL_BEST

    @property
    @abstractmethod
    def _COMPRESS_LEVEL_FAST(self):
        return self.local_gzip._COMPRESS_LEVEL_FAST

    @property
    @abstractmethod
    def _COMPRESS_LEVEL_TRADEOFF(self):
        return self.local_gzip._COMPRESS_LEVEL_TRADEOFF

    @property
    @abstractmethod
    def READ(self):
        return self.local_gzip.READ

    @property
    @abstractmethod
    def WRITE(self):
        return self.local_gzip.WRITE

    @property
    @abstractmethod
    def FTEXT(self):
        return self.local_gzip.FTEXT

    @property
    @abstractmethod
    def FHCRC(self):
        return self.local_gzip.FHCRC

    @property
    @abstractmethod
    def FEXTRA(self):
        return self.local_gzip.FEXTRA

    @property
    @abstractmethod
    def FNAME(self):
        return self.local_gzip.FNAME

    @property
    @abstractmethod
    def FCOMMENT(self):
        return self.local_gzip.FCOMMENT

    @abstractmethod
    def open(
        self,
        filename,
        mode="rb",
        compresslevel=_COMPRESS_LEVEL_BEST,
        encoding=None,
        errors=None,
        newline=None,
    ) -> local_gzip.GzipFile:
        ...

    @abstractmethod
    def compress(self, data, compresslevel=_COMPRESS_LEVEL_BEST, *, mtime=None) -> bytes:
        ...

    @abstractmethod
    def decompress(self, data) -> bytes:
        ...


class AbcGzip(_interface, AbcRuntimeDelegate):
    __frameworkpath__ = "mpython.mgzip"

    __all__ = ["BadGzipFile", "GzipFile", "open", "compress", "decompress"]

    __doc__ = _interface.local_gzip.__doc__

    __delegated__ = {_interface: _interface.local_gzip}
    __delegate_check_type__ = False

    def __init__(self, *a, **kwa):
        mod = mbuiltins.wrap_module(self.local_gzip, self)

        self.__delegate__(_interface, mod)
