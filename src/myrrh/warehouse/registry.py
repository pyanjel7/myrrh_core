import importlib
import typing
import pydantic
import functools

from myrrh.core.services import load_ext_group

from .item import BaseItem, NoneItemType, GenericItem
from ._system import System
from ._id import Id
from ._credentials import Credentials
from ._host import Host
from ._supply import Supply, Settings


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
    __single__: typing.Type["ItemRegistry"] | None = None

    warehouse_predefined_items = {
        System._type_(): System,
        Id._type_(): Id,
        Credentials._type_(): Credentials,
        Host._type_(): Host,
        NoneItemType._type_(): NoneItemType,
    }

    __warehouse_items__: dict[str, typing.Type[BaseItem]] = {}

    __warehouse_items__.update(warehouse_predefined_items)

    provider_settings: dict[str, typing.Any] = dict()

    generic = GenericItem

    def __new__(cls):
        if cls.__single__ is None:
            cls.__single__ = super().__new__(cls)
        return cls.__single__

    def __getattr__(self, name) -> typing.Type[BaseItem]:
        return self.get(name)

    def get(self, name) -> typing.Type[BaseItem]:
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
    def FactorySupply(self) -> typing.Type[Supply]:
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


def register_warehouse(module_name: str, item: str):
    module = importlib.import_module(module_name)
    item_cls = getattr(module, item)
    return ItemRegistry().register_warehouse(item_cls)


def register_provider_model(module_name: str, model: str):
    module = importlib.import_module(module_name)
    model_cls = getattr(module, model)
    return ItemRegistry().register_provider_model(model_cls)


load_ext_group("myrrh.warehouse.registry")
