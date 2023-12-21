# -*- coding: utf-8 -*-

#
# Part of this code is inspirated from or is a direct copy of the python subprocess module
#
# The python subprocess module code is licenced under this terms:
#
# Copyright (c) 2003-2005 by Peter Astrand <astrand@lysator.liu.se>
#
# Licensed to PSF under a Contributor Agreement.
# See http://www.python.org/2.4/license for licensing details.

"""
**SubProcess management module**
-----------
"""
import typing

from myrrh.core.interfaces import abstractmethod, ABC
from myrrh.core.services.system import AbcRuntimeDelegate

from myrrh.framework.mpython import mbuiltins

__mlib__ = "AbcSubProcess"


class _interface(ABC):
    import subprocess as local_subprocess

    @property
    @abstractmethod
    def _mswindows(self) -> bool:
        ...

    @property
    @abstractmethod
    def SubprocessError(self) -> local_subprocess.SubprocessError:
        ...

    @property
    @abstractmethod
    def CalledProcessError(self) -> local_subprocess.SubprocessError:
        ...

    @property
    @abstractmethod
    def TimeoutExpired(self) -> local_subprocess.SubprocessError:
        ...

    @property
    @abstractmethod
    def CompletedProcess(self) -> local_subprocess.CompletedProcess:
        ...

    @property
    @abstractmethod
    def Popen(self) -> local_subprocess.Popen:
        ...

    @property
    @abstractmethod
    def PIPE(self) -> int:
        ...

    @property
    @abstractmethod
    def DEVNULL(self) -> int:
        ...

    @property
    @abstractmethod
    def STDOUT(self) -> int:
        ...

    @property
    @abstractmethod
    def STARTF_USESHOWWINDOW(self) -> int:
        ...

    @property
    @abstractmethod
    def SW_HIDE(self) -> int:
        ...

    @property
    @abstractmethod
    def _USE_POSIX_SPAWN(self) -> bool:
        ...

    @property
    @abstractmethod
    def _active(self) -> list:
        ...

    @abstractmethod
    def _cleanup(self) -> None:
        ...

    @property
    @abstractmethod
    def STARTUPINFO(self) -> typing.Any:
        ...

    @abstractmethod
    def call(self, *popenargs, timeout=None, **kwargs) -> typing.Any:
        ...

    @abstractmethod
    def check_call(self, *popenargs, **kwargs) -> int:
        ...

    @abstractmethod
    def check_output(self, *popenargs, timeout=None, **kwargs) -> typing.Any:
        ...

    @abstractmethod
    def run(self, *popenargs, input=None, capture_output=False, timeout=None, check=False, **kwargs) -> local_subprocess.CompletedProcess:
        ...

    @abstractmethod
    def getoutput(self, cmd, *, encoding=None, errors=None) -> str:
        ...

    @abstractmethod
    def getstatusoutput(cmd, *, encoding=None, errors=None) -> tuple[int, str]:
        ...

    @abstractmethod
    def list2cmdline(self, seq: list) -> str:
        ...


class AbcSubProcess(_interface, AbcRuntimeDelegate):
    __frameworkpath__ = "mpython.msubprocess"

    __all__ = _interface.local_subprocess.__all__

    __delegated__ = {_interface: _interface.local_subprocess}
    __delegate_check_type__ = False

    def __init__(self, *a, **kwa):
        mod = mbuiltins.wrap_module(self.local_subprocess, self)
        self.__delegate__(_interface, mod)

        mod._USE_POSIX_SPAWN = not mod._mswindows
