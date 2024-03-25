import pydantic
import typing
import weakref

from ....warehouse.items import VolatileBaseItem

from ...interfaces import IESystem, IRuntimeObject, IProcess, IMyrrhOs

__all__ = ["init_cache"]


class _RuntimeItem(VolatileBaseItem[typing.Literal["runtime"]]):  # type: ignore[type-arg]
    modules: dict[str, typing.Any] = pydantic.Field(default_factory=dict)
    concretes: dict[str, IMyrrhOs] = pydantic.Field(default_factory=dict)
    fds: list[IRuntimeObject | None] = pydantic.Field(default_factory=list)
    procs: dict[int, IProcess] = pydantic.Field(default_factory=weakref.WeakValueDictionary)


def init_cache(system: IESystem):
    if not system.reg.runtime:
        system.reg.append(_RuntimeItem(), mode="keep")  # type: ignore[arg-type]