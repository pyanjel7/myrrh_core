import typing

import pydantic

from myrrh.utils import mstring

from .item import BaseItem


class System(BaseItem[typing.Literal["system"]]):
    os: str = ""
    version: str = ""
    machine: str = ""

    fsencoding: str = ""
    fsencodeerrors: str = ""
    encoding: str = ""
    encoding_errors: str = ""
    localecode: str = ""

    eol: str = ""
    curdir: str = ""
    pardir: str = ""
    extsep: str = ""
    sep: str = ""
    pathsep: str = ""

    max_size: int | None = None

    cwd: str = ""
    devnull: str = ""

    tmpdirs: str = ""  # uses pathsep as separator
    defpaths: str = ""  # uses pathsep as separator
    shells: str = ""  # uses pathsep as separator

    module: str = ""  # specified the myrrhos specialized module used for the system
