from __future__ import annotations


from myrrh.utils import mstring

import typing
import datetime

import pydantic
import pydantic.json
import pydantic_core

__all__ = ["NoneItem", "BaseItem", "GenericItem", "NoneItemType", "ColdGenericItem", "VolatileBaseItem"]

ItemT = typing.TypeVar("ItemT")


class _PydanticDecoded:
    @classmethod
    def __get_pydantic_core_schema__(cls, source: type[typing.Any], handler: pydantic.GetCoreSchemaHandler) -> pydantic_core.core_schema.CoreSchema:
        inner_schema: typing.Any

        if issubclass(source, DecodedStr):
            inner_schema = pydantic_core.core_schema.str_schema()
        elif issubclass(source, DecodedList):
            inner_schema = pydantic_core.core_schema.list_schema()
        elif issubclass(source, DecodedDict):
            inner_schema = pydantic_core.core_schema.dict_schema()
        else:
            inner_schema = pydantic_core.core_schema.bytes_schema()

        def serialize(value: mstring.Decoded[mstring.DecodedTypeVar]) -> str | list[str] | dict[str, str]:
            return value.d

        def validate(value, __f, info):
            if value is not NoneItem:
                return mstring.DecodedType(source, info.data.get("encoding") or source._encodings[0], info.data.get("encerrors") or source._encodings[1])(value)
            return source()

        schema = pydantic_core.core_schema.with_info_wrap_validator_function(
            validate,
            schema=inner_schema,
            serialization=pydantic_core.core_schema.plain_serializer_function_ser_schema(
                serialize,
                info_arg=False,
                return_schema=inner_schema,
                when_used="json",
            ),
        )
        return schema


class DecodedStr(mstring.MString, _PydanticDecoded): ...


class DecodedList(mstring.MList, _PydanticDecoded): ...


class DecodedDict(mstring.MDict, _PydanticDecoded): ...


class BaseItem(pydantic.BaseModel, typing.Generic[ItemT]):
    type_: ItemT = None  # type: ignore[assignment]

    DOM: pydantic.types.PastDatetime | None = None
    SLL: datetime.timedelta | None = None
    UBD: datetime.datetime | None = None
    UTC: bool | None = None

    label: str = ""
    tags: str = ""
    description: str = ""

    _encodings: tuple[str, str] = ("utf8", "strict")

    model_config = pydantic.ConfigDict(extra="forbid", validate_assignment=True, frozen=False, validate_default=True)

    encoding: str = "utf8"
    encerrors: str = "strict"

    def __bool__(self):
        return self.UBD is None or self.UBD >= self.now()

    def __hash__(self):
        return hash(self.type_)

    def __getitem__(self, path):
        attr = self

        if not path:
            return attr

        for p in path.split("."):
            if isinstance(attr, dict):
                attr = attr.get(p) or NoneItem
            elif isinstance(attr, list):
                attr = attr[int(p)] if len(attr) > int(p) else NoneItem
            else:
                attr = getattr(attr, p, NoneItem)

        return attr

    def __setitem__(self, path: str, value):
        self.update(path, value)

    def __repr__(self):
        return self.model_dump_json()

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

        return None

    @pydantic.model_validator(mode="before")
    @classmethod
    def model_validation_before(cls, data):
        if data is None:
            return

        type_ = (data and data.get("type_")) or cls._type_()
        if type_:
            data["type_"] = type_

        utc = data.get("UTC", False)

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

    def now(self):
        return datetime.datetime.utcnow if self.UTC else datetime.datetime.now

    def model_dump_json(self, *, by_alias=False, exclude_defaults=True, **dumps_kwargs):
        return super().model_dump_json(by_alias=by_alias, exclude_defaults=exclude_defaults, **dumps_kwargs)

    def _add_to_model_field_set(self, path: str):
        root, _, _ = path.partition(".")
        if root in self.model_fields:
            self.model_fields_set.add(root)

    @property
    def has_unset_fields(self):
        return not self.model_fields_set.issuperset(self.model_fields)

    def frozenpath(self, path: str) -> bool:
        root, _, _ = path.partition(".")
        return self.model_config.get("frozen") or getattr(self.model_fields.get(root), "frozen", False)

    def parent(self, path: str) -> tuple[typing.Any, str]:
        parent_name, attr = self.partition(path)
        if not attr:
            return self.parent(parent_name)

        parent = self.__getitem__(parent_name)

        if parent is NoneItem:
            raise ValueError(f'invalid path "{path}"", not a valid attribute')

        return parent, attr

    def partition(self, path: str):
        parent, _, attr = path.rpartition(".")

        return parent, attr

    def update(self, path: str, value):
        if self.frozenpath(path):
            raise ValueError(f"path {path} is frozen")

        attr = self.__getitem__(path)
        if attr is NoneItem:
            self.replace(path, value)
            return

        if value is NoneItem:
            self.replace(path, value)
            return

        if not isinstance(value, attr.__class__) and not (isinstance(value, dict) and isinstance(attr, pydantic.BaseModel)):
            try:
                value = attr.__class__(value)
            except Exception:
                raise TypeError(f"invalid type, value (={value.__class__}) is not instance of attribute class {attr.__class__}")

        if isinstance(attr, dict):
            attr.update(value)

        elif isinstance(attr, BaseItem):
            assert isinstance(value, dict)

            for k, v in value.items():
                attr.update(k, v)

        elif isinstance(attr, list):
            attr.extend(value)

        else:
            self.replace(path, value)

        self._add_to_model_field_set(path)

    def replace(self, path: str, value):
        if self.frozenpath(path):
            raise ValueError(f"path {path} is frozen")

        if value is NoneItem:
            self.delete(path)
            return

        parent, attr = self.parent(path)

        if isinstance(parent, dict):
            parent[attr] = value
        elif isinstance(parent, list):
            parent[int(attr)] = value
        else:
            setattr(parent, attr, value)

        self._add_to_model_field_set(path)

    def delete(self, path: str):
        if self.frozenpath(path):
            raise ValueError(f"path {path} is frozen")

        parent, attr = self.parent(path)

        if isinstance(parent, dict):
            parent.pop(attr)

        elif isinstance(parent, list):
            parent.pop(int(attr))
        else:
            delattr(parent, attr)

        if isinstance(parent, pydantic.BaseModel) and attr in parent.__pydantic_fields_set__:
            parent.__pydantic_fields_set__.remove(attr)

        self._add_to_model_field_set(path)

    def get(self, path: str, default=None):

        item = self[path]

        return default if item is NoneItem else item

    def pop(self, path: str, default=None):
        item = self[path]

        if item is not NoneItem:
            self.delete(path)
            return item

        return default

class VolatileBaseItem(BaseItem):
    model_config = pydantic.ConfigDict(
        arbitrary_types_allowed=True,
    )

    @pydantic.model_serializer
    def ser_model(self) -> dict[str, str]:
        return {
            "type_": self.type_,
            "label": self.label,
            "tags": ",".join((self.tags, "**volatile**")),
            "description": self.description,
        }


class GenericItem(BaseItem[typing.Literal["generic"]]):
    model_config = pydantic.ConfigDict(extra="allow")


class ColdGenericItem(BaseItem[typing.Literal["warm_generic"]]):
    model_config = pydantic.ConfigDict(extra="allow", frozen=True)


class NoneItemType(BaseItem[typing.Literal["null"]]):
    def __bool__(self):
        return False

    def __str__(self):
        return ""

    def __getattr__(self, item):
        try:
            return super().__getattr__(item)
        except AttributeError:
            pass

        return self

    @pydantic.model_serializer
    def ser_model(self) -> None:
        return None


NoneItem = NoneItemType(type_="null")

if False:
    _T = typing.TypeVar("_T")

    class Optional(typing.Generic[_T]): ...

else:

    @typing._SpecialForm  # type: ignore[no-redef, call-arg]
    def Optional(self, parameters):
        arg = typing._type_check(parameters, f"{self} requires a single type.")
        return typing.Annotated[typing.Union[arg, NoneItemType], pydantic.Field(default=NoneItem)]
