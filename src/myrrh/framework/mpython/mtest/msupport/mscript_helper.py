import typing

from myrrh.core.interfaces import abstractmethod, ABC
from myrrh.core.services.system import AbcRuntimeDelegate

from myrrh.framework.mpython import mbuiltins

__mlib__ = "AbcScriptHelper"


class _interface(ABC):
    import test.support.script_helper as local_script_helper

    @abstractmethod
    def assert_python_ok(self, *args, **env_vars) -> typing.Any:
        ...

    @abstractmethod
    def assert_python_failure(self, *args, **env_vars) -> typing.Any:
        ...

    @abstractmethod
    def run_python_until_end(self, *args, **env_vars) -> typing.Any:
        ...


class AbcScriptHelper(_interface, AbcRuntimeDelegate):
    __frameworkpath__ = "mpython.mtest.msupport.mscript_helper"

    __delegated__ = {_interface: _interface.local_script_helper}
    __delegate_check_type__ = False

    def __init__(self, *a, **kwa):
        mod = mbuiltins.wrap_module(self.local_script_helper, self)
        self.__delegate__(_interface, mod)
