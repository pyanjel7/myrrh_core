import abc
import typing

from ._iservices import IEService

__all__ = ["IProvider"]


class IProvider(abc.ABC):

    @property
    # @classmethod
    @abc.abstractmethod
    def _name_(cls) -> str:
        ...

    @abc.abstractmethod
    def services(self) -> tuple[typing.Type[IEService]]:
        ...

    @abc.abstractmethod
    def catalog(self) -> tuple[str]:
        ...

    @abc.abstractmethod
    def deliver(self, name: str) -> dict | None:
        ...
