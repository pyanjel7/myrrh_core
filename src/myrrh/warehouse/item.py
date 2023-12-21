from __future__ import annotations

import typing
import datetime

import pydantic
import pydantic.json

from myrrh.core.services import cfg_init

__all__ = ["NoneItem", "BaseItem", "GenericItem", "NoneItemType"]

ItemT = typing.TypeVar("ItemT")


class BaseItem(pydantic.BaseModel, typing.Generic[ItemT]):
    _utc = cfg_init("dom_in_utc", False, section="myrrh.item")

    type_: ItemT = None  # type: ignore[assignment]

    DOM: pydantic.types.PastDatetime | None = None
    SLL: datetime.timedelta | None = None
    UBD: datetime.datetime | None = None
    UTC: bool = _utc

    model_config = pydantic.ConfigDict(extra="forbid", validate_assignment=True, frozen=True)

    def now(self):
        return datetime.datetime.utcnow if self.UTC else datetime.datetime.now

    def __bool__(self):
        return self.UBD is None or self.UBD >= self.now()

    @classmethod
    def _calc_ubd(cls, dom, sll):
        if sll == datetime.timedelta():
            return dom

        try:
            return dom + sll
        except OverflowError:
            pass

        return None

    @classmethod
    def _calc_dom(cls, dom, now) -> datetime.datetime:
        return dom if dom and dom < now else now

    @classmethod
    def _type_(cls):
        annotation = typing.get_args(cls.model_fields["type_"].annotation)

        if annotation:
            return annotation[0]

        return "generic"

    @pydantic.model_validator(mode="before")
    @classmethod
    def model_validation_before(cls, data):
        type_ = data.get("type_") or cls._type_()
        data["type_"] = type_

        utc = data.get("UTC", cls._utc)

        SLL = data.get("SLL")
        if SLL is not None and SLL < datetime.timedelta():
            raise ValueError("SLL must be a positive value")

        DOM = data.get("DOM")
        if SLL and DOM is None:
            now = datetime.datetime.utcnow() if utc else datetime.datetime.utcnow()
            DOM = cls._calc_dom(DOM, now)
            data["DOM"] = DOM

        UBD = data.get("UBD")
        if SLL and UBD is None:
            UBD = cls._calc_ubd(DOM, SLL)
            if UBD is not None:
                data["UBD"] = UBD

        return data

    @staticmethod
    def _serialize(*a, **kwa):
        pass

    @staticmethod
    def _val(val, **kwa):
        return val

    def model_dump_json(self, *, by_alias=False, exclude_defaults=True, **dumps_kwargs):
        return super().model_dump_json(by_alias=by_alias, exclude_defaults=exclude_defaults, **dumps_kwargs)

    def __hash__(self):
        return hash(self.type_)

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, item, value):
        setattr(self, item, value)

    def __repr__(self):
        return self.model_dump_json()


class GenericItem(BaseItem[str]):
    model_config = pydantic.ConfigDict(extra="allow")

    type_: str

    @pydantic.field_validator("type_")
    @classmethod
    def type_validate(cls, type_):
        from .registry import ItemRegistry

        if type_ in ItemRegistry.__warehouse_items__:
            raise ValueError(f'"{type_}" is not a valid item')

        return type_


class NoneItemType(BaseItem[typing.Literal["null"]]):
    def __bool__(self):
        return False

    def __getattr__(self, item):
        return self

    def __str__(self):
        return "na"


NoneItem = NoneItemType(type_="null")
