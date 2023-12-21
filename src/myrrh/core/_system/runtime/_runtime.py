import functools
import importlib.util
import warnings

from abc import ABC, abstractmethod
from myrrh.utils.mstring import typebytes, cast, typestr

from ...interfaces import (
    IMyrrhOs,
    ISystem,
    ICoreService,
    ICoreShellService,
    ICoreFileSystemService,
    ICoreStreamService,
    ABCDelegation,
)
from ....provider import Protocol

from ..objects import MyrrhEnviron
from ..managers import RuntimeCache, init_cache, runtime_cached_property, Acquiring
from ._syscall import RuntimeSyscall

__all__ = ("AbcMyrrhOs", "AbcRuntime", "AbcRuntimeDelegate")


def _validate_exe_args_values(command, working_dir, env):
    if env:
        for k, v in env.items():
            if b"\x00" in k or b"\x00" in v:
                raise ValueError("invalid environment value for %s: %s" % (k, v))
            if b"=" in k:
                raise ValueError("invalid environment key %s" % k)
    if not command:
        raise ValueError("command parameter must not be empty")

    if b"\x00" in command:
        raise ValueError("Invalid \\x00 not allowed in command")

    if working_dir and b"\x00" in working_dir:
        raise ValueError("Invalid \\x00 not allowed in working directory")


class AbcMyrrhOs(IMyrrhOs, ABCDelegation):
    @property
    @abstractmethod
    def _curdirb_(self):
        ...

    @property
    @abstractmethod
    def _pardirb_(self):
        ...

    @property
    @abstractmethod
    def _extsepb_(self):
        ...

    @property
    @abstractmethod
    def _sepb_(self):
        ...

    @property
    @abstractmethod
    def _pathsepb_(self):
        ...

    @property
    @abstractmethod
    def _altsepb_(self):
        ...

    @property
    @abstractmethod
    def _defpathb_(self):
        ...

    @property
    @abstractmethod
    def _devnullb_(self):
        ...

    @property
    @abstractmethod
    def _linesepb_(self):
        ...

    @abstractmethod
    def _getbinb_(self):
        ...

    @abstractmethod
    def _envb_(self):
        ...

    @abstractmethod
    def _getcwdb_(self):
        ...

    @abstractmethod
    def _gettmpdirb_(self):
        ...

    @abstractmethod
    def _localecode_(self):
        ...

    @abstractmethod
    def _fsencoding_(self):
        ...

    @abstractmethod
    def _fsencodeerrors_(self):
        ...

    @abstractmethod
    def _getdefaultencoding_(self):
        ...

    @abstractmethod
    def _getdefaultshellb_(self):
        ...

    @abstractmethod
    def _getdefaultshellargsb_(self):
        ...

    @abstractmethod
    def _getreadonlyenvb_(self):
        ...

    __delegated__ = (ISystem,)

    def __init__(self, system: ISystem):
        self.__delegate__(ISystem, system)

    @functools.cached_property
    def shell(self) -> ICoreShellService:
        return _RuntimeShell(self._delegate_.shell, self)  # type: ignore[attr-defined]

    @functools.cached_property
    def fs(self) -> ICoreFileSystemService:
        return _RuntimeFs(self._delegate_.fs, self)  # type: ignore[attr-defined]

    @functools.cached_property
    def stream(self) -> ICoreStreamService:
        return _RuntimeStream(self._delegate_.stream, self)  # type: ignore[attr-defined]

    def Stream(self, protocol: str | Protocol | None = None) -> ICoreStreamService:
        return _RuntimeStream(self._delegate_.Stream(protocol), self)

    def Fs(self, protocol: str | Protocol | None = None) -> ICoreFileSystemService:
        return _RuntimeFs(self._delegate_.Fs(protocol), self)

    def Shell(self, protocol: str | Protocol | None = None) -> ICoreShellService:
        return _RuntimeShell(self._delegate_.Shell(protocol), self)

    def syspathb(self, path):
        return self.normpath(self.joinpath(self.cwdb or b"", path))

    def getshellscriptb(self, script):
        return script

    curdirb = runtime_cached_property("curdirb")("_curdirb_")  # type: ignore[assignment]
    pardirb = runtime_cached_property("pardirb")("_pardirb_")  # type: ignore[assignment]
    extsepb = runtime_cached_property("extsepb")("_extsepb_")  # type: ignore[assignment]
    sepb = runtime_cached_property("sepb")("_sepb_")  # type: ignore[assignment]
    pathsepb = runtime_cached_property("pathsepb")("_pathsepb_")  # type: ignore[assignment]
    altsepb = runtime_cached_property("altsepb")("_altsepb_")  # type: ignore[assignment]
    linesepb = runtime_cached_property("linesepb")("_linesepb_")  # type: ignore[assignment]
    defpathb = runtime_cached_property("defpathb", init_cfg_path="system.defpathb")("_defpathb_")  # type: ignore[assignment]
    devnullb = runtime_cached_property("devnullb", init_cfg_path="system.devnullb")("_devnullb_")  # type: ignore[assignment]

    @runtime_cached_property("_shellb", init_cfg_path="system.shellb")
    def shellb(self):
        return self._getdefaultshellb_()

    @runtime_cached_property("_shellargsb", init_cfg_path="system.shellargsb")
    def shellargsb(self):
        return self._getdefaultshellargsb_()

    @runtime_cached_property("envb", init_value=dict(), init_cfg_path="system.envb")
    def envb(self):
        new_env = MyrrhEnviron({}, conv=self.fsencode, keyformat=self.environkeyformat)

        try:
            environ = self._envb_()
        except OSError:
            return new_env

        new_env.update(environ)

        return new_env

    @runtime_cached_property("cwdb", init_cfg_path="system.cwdb")
    def cwdb(self):
        return self._getcwdb_()

    @runtime_cached_property("tmpdirb", init_cfg_path="system.tmpdirb")
    def tmpdirb(self):
        return self._gettmpdirb_()

    @runtime_cached_property("rdenvb", init_cfg_path="system.rdenvb")
    def rdenvb(self):
        return self._getreadonlyenvb_()

    @runtime_cached_property("encoding", init_cfg_path="system.encoding")
    def defaultencoding(self):
        return self._getdefaultencoding_()

    @runtime_cached_property("fsencoding", init_cfg_path="system.fsencoding")
    def fsencoding(self):
        return self._fsencoding_()

    @runtime_cached_property("fsencodeerrors", init_cfg_path="system.fsencodeerrors")
    def fsencodeerrors(self):
        return self._fsencodeerrors_()

    @runtime_cached_property("localecode", init_cfg_path="system.localecode")
    def localcode(self):
        return self._localecode_()

    @runtime_cached_property("binb", init_cfg_path="system.binb")
    def getbinb(self):
        return self._getbinb_()

    @runtime_cached_property("modules", init_at_creation_time=True)
    def modules(self):
        return dict()

    @runtime_cached_property("impls", init_at_creation_time=True)
    def impls(self):
        return dict()

    def cmd(self, cmdline, **kwargs):
        out, err, rval = self.cmdb(cmdline, **kwargs)
        return self.shdecode(out), self.shdecode(err), rval

    def cmdb(self, cmdline, **kwargs):
        try:
            kwargs = {k.encode(): v for k, v in kwargs.items()}
            kwargs.update(self.getbinb)
            cmdline = cmdline % kwargs
        except KeyError as k:
            if not self.getbinb:
                raise OSError("Usable binaries list is empty, provider connection too long or failure?")

            raise OSError("%s not found on system" % k)

        working_dir = kwargs.get(b"execute_working_dir", None)
        env = kwargs.get(b"execute_env", None)
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

    def getdefaultshellb(self, args=()):
        return [self.shellb, *self.formatshellargs(args, defaultargs=self.shellargsb)] if self.shellb != b"" else args

    def getpathb(self, path=None):
        if path is None:
            return self.cwdb

        path = self.fsencode(path)

        if self.isabs(path):
            return self.normpath(path)

        return self.syspathb(path)

    def getenvb(self, env=None):
        if env is not None:
            _env = MyrrhEnviron({}, conv=self.fsencode)
            _env.update(env)
            return _env

        return self.envb

    def getpath(self, path=None):
        return self.fsdecode(self.getpathb(self.fsencode(path)))

    def getenv(self):
        return MyrrhEnviron(self.getenvb(), conv=self.fsdecode, keyformat=self.environkeyformat)

    def setenvb(self, env):
        conv = self.fsencode
        new_env = MyrrhEnviron({}, conv=conv, keyformat=self.environkeyformat)
        new_env.update(env)
        self.envb = new_env

    from os import PathLike, fspath  # type: ignore[misc]

    _fspath_ = staticmethod(fspath)

    def f(self, path, *, dir_fd=None):
        if isinstance(path, int):
            return self._get_runtime_object_(path).info

        return self.p(path, dir_fd=dir_fd)

    def p(self, path, *, dir_fd=None):
        try:
            path = self._fspath_(path)

            if isinstance(path, str):
                path = self.fsencode(path)

            if dir_fd is not None:
                path = self.join(self.f(dir_fd), path)

            return path

        except TypeError:
            if isinstance(path, (bytearray, memoryview)):
                warnings.warn(
                    "%s type deprecated for path parameter" % path.__class__.__name__,
                    DeprecationWarning,
                )
                return self.p(bytes(path), dir_fd=dir_fd)

        raise TypeError("path should be string, bytes or os.PathLike, not {}".format(path.__class__.__name__))


class _RuntimeShell(ICoreShellService, ICoreService, ABCDelegation):
    __delegated__ = (ICoreShellService, ICoreService)

    def __init__(self, shell, runtime: AbcMyrrhOs):
        self.__delegate__(ICoreShellService, shell)

        self._runtime = runtime

    def _getenv(self, env):
        env = self._runtime.getenvb(env)
        if env is None:
            return
        env = dict(env)
        for k in self._runtime.rdenvb:
            env.pop(k, None)
        return dict(env)  # need to be a dict

    def execute(self, command, working_dir=None, env=None, *, extras=None):
        _validate_exe_args_values(command, working_dir, env)

        try:
            working_dir = self._runtime.getpathb(working_dir)
        except Acquiring:
            working_dir = None
        try:
            env = self._getenv(env)
        except Acquiring:
            env = None
        try:
            command = self._runtime.getshellscriptb(command)
        except Acquiring:
            pass

        return self._delegate_.execute(command, working_dir, env, extras=extras)

    def spawn(self, command, working_dir=None, env=None, extras=None):
        _validate_exe_args_values(command, working_dir, env)

        working_dir = self._runtime.getpathb(working_dir)
        env = self._getenv(env)
        return self._delegate_.spawn(command, working_dir, env, extras=extras)


class _RuntimeFs(ICoreFileSystemService, ICoreService, ABCDelegation):
    __delegated__ = (ICoreFileSystemService, ICoreService)

    def __init__(self, fs: ICoreFileSystemService, runtime: AbcMyrrhOs):
        self.__delegate__(ICoreFileSystemService, fs)

        self._runtime: AbcMyrrhOs = runtime

    def rm(self, file_path, *, extras=None):
        return self._delegate_.rm(self._runtime.getpathb(file_path), extras=extras)

    def mkdir(self, path, *, extras=None):
        return self._delegate_.mkdir(self._runtime.getpathb(path), extras=extras)

    def rmdir(self, path, *, extras=None):
        return self._delegate_.rmdir(self._runtime.getpathb(path), extras=extras)

    def is_container(self, path, *, extras=None):
        return self._delegate_.is_container(self._runtime.getpathb(path), extras=extras)

    def exist(self, path, *, extras=None):
        return self._delegate_.exist(self._runtime.getpathb(path), extras=extras)

    def list(self, path, *, extras=None):
        return self._delegate_.list(self._runtime.getpathb(path), extras=extras)

    def stat(self, path, *, extras=None):
        return self._delegate_.stat(self._runtime.getpathb(path), extras=extras)


class _RuntimeStream(ICoreStreamService, ABCDelegation):
    __delegated__ = (ICoreStreamService, ICoreService)

    def __init__(self, stream: ICoreStreamService, runtime: IMyrrhOs):
        self.__delegate__(ICoreStreamService, stream)
        self._runtime = runtime

    def open_file(self, path: bytes, wiring: int, *, extras: dict | None = None) -> tuple[bytes, int]:
        return self._delegate_.open_file(self._runtime.getpathb(path), wiring=wiring, extras=extras)

    def open_process(
        self,
        path: bytes,
        wiring: int,
        args: list[bytes],
        working_dir: bytes | None = None,
        env: dict[bytes, bytes] | None = None,
        *,
        extras: dict | None = None,
    ) -> tuple[bytes, int, int, int, int]:
        return self._delegate_.open_process(
            self._runtime.getpathb(path),
            wiring=wiring,
            args=args,
            working_dir=working_dir,
            env=env,
            extras=extras,
        )


class AbcRuntime(ABC):
    __frameworkpath__: str
    __root_system__: ISystem

    def __new__(cls, system: ISystem):
        system = getattr(system, "__root_system__", system)

        with system.lock:
            __frameworkpath__ = getattr(cls, "__frameworkpath__", None)
            cache: RuntimeCache = getattr(system, "__m_runtime_cache__", None)  # type: ignore[assignment]

            if __frameworkpath__ and cache:
                impls = cache.get("impls") or tuple()

                if __frameworkpath__ in impls:
                    return impls[__frameworkpath__]

            clsname = cls.__name__

            myrrh_os = getattr(system, "__m_runtime_os__", None)
            myrrh_syscall = getattr(system, "__m_runtime_syscall__", None)

            arch = system.cfg.system.os

            if not arch:
                raise TypeError('no system type specified for %s, required "posix" or "nt"' % system.cfg.id)

            if not myrrh_os:
                modsys = importlib.import_module(f"myrrh.framework.arch.{arch}.myrrhos")
                myrrhos_cls = getattr(modsys, "MyrrhOs")
                myrrh_os = myrrhos_cls(system)

                myrrh_syscall = RuntimeSyscall(myrrh_os)
                myrrh_cache = RuntimeCache()

                init_cache(myrrh_cache, myrrh_os)
                init_cache(myrrh_cache, myrrh_syscall)

                setattr(system, "__m_runtime_os__", myrrh_os)
                setattr(system, "__m_runtime_syscall__", myrrh_syscall)
                setattr(system, "__m_runtime_cache__", myrrh_cache)

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
                    assert frameworkpath not in self.myrrh_os.impls
                except AssertionError:
                    pass
                self.myrrh_os.impls[frameworkpath] = self

            return self

    def __del__(self):
        cache = getattr(self.__root_system__, "__m_runtime_cache__", None)
        frameworkpath = getattr(self, "__frameworkpath__", None)

        if cache and frameworkpath:
            cache["impls"].pop(self.__frameworkpath__, None)

    @property
    @abstractmethod
    def myrrh_os(self) -> AbcMyrrhOs:
        ...

    @property
    @abstractmethod
    def myrrh_syscall(self) -> RuntimeSyscall:
        ...


class AbcRuntimeDelegate(AbcRuntime, ABCDelegation):
    ...
