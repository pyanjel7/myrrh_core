import typing

from myrrh.core.interfaces import abstractmethod, ABC
from myrrh.core.services.system import AbcRuntimeDelegate

from . import mbuiltins

__mlib__ = "AbcTarFile"


class _interface(ABC):
    import tarfile as local_tarfile

    @property
    @abstractmethod
    def TarFile(self) -> local_tarfile.TarFile:
        ...

    @property
    @abstractmethod
    def TarInfo(self) -> local_tarfile.TarInfo:
        ...

    @property
    @abstractmethod
    def TarError(self) -> local_tarfile.TarError:
        ...

    @property
    @abstractmethod
    def ReadError(self) -> local_tarfile.ReadError:
        ...

    @property
    @abstractmethod
    def CompressionError(self) -> local_tarfile.CompressionError:
        ...

    @property
    @abstractmethod
    def StreamError(self) -> local_tarfile.StreamError:
        ...

    @property
    @abstractmethod
    def ExtractError(self) -> local_tarfile.ExtractError:
        ...

    @property
    @abstractmethod
    def HeaderError(self) -> local_tarfile.HeaderError:
        ...

    @property
    @abstractmethod
    def ENCODING(self):
        return self.local_tarfile.ENCODING

    @property
    @abstractmethod
    def USTAR_FORMAT(self):
        return self.local_tarfile.USTAR_FORMAT

    @property
    @abstractmethod
    def GNU_FORMAT(self):
        return self.local_tarfile.GNU_FORMAT

    @property
    @abstractmethod
    def PAX_FORMAT(self):
        return self.local_tarfile.PAX_FORMAT

    @property
    @abstractmethod
    def DEFAULT_FORMAT(self):
        return self.local_tarfile.DEFAULT_FORMAT

    @property
    @abstractmethod
    def RECORDSIZE(self):
        return self.local_tarfile.RECORDSIZE

    @property
    @abstractmethod
    def GNUTYPE_LONGNAME(self):
        return self.local_tarfile.GNUTYPE_LONGNAME

    @property
    @abstractmethod
    def XHDTYPE(self):
        return self.local_tarfile.XHDTYPE

    @property
    @abstractmethod
    def BLOCKSIZE(self):
        return self.local_tarfile.BLOCKSIZE

    @property
    @abstractmethod
    def DIRTYPE(self):
        return self.local_tarfile.DIRTYPE

    @property
    @abstractmethod
    def BLKTYPE(self):
        return self.local_tarfile.BLKTYPE

    @property
    @abstractmethod
    def REGTYPE(self):
        return self.local_tarfile.REGTYPE

    @property
    @abstractmethod
    def PAX_NUMBER_FIELDS(self):
        return self.local_tarfile.PAX_NUMBER_FIELDS

    @property
    @abstractmethod
    def LENGTH_NAME(self):
        return self.local_tarfile.LENGTH_NAME

    @property
    @abstractmethod
    def LNKTYPE(self):
        return self.local_tarfile.LNKTYPE

    @property
    @abstractmethod
    def LENGTH_LINK(self):
        return self.local_tarfile.LENGTH_LINK

    @abstractmethod
    def open(self, name=None, mode="r", fileobj=None, bufsize=RECORDSIZE, **kwargs) -> local_tarfile.TarFile:
        ...

    @abstractmethod
    def is_tarfile(self, name) -> bool:
        ...

    @abstractmethod
    def stn(s, length, encoding, errors) -> typing.Any:
        ...

    @abstractmethod
    def nts(s, encoding, errors) -> typing.Any:
        ...

    @abstractmethod
    def nti(s) -> typing.Any:
        ...

    @abstractmethod
    def itn(n, digits=8, format=DEFAULT_FORMAT) -> typing.Any:
        ...

    @abstractmethod
    def calc_chksums(buf) -> typing.Any:
        ...


class AbcTarFile(_interface, AbcRuntimeDelegate):
    __frameworkpath__ = "mpython.mtarfile"

    __all__ = _interface.local_tarfile.__all__

    __delegated__ = {_interface: _interface.local_tarfile}
    __delegate_check_type__ = False

    __name__ = _interface.local_tarfile.__name__

    def __init__(self, *a, **kwa):
        mod = mbuiltins.wrap_module(self.local_tarfile, self)

        self.__delegate__(_interface, mod)
