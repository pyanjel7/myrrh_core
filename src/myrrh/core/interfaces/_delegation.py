import inspect

from abc import ABCMeta, abstractmethod, ABC
import typing

__all__ = (
    "ABCDelegationMeta",
    "NoneDelegation",
    "ABCDelegation",
    "ABCMeta",
    "abstractmethod",
    "ABC",
    "DelegateProperty",
)


class DelegateProperty:
    def __init__(self, cls, name):
        self.cls = cls
        self.name = name

    def __get__(self, obj, type):
        if obj is None:
            return self

        try:
            return getattr(obj._delegate_, self.name)
        except AttributeError:
            pass

    def __set__(self, obj, value):
        setattr(obj._delegate_, self.name, value)

    def __delete__(self, obj):
        delattr(obj._delegate_, self.name)


class Delegation:
    __delegation_ref__: dict

    __delagation_owner__: typing.Any = None

    def __init__(self):
        super().__setattr__("__delegation_ref__", dict())
        super().__setattr__("__delagation_owner__", None)

    def __set_name__(self, owner, name):
        super().__setattr__("__delagation_owner__", owner)

    def __getattr__(self, name: str):
        try:
            _, ref, _getattr_ = self.__delegation_ref__[name]
            if ref is not None:
                return _getattr_(ref, name)
        except KeyError:
            pass

        raise AttributeError(f"{self.__delagation_owner__.__class__.__name__} delegation has no attribute {name}")

    def __setattr__(self, name: str, value):
        try:
            _, ref, _ = self.__delegation_ref__[name]
            if ref is not None:
                return setattr(ref, name, value)
        except KeyError:
            pass

        raise AttributeError(f"{self.__delagation_owner__.__class__.__name__} delegation has no attribute {name}")

    def __delattr__(self, name: str):
        try:
            _, ref, _ = self.__delegation_ref__[name]
            if ref is not None:
                return delattr(ref, name)
        except KeyError:
            pass

        raise AttributeError(f"{self.__delagation_owner__.__class__.__name__} delegation has no attribute {name}")


class ABCDelegationMeta(ABCMeta):
    def __prepare__(name, bases):
        dct = {"__delegate__": ABCDelegationMeta.__delegate__, "_delegate_": None}

        return dct

    def __new__(mcls, name, bases, dct):
        delegated = dct.get("__delegated__") or dict()
        delegated_attrs = dct.get("__delegated_attrs__") or set()

        if not isinstance(delegated, dict):
            delegated = dict.fromkeys(delegated, None)

        for b in bases:
            if hasattr(b, "__delegated__"):
                delegated.update(b.__delegated__)
            if hasattr(b, "__delegated_attrs__"):
                delegated_attrs.update(b.__delegated_attrs__)

        dct["__delegated__"] = delegated
        dct["__delegated_attrs__"] = delegated_attrs

        inherited_dct = set(m for b in bases for m, _ in inspect.getmembers_static(b) if m not in (getattr(b, "__abstractmethods__", None) or list()))

        for delgcls in delegated:
            if not hasattr(delgcls, "__abstractmethods__"):
                raise TypeError(f"{delgcls.__name__} invalid type: delegated class type must be abc.ABCMeta")

            for method in delgcls.__abstractmethods__:
                dct["__delegated_attrs__"].add(method)
                if method not in dct and method not in inherited_dct:
                    dct[method] = DelegateProperty(delgcls, method)

        return super().__new__(mcls, name, bases, dct)

    def __call__(cls, *a, **kwa):
        inst = cls.__new__(cls, *a, **kwa)

        inst._delegate_ = Delegation()
        inst._delegate_.__set_name__(inst, "_delegate_")

        for delgcls, default in cls.__delegated__.items():
            if default:
                for m in delgcls.__abstractmethods__:
                    inst._delegate_.__delegation_ref__[m] = (delgcls, default, getattr)

        if isinstance(inst, cls):
            inst.__init__(*a, **kwa)

        return inst

    def __delegate__(self, cls, obj, *, checktype=None):
        if checktype is None:
            checktype = getattr(self, "__delegate_check_type__", True)

        delegate_all = getattr(cls, "__delegate_all__", None) or [cls]

        if checktype and delegate_all and not all(isinstance(obj, cls_) for cls_ in delegate_all):
            raise Exception("invalid delegation for %s : %s invalid type" % (cls.__name__, obj.__class__.__name__))

        if self is obj:
            if not hasattr(obj, "__get_delegate__"):
                raise Exception("invalid delegation for %s : %s need  __get_delegate__ method" % (cls.__name__, obj.__class__.__name__))

            for m in cls.__abstractmethods__:
                self._delegate_.__delegation_ref__[m] = (
                    cls,
                    obj,
                    obj.__class__.__get_delegate__,
                )
        else:
            for m in cls.__abstractmethods__:
                delegated = getattr(obj, "_delegate_", None)
                getter = getattr

                if delegated:
                    cls_, obj_, getter_ = delegated.__delegation_ref__.get(m) or (
                        None,
                        None,
                        None,
                    )
                    if cls_ is cls and isinstance(getter_(obj_.__class__, m, None), DelegateProperty):
                        cls, obj, getter = cls_, obj_, getter_

                self._delegate_.__delegation_ref__[m] = cls, obj, getter


class ABCDelegation(metaclass=ABCDelegationMeta):
    __delegated__: tuple[typing.Any, ...] | typing.Dict[typing.Type[ABC], typing.Any] | None = None
    __delegate_all__: tuple[typing.Any, ...]
    __delegate_check_type__: bool

    @property
    @abstractmethod
    def _delegate_(self) -> typing.Any:
        ...

    @abstractmethod
    def __delegate__(self, t: typing.Type[ABC], o: object) -> None:
        ...


def NoneDelegation(name, delegation_class):
    def __new__(cls):
        if cls.__inst__:
            return cls.__inst__
        return object.__new__(cls)

    def __init__(self):
        self.__delegate__(delegation_class, self)

    def __bool__(self):
        return False

    def __get_delegate__(self, name):
        raise AttributeError(f"{delegation_class} is not provided")

    d = ABCDelegationMeta.__prepare__(name, (delegation_class,))
    d.update(
        {
            "__delegated__": (delegation_class,),
            "__inst__": None,
            "__new__": __new__,
            "__init__": __init__,
            "__bool__": __bool__,
            "__get_delegate__": __get_delegate__,
        }
    )

    cls = ABCDelegationMeta(name, (delegation_class,), d)

    inst = cls()
    cls.__inst__ = inst

    return inst
