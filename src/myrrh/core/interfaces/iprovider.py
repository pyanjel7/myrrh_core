import abc

from .ieservices import IEService

__all__ = ["IProvider"]


class IProvider(abc.ABC):
    _name_: str

    def __init_subclass__(cls, _name_=None) -> None:
        super().__init_subclass__()

        if _name_:
            cls._name_ = _name_
            return

        import inspect

        if not inspect.isabstract(cls):
            raise TypeError(f"Can't instantiate class provider {cls.__name__} without _name_ argument")

    @abc.abstractmethod
    def services(self) -> list[type[IEService]]: ...

    @abc.abstractmethod
    def subscribe(self, serv: type[IEService]) -> IEService | None: ...
