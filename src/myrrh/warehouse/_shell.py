import typing

import pydantic

from .item import BaseItem


class Shell(BaseItem[typing.Literal["shell"]]):
    os: str = ""
    shell: str = ""
    shellargs: tuple[str] = pydantic.Field(default_factory=tuple)
    encoding: str = ""
    commands: dict[str, str] = pydantic.Field(default_factory=dict)
