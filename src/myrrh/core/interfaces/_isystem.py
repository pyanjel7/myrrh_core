import abc
import typing

from ._ientity import (
    ISystem,
    ICoreShellService,
    ICoreFileSystemService,
    ICoreStreamService,
)
from ...provider import Stat, Protocol

__all__ = ["IRuntimeObject", "ITask", "IMyrrhOs", "IMHandle"]
__all__ += [
    "IStream",
    "IInStream",
    "IOutStream",
    "IInOutStream",
    "IFileInStream",
    "IFileOutStream",
    "IFileInOutStream",
    "Stat",
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
    def val(self) -> int:
        ...

    @property
    @abc.abstractmethod
    def closed(self) -> bool:
        ...

    @abc.abstractmethod
    def close(self) -> None:
        ...

    @abc.abstractmethod
    def detach(self) -> int:
        ...


class IFuture(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def wait(self, timeout: float) -> None:
        ...

    @classmethod
    @abc.abstractmethod
    def result(self, timeout: float) -> None:
        ...

    @classmethod
    @abc.abstractmethod
    def notify(self, msg: typing.Any) -> None:
        ...


class IRuntimeObject(abc.ABC):
    __m_ref_count__ = 0

    @property
    @abc.abstractmethod
    def ehandle(self) -> int:
        ...

    @property
    @abc.abstractmethod
    def eref(self) -> str:
        ...

    @property
    @abc.abstractmethod
    def epath(self) -> bytes:
        ...

    @property
    @abc.abstractmethod
    def ename(self) -> bytes:
        ...

    @property
    @abc.abstractmethod
    def closed(self) -> bool:
        ...

    @abc.abstractmethod
    def close(self):
        ...

    @classmethod
    def __subclasshook__(cls, C):
        if issubclass(C, IMHandle):
            return issubclass(C.obj.__class__, cls)

        return NotImplemented


class ITask(abc.ABC):
    @abc.abstractmethod
    def task(self, future: IFuture) -> bool:
        ...

    @abc.abstractmethod
    def terminated(self) -> int | None:
        ...


class IRuntimeTaskManager(abc.ABC):
    @abc.abstractmethod
    def submit(self) -> bool:
        ...


class IMyrrhOs(ISystem, abc.ABC):
    @property
    @abc.abstractmethod
    def curdirb(self) -> bytes:
        ...

    @property
    @abc.abstractmethod
    def pardirb(self) -> bytes:
        ...

    @property
    @abc.abstractmethod
    def extsepb(self) -> bytes:
        ...

    @property
    @abc.abstractmethod
    def sepb(self) -> bytes:
        ...

    @property
    @abc.abstractmethod
    def pathsepb(self) -> bytes:
        ...

    @property
    @abc.abstractmethod
    def altsepb(self) -> bytes:
        ...

    @property
    @abc.abstractmethod
    def linesepb(self) -> bytes:
        ...

    @property
    @abc.abstractmethod
    def devnullb(self) -> bytes:
        ...

    @property
    @abc.abstractmethod
    def defpathb(self) -> bytes:
        ...

    @property
    @abc.abstractmethod
    def modules(self) -> dict[str, typing.Any]:
        ...

    @property
    @abc.abstractmethod
    def impls(self) -> dict[str, typing.Any]:
        ...

    @abc.abstractmethod
    def getbinb(self) -> dict[bytes, bytes]:
        ...

    @abc.abstractmethod
    def cwdb(self) -> bytes:
        ...

    @abc.abstractmethod
    def tmpdirb(self) -> bytes:
        ...

    @abc.abstractmethod
    def localcode(self) -> str:
        ...

    @abc.abstractmethod
    def getdefaultlocale(self) -> tuple[str]:
        ...

    @abc.abstractmethod
    def getpath(self, path: str | None = None) -> str:
        ...

    @abc.abstractmethod
    def getpathb(self, path: bytes | None = None) -> bytes:
        ...

    @abc.abstractmethod
    def envb(self) -> dict[bytes, bytes]:
        ...

    @abc.abstractmethod
    def getenvb(self, env: dict[bytes, bytes] | None = None) -> dict[bytes, bytes]:
        ...

    @abc.abstractmethod
    def getenv(self) -> dict[str, str]:
        ...

    @abc.abstractmethod
    def setenvb(self, env) -> None:
        ...

    @abc.abstractmethod
    def rdenvb(self) -> list[bytes]:
        ...

    @abc.abstractmethod
    def environkeyformat(self, key: bytes) -> bytes:
        ...

    @abc.abstractmethod
    def isabs(self, path: bytes) -> bool:
        ...

    @abc.abstractmethod
    def normpath(self, pathh: bytes) -> bytes:
        ...

    @abc.abstractmethod
    def joinpath(self, *args: list[bytes]) -> bytes:
        ...

    @abc.abstractmethod
    def basename(self, path: bytes) -> bytes:
        ...

    @abc.abstractmethod
    def dirname(self, path: bytes) -> bytes:
        ...

    @abc.abstractmethod
    def syspathb(self, path: bytes) -> bytes:
        ...

    @abc.abstractmethod
    def getshellscriptb(self, script: bytes) -> bytes:
        ...

    @abc.abstractmethod
    def getdefaultshellb(self, args: tuple[bytes, ...] = tuple()) -> bytes:
        ...

    @abc.abstractmethod
    def formatshellargs(self, args: list[bytes], *, defaultargs: list[bytes] | None = None) -> bytes:
        ...

    @abc.abstractmethod
    def sh_escape_bytes(self, string: bytes) -> bytes:
        ...

    @abc.abstractmethod
    def shellb(self) -> bytes:
        ...

    @abc.abstractmethod
    def shellargsb(self) -> list[bytes]:
        ...

    @abc.abstractmethod
    def cmd(self, cmdline: bytes, **kwargs) -> tuple[str, str, int]:
        ...

    @abc.abstractmethod
    def cmdb(self, cmdline: bytes, **kwargs) -> tuple[bytes, bytes, int]:
        ...

    @abc.abstractmethod
    def fsencoding(self) -> str:
        ...

    @abc.abstractmethod
    def fsencodeerrors(self) -> str:
        ...

    @abc.abstractmethod
    def defaultencoding(self) -> str:
        ...

    @abc.abstractmethod
    def shdecode(self, b: str | bytes, errors="surrogateescape") -> str:
        ...

    @abc.abstractmethod
    def shencode(self, s: str | bytes, errors="surrogateescape") -> bytes:
        ...

    @abc.abstractmethod
    def fsdecode(self, val: str | bytes) -> str:
        ...

    @abc.abstractmethod
    def fsencode(self, val: str | bytes) -> bytes:
        ...

    @abc.abstractmethod
    def fdcast(self, val: typing.Any, *, encoding: str | None = None) -> typing.Any:
        ...

    @abc.abstractmethod
    def fscast(self, val: typing.Any, *, encoding: str | None = None) -> typing.Any:
        ...

    @abc.abstractmethod
    def f(self, path: str | bytes | int, *, dir_fd: None | int = None) -> bytes:
        ...

    @abc.abstractmethod
    def p(self, path: str | bytes, *, dir_fd: None | int = None) -> bytes:
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


class IStream(IRuntimeObject):
    @property
    @abc.abstractmethod
    def eot(self) -> bool:
        ...

    @abc.abstractmethod
    def send_eot(self, eot: bool, id: int | None) -> bool:
        ...

    @abc.abstractmethod
    def sync(self, *, extras: dict[str, typing.Any] | None = None) -> None:
        ...

    @abc.abstractmethod
    def flush(self, *, extras: dict[str, typing.Any] | None = None) -> bytearray:
        ...

    @abc.abstractmethod
    def stat(self, *, extras: dict[str, typing.Any] | None = None) -> Stat:
        ...


class IInStream(IStream):
    @abc.abstractmethod
    def read(self, nbytes: int | None = None, *, extras: dict[str, typing.Any] | None = None) -> bytearray:
        ...


class IOutStream(IStream):
    @abc.abstractmethod
    def write(self, data: bytes, *, extras: dict[str, typing.Any] | None = None):
        ...


class IInOutStream(IInStream, IOutStream):
    ...


class IFileInStream(IInStream):
    @abc.abstractmethod
    def seek(self, nbytes: int, *, extras: dict[str, typing.Any] | None = None) -> int:
        ...


class IFileOutStream(IOutStream):
    @abc.abstractmethod
    def truncate(self, length: int, *, extras: dict[str, typing.Any] | None = None) -> None:
        ...

    @abc.abstractmethod
    def seek(self, nbytes: int, *, extras: dict[str, typing.Any] | None = None) -> int:
        ...


class IFileInOutStream(IFileInStream, IFileOutStream, IInOutStream):
    ...


class IProcess(ITask, IRuntimeObject):
    @property
    @abc.abstractmethod
    def pid(self) -> int:
        ...

    @property
    @abc.abstractmethod
    def exit_status(self, *, extras: dict[str, typing.Any] | None = None) -> int | None:
        ...

    @abc.abstractmethod
    def terminate(self, *, extras: dict[str, typing.Any] | None = None) -> None:
        ...

    @abc.abstractmethod
    def stat(self, *, extras=None) -> Stat:
        ...
