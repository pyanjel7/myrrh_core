# -*- coding: utf-8 -*-

"""
**Os environment module**
-------------------------
"""
import os
from myrrh.utils.mstring import typestr

from myrrh.core.interfaces import abstractmethod
from myrrh.core.services.system import AbcRuntime

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
        return self.myrrh_os.fsdecode(self.myrrh_os.linesepb)

    @property
    def environ(self):
        return self.myrrh_os.getenv()

    @environ.setter
    def environ(self, env):
        return self.myrrh_os.setenvb(env)

    @property
    def environb(self):
        return self.myrrh_os.getenvb()

    @environb.setter
    def environb(self, env):
        return self.myrrh_os.setenvb(env)

    @property
    @abstractmethod
    def name(self):
        ...

    def getenv(self, key, default=None):
        try:
            return self.environ[key]
        except KeyError:
            return self.myrrh_os.fsdecode(default)

    def getenvb(self, key, default=None):
        try:
            return self.environb[key]
        except KeyError:
            return self.myrrh_os.fsencode(default)

    def get_exec_path(self, env=None):
        if env and env.get(b"PATH") and env.get("PATH"):
            raise ValueError("env cannot contain 'PATH' and b'PATH' keys")

        if env is None:
            env = self.myrrh_os.getenvb()

        paths = env.get("PATH", env.get(b"PATH", self.myrrh_os.defpathb))

        return typestr(self.myrrh_os.fsencoding)([p for p in paths.split(self.myrrh_os.pathsepb)])

    @abstractmethod
    def putenv(self, key, value):
        ...

    @abstractmethod
    def unsetenv(self, key):
        ...

    @abstractmethod
    def gethome(self):
        ...

    @abstractmethod
    def gettemp(self):
        ...

    @abstractmethod
    def getlogin(self):
        ...

    @abstractmethod
    def geteuid(self):
        ...

    @abstractmethod
    def getegid(self):
        ...

    @abstractmethod
    def getuid(self):
        ...

    @abstractmethod
    def getgid(self):
        ...

    @abstractmethod
    def getgroups(self):
        ...

    def device_encoding(self, fd):
        # fd connected to a terminal unsupported => always None
        return None

    # Miscellaneous System Information

    @abstractmethod
    def cpu_count(self):
        ...
