import threading
import sys
import fnmatch
import typing
import weakref

from mplugins.provider.local import Provider

from ..services import db
from ...utils.delegation import ABCDelegation, ABCDelegationMeta

from ..interfaces import (
    IECoreService,
    IESystem,
    IERegistry,
    IEServiceGroup,
    IEWarehouseService,
    IECoreShellService,
    IECoreFileSystemService,
    IECoreStreamService,
    EServiceGroup,
    IEService,
    IEHost,
    IEVendor,
    IProvider,
    EProtocol,
)

from ...utils.misc import service_fullname

from ...warehouse.registry import ItemRegistry


from ._registry import ERegistry, ERegistry_Static

__all__ = ["Entity", "CoreEServiceClass", "CoreProvider"]


class _EServiceProtocol:
    services: dict[str, "_EServiceGroup"]

    def use(self, path):
        serv = self.services.get(path, False)

        if serv is False:
            raise KeyError(f"invalid service path: {path}")

        setattr(self, serv.name, path)


class _EServProperty:
    def __init__(self, path: str, cls: type[IECoreService]):
        self.path = path
        self.cls = cls

    def __get__(self, instance: _EServiceProtocol, owner):
        if not instance:
            return self

        serv = instance.services.get(self.path)

        if serv is None:
            serv = self.cls()  # type: ignore[assignment]
            instance.services[self.path] = serv  # type: ignore[assignment]

        return serv

    def __set__(self, instance: _EServiceProtocol, path: str):
        self.path = path


class _EServiceGroup(IEServiceGroup):
    __slots__ = ("reg", "lock", "services", "default", "protocols")

    reg: IERegistry
    lock: threading.RLock
    services: dict[str, type[IECoreService]]
    default: _EServiceProtocol | None
    protocols: set[str]

    def __init__(self, category: EServiceGroup, services: list[type[IECoreService]], registry: ERegistry):
        self.services = {s.eref(): s for s in EServiceGroup.group(category, services)}
        self.reg = registry

        self.lock = threading.RLock()
        self.default = None
        self.protocols = set()

        for path, cls in self.services.items():

            if not hasattr(self, str(cls.protocol)):
                setattr(self, str(cls.protocol), type(str(cls.protocol), (_EServiceProtocol,), {"services": dict()})())
                self.protocols.add(str(cls.protocol))

            protocol = getattr(self, str(cls.protocol))
            protocol.services[path] = None
            if not hasattr(protocol, cls.name):
                setattr(protocol.__class__, cls.name, _EServProperty(path, cls))

        self.select(EProtocol.MYRRH)

    def select(self, protocol: EProtocol):
        self.default = getattr(self, protocol.value, None)  # type: ignore[assignment]

    def __getattr__(self, name):
        if self.default is not None:
            return getattr(self.default, name)

        return super().__getattr__(name)


class _EDbWarehouse(IEWarehouseService):

    def __init__(self, registry: IERegistry):
        self.reg = ERegistry_Static(weakref.proxy(registry))

    def catalog(self):
        return ["*"]

    def deliver(self, data: dict, name: str) -> dict | None:
        return db.search(self.reg, data, name)


class System(_EServiceGroup, IESystem):
    __slots__ = ("shell", "fs", "stream")

    shell: IECoreShellService
    fs: IECoreFileSystemService
    stream: IECoreStreamService

    def __init__(self, services: list[type[IECoreService]], registry: ERegistry):
        super().__init__(EServiceGroup.system, services, registry)

    def __str__(self):
        return f'{self.reg.eid}(System: {",".join(self.protocols)}'

    def Stream(self, protocol: str | EProtocol | None = None) -> IECoreStreamService:
        if not protocol:
            return self.stream

        protocol_name = protocol.value if isinstance(protocol, EProtocol) else protocol
        try:
            return getattr(self, protocol_name).stream
        except AttributeError:
            pass

        raise RuntimeError(f'Unsupported stream protocol "{protocol_name}" for {str(self)}')

    def Fs(self, protocol: str | EProtocol | None = None) -> IECoreFileSystemService:
        if not protocol:
            return self.fs

        protocol_name = protocol.value if isinstance(protocol, EProtocol) else protocol
        try:
            return getattr(self, protocol_name).fs
        except AttributeError:
            pass

        raise RuntimeError(f'Unsupported file system protocol "{protocol_name}" for {str(self)}')

    def Shell(self, protocol: str | EProtocol | None = None) -> IECoreShellService:
        if not protocol:
            return self.shell

        protocol_name = protocol.value if isinstance(protocol, EProtocol) else protocol

        try:
            return getattr(self, protocol_name).shell
        except AttributeError:
            pass

        raise RuntimeError(f'Unsupported shell protocol "{protocol_name}" for {str(self)}')


class Host(_EServiceGroup, IEHost):
    __slots__ = ("state", "snap", "inst")

    def __init__(selfself, services: list[type[IECoreService]], registry: ERegistry):
        super().__init__(EServiceGroup.host, services, registry)


class Vendor(_EServiceGroup, IEVendor):
    __slots__ = "warehouse"

    def __init__(self, services: list[type[IECoreService]], registry: ERegistry):
        super().__init__(EServiceGroup.vendor, services, registry)


def CoreEServiceClass(path: str, serv_cls: type[IEService], provider: IProvider) -> type[IECoreService]:
    ServInterface: type[IEService] = EServiceGroup[serv_cls.category].__interfaces__[serv_cls.name]

    class _(IECoreService, ServInterface, ABCDelegation):  # type: ignore[misc, valid-type]
        _eref = "/".join((path, provider._name_))
        _serv = serv_cls
        _provider: IProvider = provider

        category = serv_cls.category
        protocol = serv_cls.protocol
        name = serv_cls.name

        __delegated__ = (ServInterface,)

        def __init__(self):
            service = self._provider.subscribe(self._serv)
            self.__delegate__(ServInterface, service)

        def __repr__(self):
            return self._eref

        @classmethod
        def eref(cls):
            return cls._eref

    return ABCDelegationMeta(_._serv.__name__, _.__bases__, dict(_.__dict__))  # type: ignore[return-value]


class CoreProvider:

    SERV = 0

    def __init__(
        self,
        providers: typing.Iterable[IProvider],
        *,
        patterns: list[str] | None = None,
    ):
        self.providers = list(providers)

        self._services: dict[str, type[IECoreService]] = dict()
        self.paths = ""

        self._init_using_path(providers, patterns)

    def _get_all_paths(self, providers: list[IProvider]):
        _allpaths = dict()

        for p in providers:
            serv = map(
                lambda s: CoreEServiceClass(f"{self.SERV}/{service_fullname(s)}", s, p),
                p.services(),
            )

            for serv in EServiceGroup.group(None, list(serv)):
                _allpaths[serv.eref()] = serv

        return _allpaths

    def _init_using_path(self, providers, patterns):
        _allpaths = self._get_all_paths(providers)

        paths = list()
        if patterns:
            for pattern in patterns:
                paths.extend(fnmatch.filter(_allpaths, pattern))
        else:
            paths = _allpaths

        for entry in paths:
            _i, _, path, _ = entry.split("/", 3)

            match int(_i):
                case self.SERV:
                    self._services[entry] = _allpaths[entry]

        def _paths_todict(path: str, dct: dict, value):
            if path:
                p, _, v = path.partition("/")
                dct[p] = _paths_todict(v, (dct.get(p) or dict()), value)
                dct[f"{p}_"] = dct.get(f"{p}_") or list()
                dct[f"{p}_"].append(v)
                return dct

            return value

        self.paths = dict()

        for path in paths:
            _paths_todict(path, self.paths, _allpaths[path])

    def services(self) -> list[type[IECoreService]]:  # type: ignore[return-value]
        return tuple(self._services.values())  # type: ignore[return-value]

    def subscribe(self, serv: type[IECoreService]) -> IECoreService | None:
        return serv()


class Entity:
    system: System
    host: Host
    vendor: Vendor

    def __new__(
        cls,
        providers: typing.Iterable[IProvider],
        items: list[ItemRegistry().WarehouseItemT] = list(),  # type: ignore[valid-type]
        *,
        patterns: list[str] | None = None,
    ):  # type: ignore[valid-type]
        self = super().__new__(cls)

        sys.__msys__["@entities@"].append(self)  # type: ignore[attr-defined]

        return self

    def __init__(
        self,
        providers: typing.Iterable[IProvider],
        items: list[ItemRegistry().WarehouseItemT] = list(),  # type: ignore[valid-type]
        *,
        patterns: list[str] | None = None,
    ):
        self.provider = CoreProvider(providers, patterns=patterns)

        services = self.provider.services()

        self.reg = ERegistry(items)
        for s in EServiceGroup.group(EServiceGroup.vendor, services):
            if s.name == "warehouse":
                self.reg.add_warehouse(s())  # type: ignore[arg-type]

        # add db
        self.reg.add_warehouse(_EDbWarehouse(self.reg))

        self.system = System(services, self.reg)
        self.host = Host(services, self.reg)
        self.vendor = Vendor(services, self.reg)

    @property
    def eid(self):
        return self.reg.eid

    @property
    def uuid(self):
        return self.reg.uuid

    def __str__(self):
        return str(self.eid)

    def __repr__(self):
        return "Entity<%s>" % self.eid


setattr(
    Entity,
    ".",
    Entity(
        [Provider()],
    ),
)
