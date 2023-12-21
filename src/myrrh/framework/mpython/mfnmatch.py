"""Filename matching with shell patterns.

fnmatch(FILENAME, PATTERN) matches according to the local convention.
fnmatchcase(FILENAME, PATTERN) always takes case in account.

The functions operate by translating the pattern into a regular
expression.  They cache the compiled regular expressions for speed.

The function translate(PATTERN) returns a regular expression
corresponding to PATTERN.  (It does not compile it.)
"""
from myrrh.core.interfaces import abstractmethod, ABC
from myrrh.core.services.system import AbcRuntimeDelegate
from . import mbuiltins

__mlib__ = "AbcFnmatch"


class _interface(ABC):
    import fnmatch as local_fnmatch

    @abstractmethod
    def filter(self, names, pat) -> list:
        ...

    @abstractmethod
    def fnmatch(self, name, pat) -> bool:
        ...

    @abstractmethod
    def fnmatchcase(self, pathname) -> bool:
        ...

    @abstractmethod
    def translate(self, pathname) -> str:
        ...


class AbcFnmatch(_interface, AbcRuntimeDelegate):
    __frameworkpath__ = "mpython.mfnmatch"

    __all__ = ["filter", "fnmatch", "fnmatchcase", "translate"]

    __doc__ = _interface.local_fnmatch.__doc__

    __delegated__ = {_interface: _interface.local_fnmatch}
    __delegate_check_type__ = False

    def __init__(self, *a, **kwa):
        mod = mbuiltins.wrap_module(self.local_fnmatch, self)

        self.__delegate__(_interface, mod)
