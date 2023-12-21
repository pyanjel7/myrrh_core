import typing
import decimal

from myrrh.core.interfaces import abstractmethod, ABC
from myrrh.core.services.system import AbcRuntimeDelegate

from . import mbuiltins

__mlib__ = "AbcLocale"


class _interface(ABC):
    import locale as local_locale

    from builtins import str as _builtins_str

    @property
    @abstractmethod
    def LC_CTYPE(self):
        return self.local_locale.LC_CTYPE

    @property
    @abstractmethod
    def LC_COLLATE(self):
        return self.local_locale.LC_COLLATE

    @property
    @abstractmethod
    def LC_TIME(self):
        return self.local_locale.LC_TIME

    @property
    @abstractmethod
    def LC_MONETARY(self):
        return self.local_locale.LC_MONETARY

    @property
    @abstractmethod
    def LC_NUMERIC(self):
        return self.local_locale.LC_NUMERIC

    @property
    @abstractmethod
    def LC_ALL(self):
        return self.local_locale.LC_ALL

    @property
    @abstractmethod
    def CHAR_MAX(self):
        return self.local_locale.CHAR_MAX

    @property
    @abstractmethod
    def Error(self) -> local_locale.Error:
        ...

    @property
    @abstractmethod
    def locale_alias(self) -> dict[_builtins_str, _builtins_str]:
        ...

    @abstractmethod
    def getlocale(self, category: int = ...) -> tuple[_builtins_str | None, _builtins_str | None]:
        ...

    @abstractmethod
    def getdefaultlocale(self, envvars: tuple[_builtins_str, ...] = ...) -> tuple[_builtins_str | None, _builtins_str | None]:
        ...

    @abstractmethod
    def getpreferredencoding(self, do_setlocale: bool = ...) -> _builtins_str:
        ...

    @abstractmethod
    def setlocale(self, do_setlocale: bool = ...) -> _builtins_str:
        ...

    @abstractmethod
    def resetlocale(self, category: int = ...) -> None:
        ...

    @abstractmethod
    def localeconv(
        self,
    ) -> typing.Mapping[_builtins_str, int | _builtins_str | list[int]]:
        ...

    @abstractmethod
    def strcoll(self, __os1: _builtins_str, __os2: _builtins_str, /) -> int:
        ...

    @abstractmethod
    def strxfrm(self, __string: _builtins_str, /) -> _builtins_str:
        ...

    @abstractmethod
    def str(self, val: float) -> _builtins_str:
        ...

    @abstractmethod
    def atof(self, string: _builtins_str, func: typing.Callable[[_builtins_str], float]) -> float:
        ...

    @abstractmethod
    def atoi(self, string: _builtins_str) -> int:
        ...

    @abstractmethod
    def format(
        self,
        percent: _builtins_str,
        value: float | decimal.Decimal,
        grouping: bool = ...,
        monetary: bool = ...,
        *additional: typing.Any,
    ):
        ...

    @abstractmethod
    def format_string(
        self,
        f: _builtins_str,
        val: typing.Any,
        grouping: bool = ...,
        monetary: bool = ...,
    ) -> _builtins_str:
        ...

    @abstractmethod
    def currency(
        self,
        val: int | float | decimal.Decimal,
        symbol: bool = ...,
        grouping: bool = ...,
        international: bool = ...,
    ) -> _builtins_str:
        ...

    @abstractmethod
    def normalize(self, localename: _builtins_str) -> _builtins_str:
        ...

    @abstractmethod
    def _localize(self):
        ...

    @abstractmethod
    def getencoding(self) -> _builtins_str:
        ...

    @abstractmethod
    def delocalize(self, string: _builtins_str) -> _builtins_str:
        ...

    @abstractmethod
    def _parse_localename(self):
        ...


class AbcLocale(_interface, AbcRuntimeDelegate):
    __frameworkpath__ = "mpython.mlocale"

    __all__ = [
        "getlocale",
        "getdefaultlocale",
        "getpreferredencoding",
        "Error",
        "setlocale",
        "resetlocale",
        "localeconv",
        "strcoll",
        "strxfrm",
        "_builtins_str",
        "atof",
        "atoi",
        "format",
        "format_string",
        "currency",
        "normalize",
        "LC_CTYPE",
        "LC_COLLATE",
        "LC_TIME",
        "LC_MONETARY",
        "LC_NUMERIC",
        "LC_ALL",
        "CHAR_MAX",
    ]

    __doc__ = _interface.local_locale.__doc__

    __delegated__ = {_interface: _interface.local_locale}
    __delegate_check_type__ = False

    def __init__(self, *a, **kwa):
        mod = mbuiltins.wrap_module(self.local_locale, self)

        self.__delegate__(_interface, mod)
