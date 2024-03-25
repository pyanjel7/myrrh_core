import functools
import importlib.util
import typing
import warnings

from abc import ABC, abstractmethod

from ...objects._registry import eregistry_property


from ....utils.mstring import typebytes, cast, typestr
from ....utils.delegation import ABCDelegation

from ...interfaces import (
    EProtocol,
    IMyrrhOs,
    IESystem,
    IECoreService,
    IECoreShellService,
    IECoreFileSystemService,
    IECoreStreamService,
)

from ..objects import MyrrhEnviron
from ..managers import init_cache
from ._syscall import RuntimeSyscall

__all__ = ("AbcMyrrhOs", "AbcRuntime", "AbcRuntimeDelegate")


def _validate_exe_args_values(command, working_dir, env):
    if env:
        for k, v in env.items():
            if "\x00" in k or "\x00" in v:
                raise ValueError("invalid environment value for %s: %s" % (k, v))
            if "=" in k:
                raise ValueError("invalid environment key %s" % k)
    if not command:
        raise ValueError("command parameter must not be empty")

    if "\x00" in command:
        raise ValueError("Invalid \\x00 not allowed in command")

    if working_dir and "\x00" in working_dir:
        raise ValueError("Invalid \\x00 not allowed in working directory")


class AbcMyrrhOs(IMyrrhOs, ABCDelegation):
    __delegated__ = (IESystem,)

    _name_ = "myrrhos"

    def __init__(self, system: IESystem):
        self.__delegate__(IESystem, system)

    @functools.cached_property
    def shell(self) -> IECoreShellService:
        return _RuntimeShell(self._delegate_.shell, self)  # type: ignore[attr-defined]

    @functools.cached_property
    def fs(self) -> IECoreFileSystemService:
        return _RuntimeFs(self._delegate_.fs, self)  # type: ignore[attr-defined]

    @functools.cached_property
    def stream(self) -> IECoreStreamService:
        return _RuntimeStream(self._delegate_.stream, self)  # type: ignore[attr-defined]

    def Stream(self, protocol: str | EProtocol | None = None) -> IECoreStreamService:
        return _RuntimeStream(self._delegate_.Stream(protocol), self)

    def Fs(self, protocol: str | EProtocol | None = None) -> IECoreFileSystemService:
        return _RuntimeFs(self._delegate_.Fs(protocol), self)

    def Shell(self, protocol: str | EProtocol | None = None) -> IECoreShellService:
        return _RuntimeShell(self._delegate_.Shell(protocol), self)

    def syspath(self, path: str) -> str:
        return self.normpath(self.joinpath(self.cwd or "", path))

    def getshellscript(self, script) -> str:
        return script

    curdir: str = eregistry_property("directory.curdir")  # type: ignore[assignment]
    pardir: str = eregistry_property("directory.pardir")  # type: ignore[assignment]
    extsep: str = eregistry_property("directory.extsep")  # type: ignore[assignment]
    sep: str = eregistry_property("directory.sep")  # type: ignore[assignment]
    pathsep: str = eregistry_property("directory.pathsep")  # type: ignore[assignment]
    altsep: str = eregistry_property("directory.altsep")  # type: ignore[assignment]
    devnull: str = eregistry_property("directory.devnull")  # type: ignore[assignment]

    linesep: str = eregistry_property("system.eol")  # type: ignore[assignment]

    defpath: str = eregistry_property("session.defpath")  # type: ignore[assignment]

    modules: dict[str, typing.Any] = eregistry_property("runtime.modules")  # type: ignore[assignment]
    concretes: dict[str, "AbcRuntime"] = eregistry_property("runtime.concretes")  # type: ignore[assignment]

    shellpath: str = eregistry_property("shell.path")  # type: ignore[assignment]
    shellargs: str = eregistry_property("shell.args")  # type: ignore[assignment]
    env: dict[str, str] = eregistry_property("vars.defined")  # type: ignore[assignment]
    cwd: str = eregistry_property("session.cwd")  # type: ignore[assignment]
    tmpdir: str = eregistry_property("session.tmpdir")  # type: ignore[assignment]

    rdenv: str = eregistry_property("vars.readonly")  # type: ignore[assignment]
    defaultencoding: str = eregistry_property("system.encoding")  # type: ignore[assignment]
    fsencoding: str = eregistry_property("directory.encoding")  # type: ignore[assignment]
    fsencodeerrors: str = eregistry_property("system.encerrors")  # type: ignore[assignment]
    localcode: str = eregistry_property("system.locale")  # type: ignore[assignment]
    getbin: dict[str, str] = eregistry_property("directory.executables")  # type: ignore[assignment]

    def cmd(self, cmdline, **kwargs):
        out, err, rval = self.cmdb(cmdline, **kwargs)
        return self.shdecode(out), self.shdecode(err), rval

    def cmdb(self, cmdline, **kwargs):
        try:
            kwargs.update(self.getbin)
            cmdline = cmdline % kwargs
        except KeyError as k:
            if not self.getbin:
                raise OSError("no executable list provided on the entity, check configuration")

            raise OSError(f"executable {k} not provided by the entity")

        working_dir = kwargs.get("execute_working_dir", None)
        env = kwargs.get("execute_env", None)
        out, err, rval = self.shell.execute(cmdline, working_dir=working_dir, env=env)

        return out.strip(), err.strip(), rval

    def shdecode(self, b, errors="surrogateescape") -> str:
        if not isinstance(b, bytes):
            return b
        return b.decode(encoding=self.defaultencoding, errors=errors)

    def shencode(self, s, errors="surrogateescape") -> bytes:
        if not isinstance(s, str):
            return s
        return s.encode(encoding=self.defaultencoding, errors=errors)

    def fsdecode(self, val) -> str:
        return typestr(encoding=self.fsencoding, errors=self.fsencodeerrors)(val)

    def fsencode(self, val) -> bytes:
        return typebytes(encoding=self.fsencoding, errors=self.fsencodeerrors)(val)

    def fdcast(self, val):
        try:
            if isinstance(val, int):
                val = str()
            return cast(val, encoding=self.fsencoding, errors=self.fsencodeerrors)

        except TypeError:
            return val.__class__

    def fscast(self, val):
        _type = self.fdcast(val)
        if issubclass(_type, self.PathLike):
            return cast(self._fspath_(val), encoding=self.fsencoding)
        return _type

    def shcast(self, val):
        return cast(val, encoding=self.defaultencoding)

    def getdefaultlocale(self):
        return self.localcode, self.defaultencoding

    def getdefaultshell(self, args=()):
        return [self.shellpath, *self.formatshellargs(args, defaultargs=self.shellargs)] if self.shellpath != "" else args

    def getpath(self, path: str | None = None):
        if path is None:
            return self.cwd

        if self.isabs(path):
            return self.normpath(path)

        return self.syspath(path)

    def getenv(self, env: dict[str, str] | None = None):
        if env is not None:
            return MyrrhEnviron(env)

        return MyrrhEnviron(self.env)

    def setenv(self, env: dict[str, str]):
        self.env = env

    from os import PathLike, fspath  # type: ignore[misc]

    _fspath_ = staticmethod(fspath)

    def f(self, path, *, dir_fd=None):
        if isinstance(path, int):
            return self.system.reg.runtime.fds[path].info

        return self.p(path, dir_fd=dir_fd)

    def p(self, path: str | bytes | bytearray | memoryview, *, dir_fd: int | None = None):
        try:
            path = self._fspath_(path)

            if isinstance(path, bytes):
                path = self.fsdecode(path)

            if not isinstance(path, str):
                raise TypeError

            if dir_fd is not None:
                path = self.joinpath(self.f(dir_fd), path)

            return path

        except TypeError:
            if isinstance(path, (bytearray, memoryview)):
                warnings.warn(
                    "%s type deprecated for path parameter" % path.__class__.__name__,
                    DeprecationWarning,
                )
                return self.p(bytes(path), dir_fd=dir_fd)

        raise TypeError("path should be string, bytes or os.PathLike, not {}".format(path.__class__.__name__))


class _RuntimeShell(IECoreShellService, IECoreService, ABCDelegation):
    __delegated__ = (IECoreShellService, IECoreService)

    def __init__(self, shell, runtime: AbcMyrrhOs):
        self.__delegate__(IECoreShellService, shell)

        self._runtime = runtime

    def _getenv(self, env):
        env = self._runtime.getenv(env)
        if env is None:
            return
        env = dict(env)
        for k in self._runtime.rdenv:
            env.pop(k, None)
        return dict(env)  # need to be a dict

    def execute(self, command, working_dir=None, env=None, *, extras=None):
        _validate_exe_args_values(command, working_dir, env)

        working_dir = self._runtime.getpath(working_dir)
        env = self._getenv(env)
        command = self._runtime.getshellscript(command)

        return self._delegate_.execute(command, working_dir, env, extras=extras)

    def spawn(self, command, working_dir=None, env=None, extras=None):
        _validate_exe_args_values(command, working_dir, env)

        working_dir = self._runtime.getpath(working_dir)
        env = self._getenv(env)
        return self._delegate_.spawn(command, working_dir, env, extras=extras)


class _RuntimeFs(IECoreFileSystemService, IECoreService, ABCDelegation):
    __delegated__ = (IECoreFileSystemService, IECoreService)

    def __init__(self, fs: IECoreFileSystemService, runtime: AbcMyrrhOs):
        self.__delegate__(IECoreFileSystemService, fs)

        self._runtime: AbcMyrrhOs = runtime

    def rm(self, file_path, *, extras=None):
        return self._delegate_.rm(self._runtime.getpath(file_path), extras=extras)

    def mkdir(self, path, *, extras=None):
        return self._delegate_.mkdir(self._runtime.getpath(path), extras=extras)

    def rmdir(self, path, *, extras=None):
        return self._delegate_.rmdir(self._runtime.getpath(path), extras=extras)

    def is_container(self, path, *, extras=None):
        return self._delegate_.is_container(self._runtime.getpath(path), extras=extras)

    def exist(self, path, *, extras=None):
        return self._delegate_.exist(self._runtime.getpath(path), extras=extras)

    def list(self, path, *, extras=None):
        return self._delegate_.list(self._runtime.getpath(path), extras=extras)

    def stat(self, path, *, extras=None):
        return self._delegate_.stat(self._runtime.getpath(path), extras=extras)


class _RuntimeStream(IECoreStreamService, ABCDelegation):
    __delegated__ = (IECoreStreamService, IECoreService)

    def __init__(self, stream: IECoreStreamService, runtime: IMyrrhOs):
        self.__delegate__(IECoreStreamService, stream)
        self._runtime = runtime

    def open_file(self, path: str, wiring: int, *, extras: dict | None = None) -> tuple[str, int]:
        return self._delegate_.open_file(self._runtime.getpath(path), wiring=wiring, extras=extras)

    def open_process(
        self,
        path: str,
        wiring: int,
        args: list[str],
        working_dir: str | None = None,
        env: dict[str, str] | None = None,
        *,
        extras: dict | None = None,
    ) -> tuple[str, int, int, int, int]:
        return self._delegate_.open_process(
            self._runtime.getpath(path),
            wiring=wiring,
            args=args,
            working_dir=working_dir,
            env=env,
            extras=extras,
        )


class AbcRuntime(ABC):
    __frameworkpath__: str
    __root_system__: IESystem

    def __new__(cls, system: IESystem):
        system: IESystem = getattr(system, "__root_system__", system)  #  type: ignore[assignment]
        init_cache(system)

        with system.lock:
            __frameworkpath__ = getattr(cls, "__frameworkpath__", None)

            if __frameworkpath__:
                if __frameworkpath__ in system.reg.runtime.concretes:
                    return system.reg.runtime.concretes[__frameworkpath__]

            clsname = cls.__name__

            myrrh_os = getattr(system, "__m_runtime_os__", None)
            myrrh_syscall = getattr(system, "__m_runtime_syscall__", None)

            arch = system.reg.system.os

            if not arch:
                raise TypeError('no system type specified for %s, required "posix" or "nt"' % system.reg.id)

            if not myrrh_os:
                mod_myrrhos_path = system.reg.system.myrrhos or f"myrrh.framework.arch.{arch}.myrrhos"

                mod_myrrhos = importlib.import_module(mod_myrrhos_path)

                myrrhos_cls = getattr(mod_myrrhos, "MyrrhOs")
                myrrh_os = myrrhos_cls(system)
                system.reg.add_warehouse(myrrh_os)

                myrrh_syscall = RuntimeSyscall(myrrh_os)

                setattr(system, "__m_runtime_os__", myrrh_os)
                setattr(system, "__m_runtime_syscall__", myrrh_syscall)

            if clsname.startswith("Abc"):
                try:
                    spec = importlib.util.find_spec(f"myrrh.framework.arch.{arch}.{cls.__frameworkpath__}")
                except ImportError:
                    pass
                else:
                    if spec:
                        mod = importlib.import_module(f"myrrh.framework.arch.{arch}.{cls.__frameworkpath__}")
                        clsname = getattr(mod, "__mlib__", None) or clsname
                        cls = getattr(mod, clsname)

            clsname = clsname[3:] if (clsname.startswith("Abc")) else clsname

            concrete_cls = type(
                clsname,
                (cls,),
                {
                    "__root_system__": system,
                    "myrrh_os": myrrh_os,
                    "myrrh_syscall": myrrh_syscall,
                    "__new__": ABC.__new__,
                },
            )

            self = concrete_cls()

            frameworkpath = getattr(self, "__frameworkpath__", None)
            if frameworkpath:
                try:
                    assert frameworkpath not in self.myrrh_os.concretes
                except AssertionError:
                    pass
                self.myrrh_os.concretes[frameworkpath] = self

            return self

    def __del__(self):
        frameworkpath = getattr(self, "__frameworkpath__", None)

        if frameworkpath:
            self.myrrh_os.concretes.pop(self.__frameworkpath__, None)

    @property
    @abstractmethod
    def myrrh_os(self) -> AbcMyrrhOs: ...

    @property
    @abstractmethod
    def myrrh_syscall(self) -> RuntimeSyscall: ...


class AbcRuntimeDelegate(AbcRuntime, ABCDelegation): ...
