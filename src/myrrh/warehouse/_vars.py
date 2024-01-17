import typing

import pydantic

from .item import BaseItem


class Vars(BaseItem[typing.Literal["vars"]]):
    readonly: list[str] = pydantic.Field(default_factory=list)
    defined: dict[str, str] = pydantic.Field(default_factory=dict)
