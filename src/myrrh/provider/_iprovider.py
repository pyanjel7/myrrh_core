import abc
import typing

from ._iservices import IEntityService

__all__ = ["IProvider"]


class IProvider(abc.ABC):
    _name_: str  # reserved

    @abc.abstractmethod
    def services(self) -> tuple[typing.Type[IEntityService]]:
        ...

    @abc.abstractmethod
    def catalog(self) -> tuple[str]:
        ...

    @abc.abstractmethod
    def deliver(self, name: str) -> dict | None:
        ...
