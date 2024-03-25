import abc
import typing

from .ientity import (
    IESystem,
    IECoreShellService,
    IECoreFileSystemService,
    IECoreStreamService,
)
from .ieservices import EStat, EProtocol, IEWarehouseService

__all__ = ["IRuntimeObject", "ITask", "IMyrrhOs", "IMHandle"]
__all__ += [
    "IStream",
    "IInStream",
    "IOutStream",
    "IInOutStream",
    "IFileInStream",
    "IFileOutStream",
    "IFileInOutStream",
    "EStat",
]
__all__ += [
    "IProcess",
]
__all__ += [
    "IRuntimeTaskManager",
]


class IMHandle(abc.ABC):
    @property
    @abc.abstractmethod
    def val(self) -> int: ...

    @property
    @abc.abstractmethod
    def closed(self) -> bool: ...

    @abc.abstractmethod
    def close(self) -> None: ...

    @abc.abstractmethod
    def detach(self) -> int: ...


class IFuture(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def wait(self, timeout: float) -> None: ...

    @classmethod
    @abc.abstractmethod
    def result(self, timeout: float) -> None: ...

    @classmethod
    @abc.abstractmethod
    def notify(self, msg: typing.Any) -> None: ...


class IRuntimeObject(abc.ABC):
    __m_ref_count__ = 0

    @property
    @abc.abstractmethod
    def ehandle(self) -> int: ...

    @property
    @abc.abstractmethod
    def eref(self) -> str: ...

    @property
    @abc.abstractmethod
    def epath(self) -> str: ...

    @property
    @abc.abstractmethod
    def ename(self) -> str: ...

    @property
    @abc.abstractmethod
    def closed(self) -> bool: ...

    @abc.abstractmethod
    def close(self): ...

    @classmethod
    def __subclasshook__(cls, C):
        if issubclass(C, IMHandle):
            return issubclass(C.obj.__class__, cls)

        return NotImplemented


class ITask(abc.ABC):
    @abc.abstractmethod
    def task(self, future: IFuture) -> bool: ...

    @abc.abstractmethod
    def terminated(self) -> int | None: ...


class IRuntimeTaskManager(abc.ABC):

    @abc.abstractmethod
    def submit(self, task: ITask) -> bool: ...


class IMyrrhOs(IESystem, IEWarehouseService):
    @property
    @abc.abstractmethod
    def curdir(self) -> str: ...

    @property
    @abc.abstractmethod
    def pardir(self) -> str: ...

    @property
    @abc.abstractmethod
    def extsep(self) -> str: ...

    @property
    @abc.abstractmethod
    def sep(self) -> str: ...

    @property
    @abc.abstractmethod
    def pathsep(self) -> str: ...

    @property
    @abc.abstractmethod
    def altsep(self) -> str: ...

    @property
    @abc.abstractmethod
    def linesep(self) -> str: ...

    @property
    @abc.abstractmethod
    def devnull(self) -> str: ...

    @property
    @abc.abstractmethod
    def defpath(self) -> str: ...

    @property
    @abc.abstractmethod
    def modules(self) -> dict[str, typing.Any]: ...

    @property
    @abc.abstractmethod
    def concretes(self) -> dict[str, typing.Any]: ...

    @abc.abstractmethod
    def getbin(self) -> dict[bytes, bytes]: ...

    @abc.abstractmethod
    def cwd(self) -> str: ...

    @abc.abstractmethod
    def tmpdir(self) -> str: ...

    @abc.abstractmethod
    def localcode(self) -> str: ...

    @abc.abstractmethod
    def getdefaultlocale(self) -> tuple[str]: ...

    @abc.abstractmethod
    def getpath(self, path: str | None = None) -> str: ...

    @abc.abstractmethod
    def env(self) -> dict[str, str]: ...

    @abc.abstractmethod
    def getenv(self, env: dict[str, str] | None = None) -> dict[str, str]: ...

    @abc.abstractmethod
    def setenv(self, env: dict[str, str]) -> None: ...

    @abc.abstractmethod
    def rdenv(self) -> list[str]: ...

    @abc.abstractmethod
    def environkeyformat(self, key: str) -> str: ...

    @abc.abstractmethod
    def isabs(self, path: str) -> bool: ...

    @abc.abstractmethod
    def normpath(self, path: str) -> str: ...

    @abc.abstractmethod
    def joinpath(self, *args: str) -> str: ...

    @abc.abstractmethod
    def basename(self, path: str) -> str: ...

    @abc.abstractmethod
    def dirname(self, path: str) -> str: ...

    @abc.abstractmethod
    def syspath(self, path: str) -> str: ...

    @abc.abstractmethod
    def getshellscript(self, script: str) -> str: ...

    @abc.abstractmethod
    def getdefaultshell(self, *args: str) -> list[str]: ...

    @abc.abstractmethod
    def formatshellargs(self, args: list[str], *, defaultargs: list[str] | None = None) -> str: ...

    @abc.abstractmethod
    def sh_escape(self, string: str) -> str: ...

    @abc.abstractmethod
    def shellpath(self) -> str: ...

    @abc.abstractmethod
    def shellargs(self) -> list[str]: ...

    @abc.abstractmethod
    def cmd(self, cmdline: str, **kwargs) -> tuple[str, str, int]: ...

    @abc.abstractmethod
    def cmdb(self, cmdline: str, **kwargs) -> tuple[bytes, bytes, int]: ...

    @abc.abstractmethod
    def fsencoding(self) -> str: ...

    @abc.abstractmethod
    def fsencodeerrors(self) -> str: ...

    @abc.abstractmethod
    def defaultencoding(self) -> str: ...

    @abc.abstractmethod
    def shdecode(self, b: str | bytes, errors="surrogateescape") -> str: ...

    @abc.abstractmethod
    def shencode(self, s: str | bytes, errors="surrogateescape") -> bytes: ...

    @abc.abstractmethod
    def fsdecode(self, val: str | bytes) -> str: ...

    @abc.abstractmethod
    def fsencode(self, val: str | bytes) -> bytes: ...

    @abc.abstractmethod
    def fdcast(self, val: typing.Any, *, encoding: str | None = None) -> typing.Any: ...

    @abc.abstractmethod
    def fscast(self, val: typing.Any, *, encoding: str | None = None) -> typing.Any: ...

    @abc.abstractmethod
    def shcast(self, val: typing.Any, *, encoding: str | None = None) -> typing.Any: ...

    @abc.abstractmethod
    def f(self, path: str | bytes | int, *, dir_fd: None | int = None) -> str: ...

    @abc.abstractmethod
    def p(self, path: str | bytes, *, dir_fd: None | int = None) -> str: ...

    @abc.abstractmethod
    def Stream(self, protocol: str | EProtocol | None = None) -> IECoreStreamService: ...

    @abc.abstractmethod
    def Fs(self, protocol: str | EProtocol | None = None) -> IECoreFileSystemService: ...

    @abc.abstractmethod
    def Shell(self, protocol: str | EProtocol | None = None) -> IECoreShellService: ...


class IStream(IRuntimeObject):
    @property
    @abc.abstractmethod
    def eot(self) -> bool: ...

    @abc.abstractmethod
    def send_eot(self, eot: bool, id: int | None) -> bool: ...

    @abc.abstractmethod
    def sync(self, *, extras: dict[str, typing.Any] | None = None) -> None: ...

    @abc.abstractmethod
    def flush(self, *, extras: dict[str, typing.Any] | None = None) -> bytearray: ...

    @abc.abstractmethod
    def stat(self, *, extras: dict[str, typing.Any] | None = None) -> EStat: ...


class IInStream(IStream):
    @abc.abstractmethod
    def read(self, nbytes: int | None = None, *, extras: dict[str, typing.Any] | None = None) -> bytearray: ...


class IOutStream(IStream):
    @abc.abstractmethod
    def write(self, data: bytes, *, extras: dict[str, typing.Any] | None = None): ...


class IInOutStream(IInStream, IOutStream): ...


class IFileInStream(IInStream):
    @abc.abstractmethod
    def seek(self, nbytes: int, *, extras: dict[str, typing.Any] | None = None) -> int: ...


class IFileOutStream(IOutStream):
    @abc.abstractmethod
    def truncate(self, length: int, *, extras: dict[str, typing.Any] | None = None) -> None: ...

    @abc.abstractmethod
    def seek(self, nbytes: int, *, extras: dict[str, typing.Any] | None = None) -> int: ...


class IFileInOutStream(IFileInStream, IFileOutStream, IInOutStream): ...


class IProcess(ITask, IRuntimeObject):
    @property
    @abc.abstractmethod
    def pid(self) -> int: ...

    @property
    @abc.abstractmethod
    def exit_status(self, *, extras: dict[str, typing.Any] | None = None) -> int | None: ...

    @abc.abstractmethod
    def terminate(self, *, extras: dict[str, typing.Any] | None = None) -> None: ...

    @abc.abstractmethod
    def stat(self, *, extras=None) -> EStat: ...
