import collections
import inspect
import functools

from concurrent.futures import ThreadPoolExecutor, wait

from . import cfg_init


__all__ = (
    "myrrh_group_iter",
    "myrrh_group_keys",
    "MyrrhGroup",
    "is_myrrh_group",
    "myrrh_group",
    "myrrh_group_sync",
    "myrrh_group_async",
    "myrrh_group_async_member",
)


def myrrh_group_iter(iterable):
    return iter(getattr(iterable, "_t_", iterable))


def myrrh_group_keys(iterable):
    return tuple(getattr(iterable, "_f_", iterable))


def myrrh_group_values(iterable):
    return tuple(getattr(iterable, "_t_", iterable))


def is_myrrh_group(group):
    return isinstance(group, MyrrhGroup)


def myrrh_group(func, keys=None):
    return functools.wraps(func)(MyrrhGroup(func, keys=keys))


def myrrh_group_sync(func, keys=None):
    return functools.wraps(func)(MyrrhGroup(func, keys=keys)._s_)


def myrrh_group_async(func, keys=None):
    return functools.wraps(func)(MyrrhGroup(func, keys=keys)._as_)


def myrrh_group_async_member(method):
    method.async_ = True
    return method


def myrrh_group_sync_member(method):
    method.async_ = False
    return method


class MyrrhGroupPropertySync:
    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return MyrrhGroup(
            *(getattr(instance._d_[k], self.name) for k in instance._f_),
            keys=instance._f_,
        )

    def __set__(self, instance, value):
        for k in instance._f_:
            setattr(instance._d_[k], self.name, value)


class MyrrhGroupPropertyASync:
    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        with MyrrhGroupPool(instance) as pool:
            return MyrrhGroup(
                *pool.map(lambda k: getattr(instance._d_[k], self.name), instance._f_),
                keys=instance._f_,
            )

    def __set__(self, instance, value):
        with MyrrhGroupPool(instance) as pool:
            pool.map(lambda k: setattr(instance._d_[k], self.name, value), instance._f_)


class MyrrhGroupMeta(type):
    __async__ = cfg_init("group_threaded", False, section="myrrh.core.services.system")
    __max_workers__ = cfg_init("group_max_concurrent_threads", 5, section="myrrh.core.services.system")

    def __prepare__(name, bases, *, namedtuple_, async_=None):
        _dict = dict()
        if async_ is None:
            async_ = MyrrhGroupMeta.__async__

        _dict["__namedtuple__"] = namedtuple_()
        _dict["__async__"] = async_
        _dict["__max_workers__"] = MyrrhGroupMeta.__max_workers__

        if namedtuple_._field_defaults:
            master_item = namedtuple_()[0]

            for k, m in inspect.getmembers_static(master_item):
                if not k.startswith("_"):
                    _dict[k] = (MyrrhGroupPropertyASync if getattr(m, "async_", False) else MyrrhGroupPropertySync)()

            if callable(master_item):
                _dict["__call__"] = MyrrhGroupMeta.__async_group_call__ if getattr(master_item, "async_", async_) else MyrrhGroupMeta.__sync_group_call__

            try:
                iter(master_item)
                _dict["__iter__"] = MyrrhGroupMeta.__group_iter__
            except TypeError:
                ...

            for spe_attr in (
                "__getitem__",
                "__setitem__",
                "__delitem__",
                "__missing__",
                "__reversed__",
                "__contains__",
                "__enter__",
                "__exit__",
            ):
                if hasattr(master_item, spe_attr):
                    _dict[spe_attr] = (MyrrhGroupPropertyASync if getattr(m, "async_", False) else MyrrhGroupPropertySync)()

            for oper in (
                "__add__",
                "__sub__",
                "__mul__",
                "__truediv__",
                "__floordiv__",
                "__mod__",
                "__divmod__",
                "__pow__",
                "__lshift__",
                "__rshift__",
                "__and__",
                "__xor__",
                "__or__",
                "__radd__",
                "__rsub__",
                "__rmul__",
                "__rtruediv__",
                "__rfloordiv__",
                "__rmod__",
                "__rdivmod__",
                "__rpow__",
                "__rlshift__",
                "__rrshift__",
                "__rand__",
                "__rxor__",
                "__ror__",
                "__iadd__",
                "__isub__",
                "__imul__",
                "__itruediv__",
                "__ifloordiv__",
                "__imod__",
                "__idivmod__",
                "__ipow__",
                "__ilshift__",
                "__irshift__",
                "__iand__",
                "__ixor__",
                "__ior__",
                "__neg__",
                "__pos__",
                "__abs__",
                "__invert__",
                "__match_args__",
            ):
                if hasattr(master_item, oper):
                    _dict[oper] = (MyrrhGroupPropertyASync if getattr(m, "async_", False) else MyrrhGroupPropertySync)()
            """
            for unsupported in ('__complex__', '__int__', '__float__', '__index__',
                           '__round__', '__trunc__', '__floor__', '__ceil__',
                           '__length_hint__', '__len__):
                if hasattr(master_item, unsupported):
                    _dict[unsupported] =  (MyrrhGroupPropertyASync if getattr(m, 'async_', False) else MyrrhGroupPropertySync)()
            """

            _dict["__item_master__"] = property(fget=lambda cls: cls.__namedtuple__[0])
            _dict["__item_class__"] = getattr(master_item, "__item_class__", None) or getattr(master_item, "__class__") or None.__class__

        else:
            _dict["__item_master__"] = None
            _dict["__item_class__"] = None.__class__

        return _dict

    def __group_iter__(self):
        iter_ = myrrh_group_sync(iter)(self)
        try:
            while True:
                yield myrrh_group_sync(next)(iter_)

        except StopIteration:
            ...

    def __sync_group_call__(self, *a, **kwa):
        keys, vals, args, kwargs = MyrrhGroupMeta._group_members(self, a, kwa)
        futures = [(v, a, kwa) for v, a, kwa in zip(vals, args, kwargs)]

        results = list()
        rsult_keys = list()
        keys = list(reversed(keys))

        for v, a, kwa in futures:
            try:
                results.append(v(*a, **kwa))
                rsult_keys.append(keys.pop())

            except StopIteration:
                keys.pop()

        if len(rsult_keys) == 0:
            raise StopIteration

        return MyrrhGroup(*results, keys=rsult_keys)

    def __async_group_call__(self, *a, **kwa):
        keys, vals, args, kwargs = MyrrhGroupMeta._group_members(self, a, kwa)

        with MyrrhGroupPool(keys) as pool:
            futures = [pool.submit(v, *a, **kwa) for v, a, kwa in zip(vals, args, kwargs)]

        wait(futures)

        results = list()
        rsult_keys = list()
        keys = list(reversed(keys))

        for f in futures:
            try:
                results.append(f.result())
                rsult_keys.append(keys.pop())
            except StopIteration:
                keys.pop()

        if len(rsult_keys) == 0:
            raise StopIteration

        return MyrrhGroup(*results, keys=rsult_keys)

    def _group_members(self, args, kwargs):
        vals = []
        group_args = []
        group_kwargs = []

        for group in filter(lambda a: isinstance(a, MyrrhGroup), args):
            keys = group._f_
            break
        else:
            for group in filter(lambda a: isinstance(a, MyrrhGroup), kwargs.values()):
                keys = group._f_
                break
            else:
                keys = self._f_

        try:
            for k in keys:
                val = self.__namedtuple__._field_defaults.get(k) or self.__item_master__
                vals.append(val)
                group_args.append([(a if not isinstance(a, MyrrhGroup) else a._d_[k]) for a in args])
                group_kwargs.append({ka: (va if not isinstance(va, MyrrhGroup) else va._d_[k]) for ka, va in kwargs.items()})

            return keys, vals, group_args, group_kwargs

        except KeyError:
            pass

        raise ValueError("multiple MyrrhRuntimeGroup in arguments but keys are not the same")


class MyrrhGroup:
    def __new__(cls, *items, keys=None, async_=None):
        keys = keys or tuple(map(lambda i: f"f{i}", range(0, items and len(items) or 1)))

        if not items:
            items = keys

        keys = getattr(keys, "_f_", keys)
        items = myrrh_group_values(items)

        NamedTuple = collections.namedtuple("MyrrhRuntimeGroup", keys, defaults=items)

        class _MyrrhRuntimeGroup(MyrrhGroup, namedtuple_=NamedTuple, async_=async_, metaclass=MyrrhGroupMeta):
            def __new__(cls, *items, keys=None, async_=None):
                return object.__new__(cls)

        return _MyrrhRuntimeGroup()

    def __init_subclass__(cls, namedtuple_, async_):
        ...

    @property  # type: ignore[misc]
    def __class__(self):
        return self.__item_class__

    @property
    def _f_(self):
        return self.__namedtuple__._fields

    @property
    def _d_(self):
        return self.__namedtuple__._asdict()

    @property
    def _t_(self):
        return tuple(self.__namedtuple__)

    @property
    def _as_(self, *, max_workers=None):
        group = MyrrhGroup(*self._t_, keys=self._f_, async_=True)
        if max_workers:
            group.__max_workers__ = max_workers

        return group

    @property
    def _s_(self):
        return MyrrhGroup(*self._t_, keys=self._f_, async_=False)


class MyrrhGroupPool(ThreadPoolExecutor):
    def __init__(self, keys):
        if not len(keys):
            raise RuntimeError("invalid keys")
        super().__init__(len(keys), f"Myrrh{keys}")
