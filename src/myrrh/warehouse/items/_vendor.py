import typing

from ..item import BaseItem, Optional


class Vendor(BaseItem[typing.Literal["vendor"]]):
    system_ext: Optional[dict]
    host_ext: Optional[dict]
    attrs: Optional[dict]
