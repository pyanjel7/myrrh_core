import typing

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

    module: str = ""  # specified the myrrhos specialized module used for the system
