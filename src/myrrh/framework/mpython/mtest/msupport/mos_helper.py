import typing

from myrrh.core.interfaces import abstractmethod, ABC
from myrrh.core.services.system import AbcRuntimeDelegate

from myrrh.framework.mpython import mbuiltins

__mlib__ = "AbcOsHelper"


class _interface(ABC):
    import test.support.os_helper as local_os_helper

    @property
    @abstractmethod
    def EnvironmentVarGuard(self) -> local_os_helper.EnvironmentVarGuard:
        ...

    @property
    @abstractmethod
    def FakePath(self) -> local_os_helper.FakePath:
        ...

    @property
    @abstractmethod
    def TESTFN(self) -> str:
        ...

    @property
    @abstractmethod
    def TESTFN_ASCII(self) -> str:
        ...

    @abstractmethod
    def skip_if_dac_override(self, test) -> typing.Any:
        ...

    @abstractmethod
    def skip_unless_xattr(self, test) -> typing.Any:
        ...

    @abstractmethod
    def skip_unless_dac_override(self, test) -> typing.Any:
        ...

    @abstractmethod
    def skip_unless_working_chmod(self, test) -> typing.Any:
        ...

    @abstractmethod
    def skip_unless_symlink(self, test) -> typing.Any:
        ...

    @abstractmethod
    def can_symlink(self, test) -> typing.Any:
        ...

    @abstractmethod
    def create_empty_file(self, filename) -> None:
        ...

    @abstractmethod
    def change_cwd(self, path, quiet: bool = ...) -> typing.ContextManager[str]:
        ...

    @abstractmethod
    def unlink(self, filename) -> None:
        ...

    @abstractmethod
    def make_bad_fd(self) -> int:
        ...

    @abstractmethod
    def rmtree(self, path) -> None:
        ...

    @abstractmethod
    def temp_dir(self, path=None, quiet=False) -> typing.Any:
        ...

    @abstractmethod
    def temp_cwd(self, name="tempcwd", quiet=False) -> typing.Any:
        ...

    @abstractmethod
    def rmdir(self, dirname) -> typing.Any:
        ...


class AbcOsHelper(_interface, AbcRuntimeDelegate):
    __frameworkpath__ = "mpython.mtest.msupport.mos_helper"

    __delegated__ = {_interface: _interface.local_os_helper}
    __delegate_check_type__ = False

    def __init__(self, *a, **kwa):
        mod = mbuiltins.wrap_module(self.local_os_helper, self)
        self.__delegate__(_interface, mod)

        # for test purpose
        self._mod = mod
