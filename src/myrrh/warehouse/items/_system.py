import typing

from ..item import BaseItem, DecodedStr, Optional


class System(BaseItem[typing.Literal["system"]]):
    os: Optional[str]
    version: Optional[str]
    machine: Optional[str]

    locale: Optional[str]

    max_size: Optional[int]

    eol: Optional[DecodedStr]

    myrrhos: Optional[str]  # specified the myrrhos specialized module used for the system
