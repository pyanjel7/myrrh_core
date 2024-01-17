import typing

import pydantic

from .item import BaseItem


class Shell(BaseItem[typing.Literal["shell"]]):
    shell: str = ""
    shellargs: tuple[str] = pydantic.Field(default_factory=tuple)
    commands: dict[str, str] = pydantic.Field(default_factory=dict)
