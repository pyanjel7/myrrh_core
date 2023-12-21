import pprint
import pydantic
import typing
import json

from myrrh.warehouse.item import NoneItem
from myrrh.core.services.entity import Entity, CoreProvider
from myrrh.provider import IProvider

from myrrh.provider.registry import ProviderRegistry
from myrrh.warehouse.registry import ItemRegistry


__all__ = ("Assembly",)


class _FactoryModel(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid", validate_assignment=True, validate_default=True, frozen=True)

    schema_: str = pydantic.Field("http://./myrrh/1.0/schema.json", alias="$schema")
    supply: ItemRegistry().FactorySupply  # type: ignore[valid-type]
    warehouse: list[ItemRegistry().WarehouseItemT] = pydantic.Field(default_factory=list)  # type: ignore[valid-type]

    @pydantic.field_validator("supply")
    def validate_supply(cls, supply, info):
        return supply


class Assembly:
    def __init__(self, supply={}, warehouse=list(), *, _model=None, _providers=None):
        self._providers = _providers

        if _model:
            self._factory = _model
        elif _providers:
            self._factory = _FactoryModel(supply={"paths": ["*"]}, warehouse=warehouse)
        else:
            self._factory = _FactoryModel(supply=supply, warehouse=warehouse)

    @classmethod
    def Warehouse(cls, *a, **kwa):
        return ItemRegistry().WarehouseItemT(*a, **kwa)

    @classmethod
    def Supply(cls, *a, **kwa):
        return ItemRegistry().FactorySupply(*a, **kwa)

    @classmethod
    def provider_name(cls, path: str) -> str:
        _, _, pname = path.rpartition("/")
        return pname

    @classmethod
    def fromProvider(cls, provider: typing.Type[IProvider], *, warehouse=list(), **kwargs):
        supply = ItemRegistry().FactorySupply(
            paths=[f"**/{provider._name_}"],
            settings=[{"name": provider._name_, **kwargs}],
        )
        return cls(supply=supply, warehouse=warehouse)

    @classmethod
    def fromObj(cls, obj):
        return cls(_model=_FactoryModel.model_validate(obj))

    @classmethod
    def fromRaw(cls, data):
        return cls(_model=_FactoryModel.model_validate_json(data))

    @classmethod
    def fromFile(cls, file):
        with open(file) as model:
            data = model.read()

        return cls(_model=_FactoryModel.model_validate_json(data))

    @classmethod
    def schema(cls, *a, **kwa):
        indent = kwa.pop("indent", None)
        return json.dumps(_FactoryModel.model_json_schema(*a, **kwa), indent=indent)

    @property
    def warehouse(self) -> list[ItemRegistry().WarehouseItemT]:  # type: ignore[valid-type]
        return self._factory.warehouse

    @property
    def supply(self) -> ItemRegistry().FactorySupply:  # type: ignore[valid-type]
        return self._factory.supply

    def _new_providers(self):
        if not self._providers:
            self._providers = list()

            for path in self.supply.paths:
                pname = self.provider_name(path)
                setting = next(filter(lambda p: p.name == pname, self.supply.settings), None)
                provider = getattr(ProviderRegistry(), pname)(setting)

                self._providers.append(provider)

        return CoreProvider(self._providers, patterns=self.supply.paths)

    def build(self) -> Entity:
        for prestep in self.supply.pre:
            pass

        provider = self._new_providers()

        entity = Entity(provider, self.warehouse)

        for poststep in self.supply.post:
            pass

        return entity

    def fromEntity(self, entity: Entity, only_predefined=True):
        if only_predefined:
            warehouse = entity.cfg.predefined()
        else:
            warehouse = entity.cfg.values()

        return self.__class__(supply=self.supply, warehouse=warehouse)

    def get_item(self, type_: str):
        t = [item for item in filter(lambda item: item.type_ == type_, self.warehouse)]
        if len(t) == 1:
            return t[0]

        return NoneItem

    def json(
        self,
        *,
        by_alias=True,
        exclude_defaults=True,
        exclude=None,
        exclude_unset=True,
        **kwa,
    ):
        exclude = exclude or {}
        exclude.update({"warehouse": {i for i in range(len(self.warehouse)) if self.warehouse[i].type_ == "null"}})
        return self._factory.model_dump_json(
            by_alias=by_alias,
            exclude=exclude,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            **kwa,
        )

    def pformat(self, *a, **kwa):
        return pprint.pformat(self._factory, *a, **kwa)

    def dict(self, *a, **kwa):
        return self._factory.model_dump(*a, **kwa)
