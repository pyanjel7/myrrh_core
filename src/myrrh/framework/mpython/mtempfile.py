import typing

from myrrh.core.interfaces import abstractmethod, ABC
from myrrh.core.services.system import AbcRuntimeDelegate

from . import mbuiltins

__mlib__ = "AbcTempfile"


class _interface(ABC):
    import tempfile as local_tempfile

    @property
    @abstractmethod
    def NamedTemporaryFile(self):
        return self.local_tempfile.NamedTemporaryFile

    @property
    @abstractmethod
    def TemporaryFile(self):
        return self.local_tempfile.TemporaryFile

    @property
    @abstractmethod
    def SpooledTemporaryFile(self) -> local_tempfile.SpooledTemporaryFile:
        ...

    @property
    @abstractmethod
    def TemporaryDirectory(self) -> local_tempfile.TemporaryDirectory:
        ...

    @property
    @abstractmethod
    def TMP_MAX(self):
        return self.local_tempfile.TMP_MAX

    @property
    @abstractmethod
    def template(self) -> str:
        ...

    @property
    @abstractmethod
    def tempdir(self) -> str | None:
        ...

    @property
    @abstractmethod
    def _text_openflags(self) -> int:
        ...

    @property
    @abstractmethod
    def _bin_openflags(self) -> int:
        ...

    @property
    @abstractmethod
    def _RandomNameSequence(self):
        return self.local_tempfile._RandomNameSequence

    @property
    @abstractmethod
    def _TemporaryFileWrapper(self) -> local_tempfile._TemporaryFileWrapper:
        ...

    @abstractmethod
    def _candidate_tempdir_list(self) -> list:
        ...

    @abstractmethod
    def _get_candidate_names(self) -> list:
        ...

    @abstractmethod
    def _get_default_tempdir(self) -> typing.Any:
        ...

    @abstractmethod
    def _infer_return_type(*args) -> typing.Any:
        ...

    @abstractmethod
    def _mkstemp_inner(dir, pre, suf, flags, output_type) -> tuple[int, str]:
        ...

    @abstractmethod
    def mkstemp(self, suffix=None, prefix=None, dir=None, text=False) -> tuple[int, str]:
        ...

    @abstractmethod
    def mkdtemp(self, suffix=None, prefix=None, dir=None) -> str:
        ...

    @abstractmethod
    def mktemp(self, suffix="", prefix=template, dir=None) -> str:
        ...

    @abstractmethod
    def gettempprefix(self) -> bytes:
        ...

    @abstractmethod
    def gettempdir(self) -> str:
        ...

    @abstractmethod
    def gettempprefixb(self) -> bytes:
        ...

    @abstractmethod
    def gettempdirb(self) -> bytes:
        ...


class AbcTempfile(_interface, AbcRuntimeDelegate):
    __frameworkpath__ = "mpython.mtempfile"

    __all__ = _interface.local_tempfile.__all__

    __delegated__ = {_interface: _interface.local_tempfile}
    __delegate_check_type__ = False

    def __init__(self, *a, **kwa):
        mod = mbuiltins.wrap_module(self.local_tempfile, self)

        self.__delegate__(_interface, mod)
