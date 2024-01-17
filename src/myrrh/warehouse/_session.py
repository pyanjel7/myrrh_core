import typing

import pydantic

from .item import BaseItem


class Session(BaseItem[typing.Literal["session"]]):
    login: int | str | None = None
    uid: int | str | None = None
    gid: int | str | None = None
    groups: str = ""
    privileges: str = ""
