import importlib
import typing
import pydantic
import functools

from myrrh.core.services.plugins import load_ext_group

import myrrh.warehouse.items

from .items import BaseItem, GenericItem, Settings, Supply

__all__ = ["GenericItem", "ProviderSettings", "ItemRegistry", "register_warehouse", "register_provider_settings"]


class ProviderSettings(Settings):
    model_config = pydantic.ConfigDict(
        extra="allow",
    )
    name: str

    @pydantic.field_validator("name")
    @classmethod
    def name_validate(cls, name, info):
        if name in ItemRegistry.provider_settings:
            raise ValueError(f'"{name}" is not a valid model')

        return name


class ItemRegistry:
    __single__: type["ItemRegistry"] | None = None

    warehouse_predefined_items = {t: getattr(myrrh.warehouse.items, t) for t in myrrh.warehouse.items.__items__ if getattr(getattr(myrrh.warehouse.items, t, None), "_type_", None)}

    __warehouse_items__: dict[str, type[BaseItem]] = {}

    __warehouse_items__.update(warehouse_predefined_items)

    provider_settings: dict[str, typing.Any] = dict()

    generic = GenericItem

    def __new__(cls):
        if cls.__single__ is None:
            cls.__single__ = super().__new__(cls)
        return cls.__single__

    def __getattr__(self, name) -> type[BaseItem]:
        return self.get(name)

    def get(self, name) -> type[BaseItem]:
        try:
            return self.__warehouse_items__[name]
        except KeyError:
            pass

        raise AttributeError(f'{name} is not a valid item name, available items: {", ".join(self.items)}')

    @property
    def items(self):
        return self.__warehouse_items__

    @functools.cached_property
    def ProviderModelT(self):
        if len(self.provider_settings) > 1:
            return typing.Annotated[typing.Union[*self.provider_settings.values()], pydantic.Field(discriminator="name")] | ProviderSettings  # type: ignore

        if len(self.provider_settings):
            return [p for p in self.provider_settings.values()][0] | ProviderSettings

        return ProviderSettings

    @functools.cached_property
    def WarehouseItemT(self):
        return typing.Annotated[typing.Union[*self.warehouse_predefined_items.values()], pydantic.Field(discriminator="type_")] | GenericItem  # type: ignore

    @property
    def FactorySupply(self) -> type[Supply]:
        return Supply[self.ProviderModelT]  # type: ignore[name-defined]

    def warehouse_model_validate(self, *a, **kwa):
        cls = pydantic.TypeAdapter(self.WarehouseItemT).validate_python(*a, **kwa)
        return cls

    def provider_model_validate(self, *a, **kwa):
        cls = pydantic.TypeAdapter(self.ProviderModelT).validate_python(*a, **kwa)
        return cls

    def register_warehouse(self, item_cls):
        self.warehouse_predefined_items[item_cls._type_()] = item_cls
        self.__warehouse_items__[item_cls._type_()] = item_cls
        try:
            del self.WarehouseItemT
        except AttributeError:
            pass

    def register_provider_model(self, provider_model: ProviderSettings):
        for value in typing.get_args(provider_model.model_fields["name"].annotation):
            self.provider_settings[value] = provider_model
        try:
            del self.ProviderModelT
        except AttributeError:
            pass


def register_warehouse(module: str):
    mod = importlib.import_module(module)
    item_cls = getattr(mod, "WarehouseItem")

    if not isinstance(item_cls, (list, tuple)):
        item_cls = [item_cls]

    for item in item_cls:
        return ItemRegistry().register_warehouse(item)


def register_provider_settings(module: str):
    mod = importlib.import_module(module)
    model_cls = getattr(mod, "ProviderSettings")

    if not isinstance(model_cls, (list, tuple)):
        model_cls = [model_cls]

    for model in model_cls:
        ItemRegistry().register_provider_model(model)


load_ext_group("myrrh.warehouse.registry")
