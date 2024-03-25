import typing

from ..item import BaseItem, DecodedStr, DecodedDict, Optional


class Directory(BaseItem[typing.Literal["directory"]]):

    executables: Optional[DecodedDict]
    disks: Optional[DecodedStr]
    devices: Optional[DecodedStr]

    devnull: Optional[DecodedStr]

    sep: Optional[DecodedStr]
    curdir: Optional[DecodedStr]
    pardir: Optional[DecodedStr]
    extsep: Optional[DecodedStr]
    pathsep: Optional[DecodedStr]

    tmpdirs: Optional[DecodedStr]  # uses pathsep as separator
    bindirs: Optional[DecodedStr]  # uses pathsep as separator
