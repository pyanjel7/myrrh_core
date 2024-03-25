import abc
import threading

from .ieregistry import IERegistrySupplier

from .ieservices import (
    IEShellService,
    IEFileSystemService,
    IEStreamService,
    IEStateService,
    IESnapService,
    IEInstanceService,
    IEWarehouseService,
    EProtocol,
    IEService,
)


__all__ = [
    "IEServiceGroup",
    "IEServiceGroup",
    "IESystem",
    "IEHost",
    "IEVendor",
    "IEntity",
    "IECoreService",
    "IECoreStreamService",
    "IECoreShellService",
    "IECoreFileSystemService",
    "IECoreStateService",
    "IECoreSnapService",
    "IECoreInstanceService",
    "EProtocol",
]


class IECoreService(IEService):
    @classmethod
    @abc.abstractmethod
    def eref(cls) -> str: ...


class IECoreStreamService(IEStreamService, IECoreService):
    __delegate_all__ = (IEStreamService, IECoreService)


class IECoreFileSystemService(IEFileSystemService, IECoreService):
    __delegate_all__ = (IEFileSystemService, IECoreService)


class IECoreShellService(IEShellService, IECoreService):
    __delegate_all__ = (IEShellService, IECoreService)


class IECoreStateService(IEStateService, IECoreService):
    __delegate_all__ = (IEStateService, IECoreService)


class IECoreSnapService(IESnapService, IECoreService):
    __delegate_all__ = (IESnapService, IECoreService)


class IECoreInstanceService(IEInstanceService, IECoreService):
    __delegate_all__ = (IEInstanceService, IECoreService)


class IEServiceGroup(IERegistrySupplier, abc.ABC):
    @property
    @abc.abstractmethod
    def services(self) -> dict[str, type[IECoreService]]: ...

    @property
    @abc.abstractmethod
    def lock(self) -> threading.RLock: ...


class IESystem(IEServiceGroup):
    @property
    @abc.abstractmethod
    def shell(self) -> IECoreShellService: ...

    @property
    @abc.abstractmethod
    def fs(self) -> IECoreFileSystemService: ...

    @property
    @abc.abstractmethod
    def stream(self) -> IECoreStreamService: ...

    @abc.abstractmethod
    def Stream(self, protocol: str | EProtocol | None = None) -> IECoreStreamService: ...

    @abc.abstractmethod
    def Fs(self, protocol: str | EProtocol | None = None) -> IECoreFileSystemService: ...

    @abc.abstractmethod
    def Shell(self, protocol: str | EProtocol | None = None) -> IECoreShellService: ...


class IEHost(IEServiceGroup):
    @property
    @abc.abstractmethod
    def state(self) -> IECoreStateService: ...

    @property
    @abc.abstractmethod
    def snap(self) -> IECoreSnapService: ...

    @property
    @abc.abstractmethod
    def inst(self) -> IECoreInstanceService: ...


class IEVendor(IEServiceGroup):

    @property
    @abc.abstractmethod
    def warehouse(self) -> IEWarehouseService: ...


class IEntity(IERegistrySupplier):

    @property
    @abc.abstractmethod
    def system(self) -> IESystem: ...

    @property
    @abc.abstractmethod
    def host(self) -> IEHost: ...

    @property
    @abc.abstractmethod
    def vendor(self) -> IEVendor: ...

    @property
    @abc.abstractmethod
    def eid(self) -> str: ...
