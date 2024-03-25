# -*- coding: utf-8 -*-

"""
**Os environment module**
-------------------------
"""
import os

from myrrh.utils import mstring

from myrrh.utils.delegation import abstractmethod
from myrrh.core.system import AbcRuntime

__mlib__ = "AbcOsEnv"


class AbcOsEnv(AbcRuntime):
    __frameworkpath__ = "mpython._mosenv"

    __all__ = [
        "environ",
        "name",
        "linesep",
        "getenv",
        "putenv",
        "unsetenv",
        "gethome",
        "gettemp",
        "getlogin",
        "geteuid",
        "getegid",
        "getuid",
        "getgid",
        "getgroups",
        "device_encoding",
    ]

    uname_result = os.uname_result

    __all__.extend(["uname_result"])

    get_terminal_size = staticmethod(os.get_terminal_size)
    terminal_size = staticmethod(os.terminal_size)

    @property
    def linesep(self):
        return self.myrrh_os.linesep

    @property
    def environ(self):
        return self.myrrh_os.getenv()

    @environ.setter
    def environ(self, env):
        return self.myrrh_os.setenv(env)

    @property
    def environb(self):
        return mstring.encode(self.myrrh_os.getenv(), self.myrrh_os.fsencoding, self.myrrh_os.fsencodeerrors)

    @environb.setter
    def environb(self, env):
        return self.myrrh_os.setenv(mstring.decode(env))

    @property
    @abstractmethod
    def name(self): ...

    def getenv(self, key, default: str | None = None) -> str | None:
        try:
            return self.environ[key]
        except KeyError:
            return default

    def getenvb(self, key, default: bytes | None = None) -> bytes | None:
        try:
            return self.environb[key]
        except KeyError:
            return default

    def get_exec_path(self, env=None):
        if env and env.get("PATH") and env.get("PATH"):
            raise ValueError("env cannot contain 'PATH' and 'PATH' keys")

        if env is None:
            env = self.myrrh_os.getenv()

        paths = env.get("PATH", env.get("PATH", self.myrrh_os.defpathb))

        return mstring.typestr(self.myrrh_os.fsencoding)([p for p in paths.split(self.myrrh_os.pathsep)])

    @abstractmethod
    def putenv(self, key, value): ...

    @abstractmethod
    def unsetenv(self, key): ...

    @abstractmethod
    def gethome(self): ...

    @abstractmethod
    def gettemp(self): ...

    @abstractmethod
    def getlogin(self): ...

    @abstractmethod
    def geteuid(self): ...

    @abstractmethod
    def getegid(self): ...

    @abstractmethod
    def getuid(self): ...

    @abstractmethod
    def getgid(self): ...

    @abstractmethod
    def getgroups(self): ...

    def device_encoding(self, fd):
        # fd connected to a terminal unsupported => always None
        return None

    # Miscellaneous System Information

    @abstractmethod
    def cpu_count(self): ...
