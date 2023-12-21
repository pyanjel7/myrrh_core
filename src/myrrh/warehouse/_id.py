import pydantic
import uuid as _uuid
from myrrh.core.services import __version__
import typing

from .item import BaseItem

_entity = 0


def id_generator():
    global _entity
    _entity += 1
    return f"entity{_entity}"


class Id(BaseItem[typing.Literal["id"]]):
    id: str = pydantic.Field(default_factory=id_generator)
    uuid: _uuid.UUID = pydantic.Field(default=str(_uuid.UUID(int=0)))
    version: str = __version__

    def __str__(self):
        return str(self.id)
