import functools
import threading
import warnings
import weakref
import typing
from myrrh.core.interfaces.ieregistry import IBaseItem

import pydantic

from ..interfaces import IERegistry, IEWarehouseService, IERegistrySupplier
from ..services import config

from ...utils.delegation import ABCDelegation
from ...warehouse import utils
from ...warehouse.items import NoneItem
from ...warehouse.registry import ItemRegistry


__all__ = ["ERegistry", "eregistry_property"]


class ERegistry_Static(IERegistry, ABCDelegation):

    __delegated__ = (IERegistry,)

    def __init__(self, deleg: IERegistry):
        self.__delegate__(IERegistry, deleg)

    def __getattr__(self, name) -> typing.Any:
        return self.get(name)

    def __setattr__(self, name: str, value: typing.Any) -> None:
        if name != "lock" and not name.startswith("_"):
            return self._delegate_.__setattr__(name, value)

        super().__setattr__(name, value)

    def __getitem__(self, path):
        return self._delegate_.get_static(path)

    def get(self, *a, **kwa):
        return self._delegate_.get_static(*a, **kwa)

    def values(self) -> list[IBaseItem]:
        return self._delegate_.defined_values()
    
class ERegistry(IERegistry):
    __eid__: dict[str, weakref.WeakSet] = dict()
    _item_providers: dict[str, list[IEWarehouseService]]

    def __init__(self, items: list[ItemRegistry().WarehouseItemT]):  # type: ignore[valid-type]
        dict.__init__(self)

        self.lock = threading.RLock()
        self._item_providers = {"*": list()}
        self._meta = {}

        self._predefined_items = {item.type_: item for item in items}

    def __setattr__(self, name, value):
        if name != "lock" and not name.startswith("_"):
            self[name] = value
            return

        super(dict, self).__setattr__(name, value)

    def __getattr__(self, name):
        try:
            if not name.startswith("_"):
                return self[name]
        except KeyError:
            pass

        raise AttributeError(name)

    def _register_meta(self, item: dict):
        type = item.get('type_')
        if type is None:
            return
        
        meta = {k: v for k, v in item.items() if k.startswith('@')}
        for k in meta:
            item.pop(k)

        self._meta.update(meta)

    def get_meta(self, key):
        return self._meta.get(key)
    
    def search_in_providers(self, path):
        item_type = utils.get_item_type(path)

        item_provider = self._item_providers.get(item_type) or self._item_providers["*"]

        item = {}
        for p in item_provider:
            try:
                item.update(p.deliver(item, path) or dict())
            except Exception as e:
                warnings.warn(
                    f'a warehouse failed to provide a required item "{item_type}" : {e}',
                    UserWarning,
                )

        return item

    def __getitem__(self, path):
        return self.get(path)

    def _add_warehouse_provider(self, name, serv, index):
        item_providers = self._item_providers.get(name) or list(self._item_providers["*"])

        if index is None:
            item_providers.append(serv)
        else:
            item_providers.insert(index, serv)

        self._item_providers[name] = item_providers

    def add_warehouse(self, serv: IEWarehouseService, *, index=None):
        with self.lock:
            for name in serv.catalog():
                self._add_warehouse_provider(name, serv, index)

                if name != "*":
                    self[name] = NoneItem
                else:
                    for name in self._item_providers:
                        if name != "*":
                            self._add_warehouse_provider(name, serv, index)

    def predefined(self):
        with self.lock:
            return list(self._predefined_items.values())

    def defined_values(self):
        with self.lock:
            return list(filter(None, dict.values(self)))

    def values(self):
        with self.lock:
            return list(self[item] for item in self)

    def get_static(self, path, default=NoneItem):
        with self.lock:
            name, paths = utils.item_splitpath(path)
            item = dict.get(self, name, NoneItem)

            if paths:
                item = item.__getitem__(paths)

            return item

    def get(self, path, default=NoneItem):
        name, paths = utils.item_splitpath(path)

        with self.lock:
            item = self.get_static(path)

            if item is NoneItem:

                idict = self.search_in_providers(name)
                if idict:
                    idict["type_"] = utils.get_item_type(path)
                    self.append(idict)

                item = dict.get(self, name, NoneItem)

                if paths:
                    item = item.__getitem__(paths)

            if item is NoneItem:
                return default

            return item

    def set(self, path, value):
        with self.lock:
            name, _, paths = path.partition(".")

            item = self.get(name)

            item[paths] = value

    def append(self, item, mode="update"):
        with self.lock:
            if not item:
                return

            if isinstance(item, dict):
                mode = item.pop('@mode@', mode)
                self._register_meta(item)
                item = pydantic.TypeAdapter(ItemRegistry().WarehouseItemT).validate_python(item)

            cur_item = dict.get(self, item.type_)

            if not cur_item and mode == "update":
                cur_item = self._predefined_items.get(item.type_)
                mode = "keep"

            if not cur_item and mode in ("update", "keep"):
                mode = "replace"

            if mode == "update":
                cur_item.update("", item.model_dump(exclude_unset=True))
                return

            if mode == "keep":
                item.update("", cur_item.model_dump(exclude_unset=True))
                self[item.type_] = item

                return

            if mode == "replace":
                self[item.type_] = item
                return

            raise ValueError("invalid mode argument, must be one of 'replace', 'update' or 'keep' , not %s" % mode)

    @functools.cached_property
    def eid(self):
        # set unique entity id
        with self.lock:

            name = str(self.id.id)
            if not name:
                name = config.cfg._init("eid_prefix", "entity", section="myrrh.core.entity")

            eids = self.__eid__.get(name) or list()
            eid = f"{name}/{len(eids)}" if len(eids) else name
            eids.append(weakref.ref(self))
            self.__eid__[name] = eids

            return eid

    @functools.cached_property
    def uuid(self):
        with self.lock:

            if self.id.uuid:
                return str(self.id.uuid)

            import uuid

            return str(uuid.uuid4())


_T = typing.TypeVar("_T")


class ERegistryProperty(typing.Generic[_T]):
    ACQ = 2
    SET = 1
    UNSET = 0

    def __init__(self, reg_path: str, init_at_creation_time: bool = False):
        self.reg_path = reg_path
        self.func: typing.Callable[[IERegistrySupplier], None] | None = None
        self.init_at_creation_time = init_at_creation_time

    def __call__(self, func: typing.Callable[[IERegistrySupplier], None]):
        self.func = func

        return self

    def __get__(self, instance: IERegistrySupplier, owner=None) -> _T:
        if instance is None:
            return self

        value = instance.reg[self.reg_path]
        if value is NoneItem and self.func:
            value = self.func(instance)
            self.__set__(instance, value)

        if value is NoneItem:
            raise AttributeError(f"{self.reg_path} can not be resolved")

        return value

    def __set__(self, instance: IERegistrySupplier, value: _T):
        instance.reg.set(self.reg_path, value)


def eregistry_property(reg_path: str) -> ERegistryProperty:
    return ERegistryProperty(reg_path)
