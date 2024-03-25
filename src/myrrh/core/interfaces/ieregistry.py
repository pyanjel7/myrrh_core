import abc
import typing
import pydantic.types
import datetime

from .ieservices import IEWarehouseService

__all__ = ["IERegistry", "IBaseItem", "IERegistrySupplier"]


class IBaseItem(abc.ABC):
    @property
    @abc.abstractmethod
    def DOM(self) -> pydantic.types.PastDatetime | None:
        return None

    @property
    @abc.abstractmethod
    def SLL(self) -> datetime.timedelta | None:
        return None

    @property
    @abc.abstractmethod
    def UBD(self) -> datetime.datetime | None:
        return None

    @property
    @abc.abstractmethod
    def UTC(self) -> bool | None:
        return None

    @abc.abstractmethod
    def now(self): ...

    @abc.abstractmethod
    def __bool__(self): ...


TAppendMode: typing.TypeAlias = typing.Literal["keep", "update", "replace"]


class IERegistry(dict, abc.ABC):
    @abc.abstractmethod
    def __getattr__(self, name) -> typing.Any: ...

    @abc.abstractmethod
    def predefined(self) -> list[typing.Any]: ...

    @abc.abstractmethod
    def defined_values(self) -> list[typing.Any]: ...

    @abc.abstractmethod
    def append(self, item: IBaseItem, mode: TAppendMode): ...

    @abc.abstractmethod
    def add_warehouse(self, serv: IEWarehouseService, *, index=None): ...

    @abc.abstractmethod
    def values(self) -> list[IBaseItem]: ...

    @abc.abstractmethod
    def get(self, path: str, default: IBaseItem): ...

    @abc.abstractmethod
    def get_static(self, path: str, default: typing.Any) -> typing.Any: ...

    @abc.abstractmethod
    def get_meta(self, key: str) -> typing.Any: ...

    @abc.abstractmethod
    def set(self, path: str, value: typing.Any): ...

    @abc.abstractmethod
    def search_in_providers(self, path) -> dict: ...


class IERegistrySupplier(abc.ABC):
    @property
    @abc.abstractmethod
    def reg(self) -> IERegistry: ...
