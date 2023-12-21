import abc
import threading
import typing

from ...warehouse.item import BaseItem
from ...provider import (
    IShellService,
    IFileSystemService,
    IStreamService,
    IStateService,
    ISnapService,
    IInstanceService,
    Protocol,
    IService,
)

__all__ = [
    "IServiceGroup",
    "IRegistry",
    "IServiceGroup",
    "ISystem",
    "IHost",
    "IVendor",
    "IEntity",
    "ICoreService",
    "ICoreStreamService",
    "ICoreShellService",
    "ICoreFileSystemService",
    "ICoreStateService",
    "ICoreSnapService",
    "ICoreInstanceService",
    "Protocol",
]


class ICoreService(IService):
    @classmethod
    @abc.abstractmethod
    def eref(cls) -> str:
        ...


class ICoreStreamService(IStreamService, ICoreService):
    __delegate_all__ = (IStreamService, ICoreService)


class ICoreFileSystemService(IFileSystemService, ICoreService):
    __delegate_all__ = (IFileSystemService, ICoreService)


class ICoreShellService(IShellService, ICoreService):
    __delegate_all__ = (IShellService, ICoreService)


class ICoreStateService(IStateService, ICoreService):
    __delegate_all__ = (IStateService, ICoreService)


class ICoreSnapService(ISnapService, ICoreService):
    __delegate_all__ = (ISnapService, ICoreService)


class ICoreInstanceService(IInstanceService, ICoreService):
    __delegate_all__ = (IInstanceService, ICoreService)


class IRegistry(dict, abc.ABC):
    @abc.abstractmethod
    def __getattr__(self, name) -> typing.Any:
        ...

    @abc.abstractmethod
    def predefined(self) -> list[typing.Any]:
        ...

    @abc.abstractmethod
    def defined_values(self) -> list[typing.Any]:
        ...

    @abc.abstractmethod
    def append(self, item: BaseItem, mode: typing.Literal["keep", "update", "replace"]):
        ...


class IServiceGroup(abc.ABC):
    @property
    @abc.abstractmethod
    def services(self) -> dict[str, typing.Type[ICoreService]]:
        ...

    @property
    @abc.abstractmethod
    def cfg(self) -> IRegistry:
        ...

    @property
    @abc.abstractmethod
    def lock(self) -> threading.RLock:
        ...


class ISystem(IServiceGroup):
    @property
    @abc.abstractmethod
    def shell(self) -> ICoreShellService:
        ...

    @property
    @abc.abstractmethod
    def fs(self) -> ICoreFileSystemService:
        ...

    @property
    @abc.abstractmethod
    def stream(self) -> ICoreStreamService:
        ...

    @abc.abstractmethod
    def Stream(self, protocol: str | Protocol | None = None) -> ICoreStreamService:
        ...

    @abc.abstractmethod
    def Fs(self, protocol: str | Protocol | None = None) -> ICoreFileSystemService:
        ...

    @abc.abstractmethod
    def Shell(self, protocol: str | Protocol | None = None) -> ICoreShellService:
        ...


class IHost(IServiceGroup):
    @property
    @abc.abstractmethod
    def state(self) -> ICoreStateService:
        ...

    @property
    @abc.abstractmethod
    def snap(self) -> ICoreSnapService:
        ...

    @property
    @abc.abstractmethod
    def inst(self) -> ICoreInstanceService:
        ...


class IVendor(IServiceGroup):
    ...


class IEntity:
    @property
    @abc.abstractmethod
    def system(self) -> ISystem:
        ...

    @property
    @abc.abstractmethod
    def host(self) -> IHost:
        ...

    @property
    @abc.abstractmethod
    def vendor(self) -> IVendor:
        ...

    @property
    @abc.abstractmethod
    def cfg(self) -> IRegistry:
        ...

    @property
    @abc.abstractmethod
    def eid(self) -> str:
        ...
