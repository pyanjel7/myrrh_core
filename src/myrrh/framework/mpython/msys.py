import collections
import json
import typing

from myrrh.core.interfaces import abstractmethod, ABC
from myrrh.core.services.system import AbcRuntimeDelegate, ExecutionFailureCauseRVal
from myrrh.utils import mshlex

__mlib__ = "AbcSys"


class _interface(ABC):
    import sys as local_sys

    @property
    @abstractmethod
    def flags(self) -> typing.Any:
        ...

    @property
    @abstractmethod
    def maxsize(self) -> int:
        ...

    @property
    @abstractmethod
    def hash_info(self) -> typing.Any:
        ...

    @property
    @abstractmethod
    def _git(self) -> tuple:
        ...

    @abstractmethod
    def implementation(self) -> tuple:
        ...

    @property
    @abstractmethod
    def stderr(self) -> object:
        ...

    @property
    @abstractmethod
    def stdout(self) -> object:
        ...

    @property
    @abstractmethod
    def stdin(self) -> object:
        ...

    @property
    @abstractmethod
    def __stderr__(self) -> object:
        ...

    @property
    @abstractmethod
    def __stdout__(self) -> object:
        ...

    @property
    @abstractmethod
    def __stdin__(self) -> object:
        ...

    @abstractmethod
    def getsizeof(self, obj: object, default: int = ...) -> int:
        ...

    @abstractmethod
    def exc_info(self) -> tuple:
        ...

    @abstractmethod
    def audit(self, event, *args) -> None:
        ...


class AbcSys(_interface, AbcRuntimeDelegate):
    __frameworkpath__ = "mpython.msys"

    __all__ = [
        "local_sys",
        "maxsize",
        "prefix",
        "version",
        "path",
        "version_info",
        "base_prefix",
        "exec_prefix",
        "base_exec_prefix",
        "executable",
        "implementation",
        "platform",
    ]

    __version_info_tuple__ = collections.namedtuple("sys_version_info", "major minor micro releaselevel serial")  # type: ignore[name-match]

    attr_list = "('version', 'version_info', 'prefix', 'base_prefix', 'exec_prefix', 'base_exec_prefix', 'path', 'maxsize', 'abiflags')"

    _version = "0.0.0"
    _version_info = [0, 0, 0, "na", 0]
    _prefix = ""
    _base_prefix = ""
    _exec_prefix = ""
    _base_exec_prefix = ""
    _path: list[str] = []
    _maxsize = 2**31

    __plateform: str | None = None

    __delegated__ = {_interface: _interface.local_sys}
    __delegate_check_type__ = False

    def __init__(self, *a, **kwa):
        self.__delegate__(_interface, self.local_sys)

    @property
    def modules(self):
        return self.myrrh_os.__m_runtime_cache__.modules

    def _get_sys_attr(self, attr):
        instance_attr_name = "_%s" % attr

        try:
            executable = self._executable
        except ExecutionFailureCauseRVal:
            executable = b""

        if getattr(self, instance_attr_name) is getattr(self.__class__, instance_attr_name) and executable != b"":
            try:
                out, err, rval = self.myrrh_os.cmdb(
                    b'%s -c "import sys,json; print(json.dumps({n : getattr(sys, n) for n in %s if hasattr(sys, n) }))"'
                    % (
                        mshlex.dquote(executable),
                        self.myrrh_os.shencode(self.attr_list),
                    )
                )
                ExecutionFailureCauseRVal(self, err, rval, 0).check()
            except (ExecutionFailureCauseRVal, OSError):
                pass
            else:
                out = json.loads(self.myrrh_os.shdecode(out))
                for k, v in out.items():
                    setattr(self, "_%s" % k, v)

        return getattr(self, instance_attr_name)

    @property
    def prefix(self):
        return self._get_sys_attr("prefix")

    @property
    def version(self):
        return self._get_sys_attr("version")

    @version.setter
    def version(self, value):
        self._version = value

    @property
    def path(self):
        return self._get_sys_attr("path")

    @property
    def version_info(self):
        return self.__version_info_tuple__(*self._get_sys_attr("version_info"))

    @property
    def base_prefix(self):
        return self._get_sys_attr("base_prefix")

    @property
    def exec_prefix(self):
        return self._get_sys_attr("base_prefix")

    @property
    def base_exec_prefix(self):
        return self._get_sys_attr("base_exec_prefix")

    @property
    def executable(self):
        try:
            executable = self._executable
            if executable:
                return self.myrrh_os.shdecode(self._executable)
        except ExecutionFailureCauseRVal:
            pass

        raise AttributeError("sys.executable not supported on %s" % self.cfg.id) from None

    @property
    def platform(self):
        if self.__plateform is None:
            self.__plateform = self._platform

        return self.__plateform

    @platform.setter
    def platform(self, value):
        self.__plateform = value

    @property
    @abstractmethod
    def _platform(self):
        """This string contains a platform identifier that can be used to append platform-specific warehouse.
        the values are:
            Linux  => 'linux'
            Windows =>'win32'
        """

    @property
    @abstractmethod
    def _executable(self):
        """
        Python executable path
        """

    def getfilesystemencoding(self):
        return self.myrrh_os.fsencoding


setattr(
    AbcSys,
    "_implementation.__dict__",
    {
        "name": b"",
        "version": AbcSys._version,
        "hexversion": 0,
        "cache_tag": b"",
        "_multiarch": b"",
    },
)
