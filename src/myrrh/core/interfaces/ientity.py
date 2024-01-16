import abc
import threading
import typing
import pydantic
import datetime

from ...provider import (
    IShellEService,
    IFileSystemEService,
    IStreamEService,
    IStateEService,
    ISnapEService,
    IInstanceEService,
    Protocol,
    IEService,
)

__all__ = [
    "IEServiceGroup",
    "IRegistry",
    "IEServiceGroup",
    "ISystem",
    "IHost",
    "IVendor",
    "IEntity",
    "ICoreEService",
    "ICoreStreamEService",
    "ICoreShellEService",
    "ICoreFileSystemEService",
    "ICoreStateEService",
    "ICoreSnapEService",
    "ICoreInstanceEService",
    "Protocol",
]


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
    def now(self):
        ...

    @abc.abstractmethod
    def __bool__(self):
        ...


class ICoreEService(IEService):
    @classmethod
    @abc.abstractmethod
    def eref(cls) -> str:
        ...


class ICoreStreamEService(IStreamEService, ICoreEService):
    __delegate_all__ = (IStreamEService, ICoreEService)


class ICoreFileSystemEService(IFileSystemEService, ICoreEService):
    __delegate_all__ = (IFileSystemEService, ICoreEService)


class ICoreShellEService(IShellEService, ICoreEService):
    __delegate_all__ = (IShellEService, ICoreEService)


class ICoreStateEService(IStateEService, ICoreEService):
    __delegate_all__ = (IStateEService, ICoreEService)


class ICoreSnapEService(ISnapEService, ICoreEService):
    __delegate_all__ = (ISnapEService, ICoreEService)


class ICoreInstanceEService(IInstanceEService, ICoreEService):
    __delegate_all__ = (IInstanceEService, ICoreEService)


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
    def append(self, item: IBaseItem, mode: typing.Literal["keep", "update", "replace"]):
        ...


class IEServiceGroup(abc.ABC):
    @property
    @abc.abstractmethod
    def services(self) -> dict[str, typing.Type[ICoreEService]]:
        ...

    @property
    @abc.abstractmethod
    def cfg(self) -> IRegistry:
        ...

    @property
    @abc.abstractmethod
    def lock(self) -> threading.RLock:
        ...


class ISystem(IEServiceGroup):
    @property
    @abc.abstractmethod
    def shell(self) -> ICoreShellEService:
        ...

    @property
    @abc.abstractmethod
    def fs(self) -> ICoreFileSystemEService:
        ...

    @property
    @abc.abstractmethod
    def stream(self) -> ICoreStreamEService:
        ...

    @abc.abstractmethod
    def Stream(self, protocol: str | Protocol | None = None) -> ICoreStreamEService:
        ...

    @abc.abstractmethod
    def Fs(self, protocol: str | Protocol | None = None) -> ICoreFileSystemEService:
        ...

    @abc.abstractmethod
    def Shell(self, protocol: str | Protocol | None = None) -> ICoreShellEService:
        ...


class IHost(IEServiceGroup):
    @property
    @abc.abstractmethod
    def state(self) -> ICoreStateEService:
        ...

    @property
    @abc.abstractmethod
    def snap(self) -> ICoreSnapEService:
        ...

    @property
    @abc.abstractmethod
    def inst(self) -> ICoreInstanceEService:
        ...


class IVendor(IEServiceGroup):
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
