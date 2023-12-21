import abc
import enum
import typing

__all__ = (
    "IShellService",
    "IFileSystemService",
    "IStreamService",
    "IStateService",
    "ISnapService",
    "IInstanceService",
    "ServiceGroup",
    "Protocol",
    "IService",
    "Stat",
    "Wiring",
    "Whence",
    "StatField",
)


class Stat(typing.NamedTuple):
    st_mode: int = 0
    st_ino: int = 0
    st_dev: int = 0
    st_nlink: int = 0
    st_uid: int = 0
    st_gid: int = 0
    st_size: int = 0
    st_atime: int = 0
    st_mtime: int = 0
    st_ctime: int = 0
    st_pid: int | None = None
    st_status: int | None = None


class StatField(enum.Flag):
    MODE = 0x001
    INO = 0x002
    DEV = 0x004
    NLINK = 0x008
    UID = 0x010
    GID = 0x020
    SIZE = 0x040
    ATIME = 0x080
    MTIME = 0x100
    CTIME = 0x200
    PID = 0x400
    STATUS = 0x800
    FILE = MODE | INO | DEV | NLINK | UID | GID | SIZE | ATIME | MTIME | CTIME
    ALL = MODE | INO | DEV | NLINK | UID | GID | SIZE | ATIME | MTIME | CTIME | PID | STATUS


class Wiring(enum.Flag):
    OFF = 0
    IN = 0x01
    OUT = 0x02
    ERR = 0x04
    CREATE = 0x10
    RESET = 0x20
    INOUT = IN | OUT
    INOUTERR = IN | OUT | ERR


class Whence(enum.Enum):
    SEEK_SET = 0
    SEEK_CUR = 1
    SEEK_END = 2


class Protocol(enum.Enum):
    MYRRH = "m"
    POSIX = "posix"
    WINAPI = "winapi"
    VENDOR = "vendor"

    def __str__(self):
        return self._value_


class IService(abc.ABC):
    category: str
    name: str
    protocol: Protocol | str


T = typing.TypeVar("T")


class ServiceGroup(enum.Enum):
    vendor = abc.ABCMeta("IServiceVendor", (IService,), dict())
    system = abc.ABCMeta("IServiceSystem", (IService,), dict())
    host = abc.ABCMeta("IServiceHost", (IService,), dict())

    def __init__(self, cls):
        cls.category = self.name
        cls.__interfaces__ = dict()

    def __str__(self):
        return self._name_

    def __call__(cls, name: str):
        assert len(name) > 0, "invalid service name"
        assert name not in cls.__interfaces__

        def __new__(cls_):
            d_ = dict(cls_.__dict__)
            d_.update({"name": name})
            cls_ = abc.ABCMeta.__new__(abc.ABCMeta, cls_.__name__, (cls.value,), d_)
            cls.__interfaces__[name] = cls_
            return cls_

        return __new__

    @property
    def __interfaces__(self):
        return self.value.__interfaces__

    @staticmethod
    def group(
        category: "ServiceGroup" | typing.Iterable["ServiceGroup"] | str | None,
        services: list[T],
    ) -> list[T]:
        if category is None:

            def filter_(s) -> bool:
                return True

        else:
            if isinstance(category, str):
                categories = (category,)
            elif isinstance(category, ServiceGroup):
                categories = (category.name,)
            else:
                categories = tuple((c if isinstance(c, str) else c.name) for c in category)  # type: ignore[assignment]

            def filter_(s) -> bool:
                s_cat = s.category if isinstance(s.category, str) else s.category.name
                return s_cat in categories

        return list(filter(filter_, services))


@ServiceGroup.host("state")
class IStateService(abc.ABC):
    class states(enum.Enum):
        suspended = 0
        stopped = 1
        started = 2
        starting = 3
        stopping = 4
        suspending = 5
        unknown = -1

    @abc.abstractmethod
    def start(self, wait=False, *, extras: dict | None = None):
        ...

    @abc.abstractmethod
    def stop(self, force=False, wait=False, *, extras: dict | None = None):
        ...

    @abc.abstractmethod
    def suspend(self, force=False, wait=False, *, extras: dict | None = None):
        ...

    @abc.abstractmethod
    def reset(self, force=False, wait=False, *, extras: dict | None = None):
        ...

    @abc.abstractmethod
    def wait(self, state, delay=-1, *, extras: dict | None = None):
        ...

    @abc.abstractmethod
    def status(self):
        ...


@ServiceGroup.host("snap")
class ISnapService(abc.ABC):
    import posixpath

    sep = posixpath.sep
    join = staticmethod(posixpath.join)
    isabs = staticmethod(posixpath.isabs)
    basename = staticmethod(posixpath.basename)
    history = staticmethod(posixpath.dirname)

    @abc.abstractmethod
    def new(self, name, wait=False, *, extras: dict | None = None):
        ...

    @abc.abstractmethod
    def delete(self, name, wait=False, *, extras: dict | None = None):
        ...

    @abc.abstractmethod
    def restore(self, name, wait=False, *, extras: dict | None = None):
        ...

    @abc.abstractmethod
    def find(self, name, *, extras: dict | None = None):
        ...

    @abc.abstractmethod
    def names(self):
        ...

    @abc.abstractmethod
    def current(self):
        ...


@ServiceGroup.host("instance")
class IInstanceService:
    @abc.abstractmethod
    def delete(self, warehouse, *, extras: dict | None = None):
        ...

    @abc.abstractmethod
    def create(self, warehouse, *, extras: dict | None = None):
        ...


@ServiceGroup.system("shell")
class IShellService(abc.ABC):
    @abc.abstractmethod
    def execute(self, command: bytes, working_dir: bytes | None = None, env: dict | None = None, *, extras: dict | None = None) -> tuple[bytes, bytes, bytes]:
        ...

    @abc.abstractmethod
    def spawn(self, command: bytes, working_dir: bytes | None = None, env: dict | None = None, *, extras: dict | None = None) -> int:
        ...

    @abc.abstractmethod
    def signal(self, procid: int, sig: int, *, extras: dict | None = None):
        ...


@ServiceGroup.system("fs")
class IFileSystemService(abc.ABC):
    @abc.abstractmethod
    def rm(self, path: bytes, *, extras: dict | None = None) -> None:
        ...

    @abc.abstractmethod
    def mkdir(self, path: bytes, *, extras: dict | None = None) -> None:
        ...

    @abc.abstractmethod
    def rmdir(self, path: bytes, *, extras: dict | None = None) -> None:
        ...

    @abc.abstractmethod
    def is_container(self, path: bytes, *, extras: dict | None = None) -> bool:
        ...

    @abc.abstractmethod
    def exist(self, path: bytes, *, extras: dict | None = None) -> bool:
        ...

    @abc.abstractmethod
    def list(self, path: bytes, *, extras: dict | None = None) -> list[bytes]:
        ...

    @abc.abstractmethod
    def stat(self, path: bytes, *, extras: dict | None = None) -> dict:
        ...


@ServiceGroup.system("stream")
class IStreamService(abc.ABC):
    @abc.abstractmethod
    def open_file(self, path: bytes, wiring: int, *, extras: dict | None = None) -> tuple[bytes, int]:
        ...

    @abc.abstractmethod
    def open_process(self, path: bytes, wiring: int, args: list[bytes], working_dir: bytes | None = None, env: dict[bytes, bytes] | None = None, *, extras: dict | None = None) -> tuple[bytes, int, int | None, int | None, int | None]:
        ...

    @abc.abstractmethod
    def read(self, handle: int, nbytes: int, *, extras: dict | None = None) -> bytearray:
        ...

    @abc.abstractmethod
    def readall(self, handle: int, *, extras: dict | None = None) -> bytearray:
        ...

    @abc.abstractmethod
    def readchunk(self, handle: int, *, extras: dict | None = None) -> bytearray:
        ...

    @abc.abstractmethod
    def write(self, handle: int, data: bytes, *, extras: dict | None = None):
        ...

    @abc.abstractmethod
    def close(self, handle: int, *, extras: dict | None = None) -> None:
        ...

    @abc.abstractmethod
    def seek(self, handle: int, pos: int, whence: int, *, extras: dict | None = None) -> int:
        ...

    @abc.abstractmethod
    def sync(self, handle: int, *, extras: dict | None = None) -> None:
        ...

    @abc.abstractmethod
    def flush(self, handle: int, *, extras: dict | None = None) -> bytearray:
        ...

    @abc.abstractmethod
    def truncate(self, handle: int, length: int, *, extras: dict | None = None) -> None:
        ...

    @abc.abstractmethod
    def stat(self, handle: int, fields: int = StatField.ALL.value, *, extras: dict | None = None) -> dict:
        ...

    @abc.abstractmethod
    def terminate(self, handle: int, *, extras: dict | None = None) -> None:
        ...
