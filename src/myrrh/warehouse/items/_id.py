import typing

from ..item import BaseItem, Optional

_entity = 0


def id_generator():
    global _entity
    _entity += 1
    return f"entity{_entity}"


class Id(BaseItem[typing.Literal["id"]]):
    id: Optional[str]
    uuid: Optional[str]
    version: Optional[str]

    def __str__(self):
        return str(self.id)
