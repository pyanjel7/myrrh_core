import typing

import pydantic

from .item import BaseItem


class Vendor(BaseItem[typing.Literal["vendor"]]):
    system_ext: dict = pydantic.Field(default_factory=dict)
    host_ext: dict = pydantic.Field(default_factory=dict)
    attrs: dict = pydantic.Field(default_factory=dict)
