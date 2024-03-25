import typing

from ..item import BaseItem, DecodedDict, DecodedList, Optional


class Vars(BaseItem[typing.Literal["vars"]]):
    readonly: Optional[DecodedList]
    defined: Optional[DecodedDict]
