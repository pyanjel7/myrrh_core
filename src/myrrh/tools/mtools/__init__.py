import typing

from . import mjson
from . import msecrets
from . import mcfg

cmds: list[typing.Callable] = []

cmds.extend((getattr(mjson, c) for c in mjson.__all__))
cmds.extend((getattr(msecrets, c) for c in msecrets.__all__))
cmds.extend((getattr(mcfg, c) for c in mcfg.__all__))
