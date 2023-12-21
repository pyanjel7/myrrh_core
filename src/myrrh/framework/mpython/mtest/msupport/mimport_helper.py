from types import ModuleType

from myrrh.core.interfaces import abstractmethod, ABC
from myrrh.core.services.system import AbcRuntimeDelegate

from myrrh.framework.mpython import mbuiltins

__mlib__ = "AbcImportHelper"


class _interface(ABC):
    import test.support.import_helper as local_import_helper

    @abstractmethod
    def import_module(self, name, deprecated=False, *, required_on=()) -> ModuleType:
        ...

    @abstractmethod
    def make_legacy_pyc(self, name, deprecated=False, *, required_on=()) -> ModuleType:
        ...


class AbcImportHelper(_interface, AbcRuntimeDelegate):
    __frameworkpath__ = "mpython.mtest.msupport.mimport_helper"

    __delegated__ = {_interface: _interface.local_import_helper}
    __delegate_check_type__ = False

    def __init__(self, *a, **kwa):
        mod = mbuiltins.wrap_module(self.local_import_helper, self)
        mod.make_legacy_pyc = self._unsupported

        self.__delegate__(_interface, mod)

    def _unsupported(self, *a, **kwa):
        raise NotImplementedError("not supported by myrrh")
