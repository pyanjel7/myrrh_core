import contextlib
import threading
import time
import typing

from myrrh.warehouse.item import NoneItem

from ...services import cfg_init

__all__ = ("Acquiring", "runtime_cached_property", "RuntimeCache", "init_cache")


class Acquiring(Exception):
    ...


class RuntimeCache(dict):
    def __init__(self):
        super().__init__(_runtime_cache)
        self.__lock__ = threading.RLock()
        self.__status__ = _new_runtime_status()

    @contextlib.contextmanager
    def attr(self, attr, default=None):
        with self.__lock__:
            yield self.get(attr, default)

    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            pass

        raise AttributeError(attr)

    def __setattr__(self, attr, value):
        try:
            self[attr] = value
            return
        except KeyError:
            pass

        raise AttributeError(attr)


def init_cache(cache, system):
    for k, d in _runtime_status.items():
        if getattr(system.__class__, d["property"].property_name, None):
            cfg_path = d["init_cfg_path"]

            if cfg_path and system.cfg[cfg_path] is not NoneItem:
                cache[k] = system.cfg[cfg_path]

            if d["init_at_creation_time"]:
                cache[k] = d["property"].get(system, cache)

    system.__m_runtime_cache__ = cache


_runtime_cache = {"__lock__": None, "__status__": None}
_runtime_status: dict[str, dict[str, typing.Any]] = dict()


def _new_runtime_status():
    d = dict()
    for k, v in _runtime_status.items():
        d[k] = dict(v)

    return d


class _RuntimeProperty:
    ACQ = 2
    SET = 1
    UNSET = 0

    def __init__(self, func, name):
        self.name = name
        self.func = (lambda s: getattr(s, func)) if isinstance(func, str) else func
        self.__doc__ = func.__doc__

    def __set_name__(self, owner, name):
        self.property_name = name

    def get(self, instance, cache):
        # optim?
        status = cache.__status__[self.name]
        if not (status["validity"] == -1 and status["state"] == self.SET):
            with cache.__lock__:
                if status["state"] == self.ACQ:
                    raise Acquiring

                isvalid = status["state"] == self.SET and (status["validity"] == -1 or (time.monotonic() > (status["date"] + status["validity"])))

                if isvalid:
                    return cache[self.name]

                status["state"] = self.ACQ

                self.set(instance, cache, self.func(instance))

        return cache[self.name]

    def set(self, instance, cache, value):
        with cache.__lock__:
            cache[self.name] = value
            cache.__status__[self.name]["date"] = time.monotonic()
            cache.__status__[self.name]["state"] = self.SET

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return self.get(instance, instance.__m_runtime_cache__)

    def __set__(self, instance, value):
        cache = instance.__m_runtime_cache__
        return self.set(instance, cache, value)

    def __delete__(self, instance):
        if self.name is None:
            raise TypeError("Cannot use cached_property instance without calling __set_name__ on it.")

        if not instance.__m_runtime_cache__:
            msg = f"No '__dict__' attribute on {type(instance).__name__!r} " f"instance to cache {self.name!r} property."
            raise TypeError(msg) from None

        with self._runtime_cache__.__lock_:
            instance.__m_runtime_cache__.pop(self.name, None)


def runtime_cached_property(
    name: str,
    *,
    init_value=None,
    init_cfg_path=None,
    init_at_creation_time=False,
    validity=None,
) -> typing.Callable[[typing.Any], typing.Any]:
    if validity is None:
        validity = cfg_init("default_cache_validity", -1, section="runtime")

    def wrapper(func):
        assert name not in _runtime_cache
        assert name not in _runtime_status

        _runtime_cache[name] = init_value
        _runtime_status[name] = {
            "state": _RuntimeProperty.UNSET,
            "init_at_creation_time": init_at_creation_time,
            "init_cfg_path": init_cfg_path,
            "date": 0,
            "validity": validity,
            "property": _RuntimeProperty(func, name),
        }

        return _runtime_status[name]["property"]

    return wrapper
