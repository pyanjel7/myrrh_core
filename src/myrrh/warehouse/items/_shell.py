import typing

from ..item import BaseItem, DecodedStr, DecodedList, DecodedDict, Optional


class Shell(BaseItem[typing.Literal["shell"]]):
    path: Optional[DecodedStr]
    args: Optional[DecodedList]
    commands: Optional[DecodedDict]
