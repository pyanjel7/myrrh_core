import sys
import threading
import fnmatch
import typing

from mplugins.provider.local import provider

from ..interfaces import (
    ICoreService,
    NoneDelegation,
    ISystem,
    ABCDelegation,
    ABCDelegationMeta,
    IRegistry,
    ICoreSnapService,
    ICoreInstanceService,
    ICoreStateService,
    ICoreShellService,
    ICoreFileSystemService,
    ICoreStreamService,
)
from ..services import cfg_init

from ...warehouse.item import NoneItem
from ...warehouse.registry import ItemRegistry
from ...provider import ServiceGroup, IProvider, Protocol, service_fullname


from ._services import FileSystemService, ShellService, StreamService
from ._registry import Registry

__all__ = [
    "Entity",
    "CoreServiceClass",
    "CoreProviderClass",
    "CoreProvider",
    "NoneShell",
    "NoneFs",
    "NoneStream",
    "NoneState",
    "NoneSnap",
    "NoneInstance",
]

_VALIDATE = cfg_init("validate_service_args", True, section="myrrh.core")

NoneShell = NoneDelegation("NoneShellType", ICoreShellService)
NoneFs = NoneDelegation("NoneFsType", ICoreFileSystemService)
NoneStream = NoneDelegation("NoneFsType", ICoreStreamService)
NoneState = NoneDelegation("NoneStateType", ICoreStateService)
NoneSnap = NoneDelegation("NoneSnapType", ICoreSnapService)
NoneInstance = NoneDelegation("NoneInstance", ICoreInstanceService)


class _ServiceGroup:
    __slots__ = ("cfg", "lock", "services", "protocols")

    cfg: IRegistry
    lock: threading.RLock
    services: dict[str, typing.Type[ICoreService]]

    def __init__(
        self,
        category: ServiceGroup,
        cfg,
        services: list[typing.Type[ICoreService]] = list(),
    ):
        self.services = {s.eref(): s for s in ServiceGroup.group(category, services)}

        self.cfg = cfg
        self.lock = threading.RLock()
        self.protocols = set()

        for serv in self.services.values():
            if not hasattr(self, str(serv.protocol)):
                setattr(self, str(serv.protocol), type("protocol", (), {}))

            protocol = getattr(self, str(serv.protocol))

            setattr(protocol, serv.name, serv())

            self.protocols.add(str(serv.protocol))


class System(_ServiceGroup, ISystem):
    shell: ShellService = NoneShell
    fs: FileSystemService = NoneFs
    stream: StreamService = NoneStream

    def __init__(self, cfg, services=list()):
        super().__init__(ServiceGroup.system, cfg, services)

        proto = getattr(self, Protocol.MYRRH.value, None)

        if proto:
            self.shell = getattr(proto, "shell", NoneShell)
            self.fs = getattr(proto, "fs", NoneFs)
            self.stream = getattr(proto, "stream", NoneStream)

        if _VALIDATE:
            self.shell = ShellService(self.shell)
            self.fs = FileSystemService(self.fs)
            self.stream = StreamService(self.stream)

    def __str__(self):
        return f'{self.cfg.eid}(System: {",".join(self.protocols)}'

    def Stream(self, protocol: str | Protocol | None = None) -> ICoreStreamService:
        if not protocol:
            return self.stream

        protocol_name = protocol.value if isinstance(protocol, Protocol) else protocol
        try:
            return getattr(self, protocol_name).stream
        except AttributeError:
            pass

        raise RuntimeError(f'Unsupported stream protocol "{protocol_name}" for {str(self)}')

    def Fs(self, protocol: str | Protocol | None = None) -> ICoreFileSystemService:
        if not protocol:
            return self.fs

        protocol_name = protocol.value if isinstance(protocol, Protocol) else protocol
        try:
            return getattr(self, protocol_name).fs
        except AttributeError:
            pass

        raise RuntimeError(f'Unsupported file system protocol "{protocol_name}" for {str(self)}')

    def Shell(self, protocol: str | Protocol | None = None) -> ICoreShellService:
        if not protocol:
            return self.shell

        protocol_name = protocol.value if isinstance(protocol, Protocol) else protocol

        try:
            return getattr(self, protocol_name).shell
        except AttributeError:
            pass

        raise RuntimeError(f'Unsupported shell protocol "{protocol_name}" for {str(self)}')


class Host(_ServiceGroup):
    state: ICoreStateService = NoneState
    snap: ICoreSnapService = NoneSnap
    inst: ICoreInstanceService = NoneInstance

    def __init__(self, cfg, services=list()):
        super().__init__(ServiceGroup.host, cfg, services)

        proto = getattr(self, Protocol.MYRRH.value, None)
        if proto:
            self.state = getattr(proto, "state", NoneState)
            self.snap = getattr(proto, "snap", NoneSnap)
            self.inst = getattr(proto, "inst", NoneInstance)


class Vendor(_ServiceGroup):
    def __init__(self, cfg, services=list()):
        super().__init__(ServiceGroup.vendor, cfg, services)


def CoreProviderClass(provider_cls, name) -> typing.Type[IProvider]:
    class _(IProvider, ABCDelegation):
        __delegated__ = (IProvider,)
        _name_ = name
        _provider_ = provider_cls

        def __init__(self, *a, **kwa):
            self.__delegate__(IProvider, self._provider_(*a, **kwa))

    return ABCDelegationMeta(_._provider_.__name__, _.__bases__, dict(_.__dict__))  # type: ignore[return-value]


def CoreServiceClass(path, serv_cls, pname):
    ServInterface = ServiceGroup[serv_cls.category].__interfaces__[serv_cls.name]

    class _(ICoreService, ServInterface, ABCDelegation):
        _serv_ = serv_cls

        _eref = "/".join((path, pname))
        category = serv_cls.category
        protocol = serv_cls.protocol
        name = serv_cls.name

        __delegated__ = (ServInterface,)

        def __init__(self, *a, **kwa):
            self.__delegate__(ServInterface, self._serv_(*a, **kwa))

        @classmethod
        def eref(cls):
            return cls._eref

    return ABCDelegationMeta(_._serv_.__name__, _.__bases__, dict(_.__dict__))


class CoreProvider(IProvider):
    SERV = 0
    CTLG = 1

    def __init__(
        self,
        providers: typing.Iterable[IProvider],
        *,
        patterns: list[str] | None = None,
    ):
        self.providers = list(providers)

        self._services: dict[str, typing.Type[ICoreService]] = dict()
        self._catalog: dict[str, IProvider] = dict()
        self.paths = ""

        self._init_using_path(providers, patterns)

    def _get_all_paths(self, providers: list[IProvider]):
        _allpaths = dict()

        for p in providers:
            serv = map(
                lambda s: CoreServiceClass(f"{self.SERV}/{service_fullname(s)}", s, p._name_),
                p.services(),
            )

            for serv in ServiceGroup.group(None, list(serv)):
                _allpaths[serv.eref()] = serv

            for item in p.catalog():
                path = f"{self.CTLG}/catalog/{item}/{p._name_}"
                _allpaths[path] = p

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
                case self.CTLG:
                    self._catalog[path] = _allpaths[entry]
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

    def services(self) -> tuple[typing.Type[ICoreService]]:
        return tuple(self._services.values())  # type: ignore[return-value]

    def catalog(self) -> tuple[str]:
        return tuple(self._catalog.keys())  # type: ignore[return-value]

    def deliver(self, name):
        provider = self._catalog.get(name, None)

        if provider:
            return provider.deliver(name)

        return NoneItem


class Entity:
    system: System
    host: Host
    vendor: Vendor

    def __new__(cls, provider: CoreProvider, items: list[ItemRegistry().WarehouseItemT] = list()):  # type: ignore[valid-type]
        self = super().__new__(cls)

        sys.__msys__["@entities@"].append(self)  # type: ignore[attr-defined]

        return self

    def __init__(self, provider: IProvider, items: list[ItemRegistry().WarehouseItemT] = list()):  # type: ignore[valid-type]
        services = provider.services()

        self.provider = provider

        self.cfg = Registry(provider, items)
        self.system = System(self.cfg, services)
        self.host = Host(self.cfg, services)
        self.vendor = Vendor(self.cfg, services)

    @property
    def eid(self):
        return self.cfg.eid

    @property
    def uuid(self):
        return self.cfg.uuid

    def __str__(self):
        return str(self.eid)

    def __repr__(self):
        return "Entity<%s>" % self.eid


setattr(Entity, ".", Entity(CoreProvider((CoreProviderClass(provider, ".")(),))))
