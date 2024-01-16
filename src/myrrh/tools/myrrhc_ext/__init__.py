import importlib
import typing

from myrrh.core.services.plugins import load_ext_group
from ..myrrhc import cmd, types
from ..myrrhc.cmd import myrrhc_cmds

__all__ = ["getsession", "load_commands", "cmd", "types", "myrrhc_cmds"]

_extensions: dict[str, typing.Any] = dict()


def getsession():
    from myrrh.tools.myrrhc.session import getsession

    return getsession()


def load_commands(name):
    _extensions[name] = importlib.import_module(name)


load_ext_group("myrrh.tools.myrrhc_ext")
