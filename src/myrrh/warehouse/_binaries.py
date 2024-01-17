import typing

import pydantic

from .item import BaseItem


class Files(BaseItem[typing.Literal["files"]]):
    executables: dict[str, str] = pydantic.Field(default_factory=dict)
