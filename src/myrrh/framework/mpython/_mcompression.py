from myrrh.core.interfaces import abstractmethod, ABC
from myrrh.core.services.system import AbcRuntimeDelegate

from . import mbuiltins

__mlib__ = "Abc_Compression"


class _interface(ABC):
    import _compression as local__compression

    @property
    @abstractmethod
    def BaseStream(self) -> local__compression.BaseStream:
        ...

    @property
    @abstractmethod
    def DecompressReader(self) -> local__compression.DecompressReader:
        ...

    @property
    @abstractmethod
    def BUFFER_SIZE(self):
        return self.local__compression.BUFFER_SIZE


class Abc_Compression(_interface, AbcRuntimeDelegate):
    __frameworkpath__ = "mpython._mcompression"

    __doc__ = _interface.local__compression.__doc__

    __delegated__ = {_interface: _interface.local__compression}
    __delegate_check_type__ = False

    def __init__(self, *a, **kwa):
        mod = mbuiltins.wrap_module(self.local__compression, self)

        self.__delegate__(_interface, mod)
