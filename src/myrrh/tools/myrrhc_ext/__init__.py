import importlib
import typing

from myrrh.core.services import load_ext_group
from ..myrrhc import cmd, types  # noqa: F401
from ..myrrhc.cmd import myrrhc_cmds  # noqa: F401


_extensions: dict[str, typing.Any] = dict()


def getsession():
    from myrrh.tools.myrrhc.session import getsession

    return getsession()


def load_commands(name):
    _extensions[name] = importlib.import_module(name)


load_ext_group("myrrh.tools.myrrhc_ext")
