import functools
import threading
import warnings
import weakref
import pydantic

from ..interfaces import IRegistry
from ..services import cfg_init

from ... import provider
from ...warehouse.item import NoneItem
from ...warehouse.registry import ItemRegistry


class Registry(IRegistry):
    __eid__: dict[str, weakref.WeakSet] = dict()
    _item_updaters: dict[str, list[provider.IProvider]]

    def __init__(self, provider: provider.IProvider, items: list[ItemRegistry().WarehouseItemT]):  # type: ignore[valid-type]
        super().__init__()

        self.lock = threading.RLock()
        self._item_updaters = dict()
        self._predefined_items = {item.type_: item for item in items}

        for name in provider.catalog():
            updaters = self._item_updaters.get(name) or list()
            updaters.append(provider)
            self._item_updaters[name] = updaters
            self[name] = NoneItem

    def __setattr__(self, name, value):
        if name != "lock" and not name.startswith("_"):
            self[name] = value
            return

        super().__setattr__(name, value)

    def __getattr__(self, name):
        try:
            if not name.startswith("_"):
                return self[name]
        except KeyError:
            pass

        raise AttributeError(name)

    def __getitem__(self, name):
        with self.lock:
            name, _, next = name.partition(".")
            item = super().get(name, NoneItem)
            if not item:
                updaters = self._item_updaters.get(name) or list()
                for p in updaters:
                    try:
                        self.append(p.deliver(name))
                    except Exception as e:
                        warnings.warn(
                            'a provider failed to provide a required item "%s" : %s' % (name, e),
                            UserWarning,
                        )

                item = super().get(name, NoneItem)

            if next:
                item = item.__getitem__(next)

            return item

    def predefined(self):
        return list(self._predefined_items.values())

    def defined_values(self):
        return list(filter(None, super().values()))

    def values(self):
        return list(self[item] for item in self)

    def get(self, key, default=NoneItem):
        return self[key] or default

    def append(self, item, mode="update"):
        if not item:
            return

        if isinstance(item, dict):
            item = pydantic.TypeAdapter(ItemRegistry().WarehouseItemT).validate_python(item)

        try:
            cur_item = super().__getitem__(item.type_)
        except KeyError:
            cur_item = None

        if not cur_item:
            cur_item = self._predefined_items.get(item.type_)
            mode = "keep"

        if not cur_item and mode in ("update", "keep"):
            mode = "replace"

        if mode == "update":
            dump = cur_item.model_dump()
            dump.update(item.model_dump(exclude_unset=True))
            self[item.type_] = item.model_validate(dump)
            return

        if mode == "keep":
            dump = item.model_dump()
            dump.update(cur_item.model_dump(exclude_unset=True))
            self[item.type_] = item.model_validate(dump)

            return

        if mode == "replace":
            self[item.type_] = item
            return

        raise ValueError("invalid mode argument, must be one of 'replace', 'preserve' or 'force' , not %s" % mode)

    @functools.cached_property
    def eid(self):
        name = str(self.id.id)
        if not name:
            name = cfg_init("eid_prefix", "entity", section="myrrh.core.entity")

        # set unique entity id
        with self.lock:
            eids = self.__eid__.get(name) or list()
            eid = f"{name}/{len(eids)}" if len(eids) else name
            eids.append(weakref.ref(self))
            self.__eid__[name] = eids

        return eid

    @functools.cached_property
    def uuid(self):
        if self.id.uuid:
            return str(self.id.uuid)

        import uuid

        return str(uuid.uuid4())
