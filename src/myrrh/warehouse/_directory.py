import typing

import pydantic

from .item import BaseItem


class Directory(BaseItem[typing.Literal["files"]]):
    os: str = ''
    executables: dict[str, str] = pydantic.Field(default_factory=dict)
    disks: dict[str, str] = pydantic.Field(default_factory=dict)
    
