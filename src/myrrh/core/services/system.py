from .._system.runtime import *  # noqa: F403,F401
from .._system.objects import *  # noqa: F403,F401

from ...provider import Whence, Wiring, Protocol  # noqa: F401

from abc import ABCMeta, ABC

__all__ = (
    "_mlib_",
    "supportedif",
    "ImplPropertyClass",
    "InheritedPropertyClass_properties",
    "InheritedPropertyClass",
)


def _mlib_(impl, default=None) -> type[ABC]:
    try:
        return getattr(impl, impl.__mlib__)
    except AttributeError:
        pass

    if default is not None:
        return default

    raise AttributeError(f"_mlib_ is not defined in {impl}")


# supported decorator
def supportedif(condition, reason=""):
    def condition_wrapper(func):
        def fget(self):
            def wrapper(*a, **kw):
                return func(self, *a, *kw)

            if not condition(self):
                raise AttributeError(reason)
            return wrapper

        return property(fget, doc=func.__doc__)

    return condition_wrapper


class ImplPropertyClass(ABCMeta):
    def __new__(mcls, name, bases, namespace, **kwargs):
        inherited_props = kwargs.get("__inherited_props", tuple())
        inherited_types = kwargs.get("__inherited_types", tuple())

        class Deleted:
            pass

        @property
        def cls_wrapper(self):
            if not hasattr(self, "__propertyclass__%s" % name):
                _bases = bases + tuple(p.fget(self) for p in inherited_props) + tuple(p for p in inherited_types)

                cls = type(name, _bases, namespace)

                gattr = getattr(cls, "__getattr__", None)

                if gattr:

                    def _getattr(_self, name):
                        try:
                            return gattr(_self, name)
                        except AttributeError:
                            pass

                        return getattr(self, name)

                else:

                    def _getattr(_, name):
                        return getattr(self, name)

                setattr(cls, "__getattr__", _getattr)
                cls.__rself__ = self

                setattr(self, "__propertyclass__%s" % name, cls)

            attr = getattr(self, "__propertyclass__%s" % name)

            if attr is Deleted:
                raise AttributeError

            return attr

        @cls_wrapper.setter
        def cls_wrapper(self, value):
            setattr(self, "__propertyclass__%s" % name, value)

        @cls_wrapper.deleter
        def cls_wrapper(self):
            setattr(self, "__propertyclass__%s" % name, Deleted)

        return cls_wrapper


def InheritedPropertyClass_properties(*props):
    class wrapper(ImplPropertyClass):
        def __new__(mcls, name, bases, namespace, **kwargs):
            return super().__new__(mcls, name, bases, namespace, __inherited_props=props)

    return wrapper


def InheritedPropertyClass(*types):
    class wrapper(ImplPropertyClass):
        def __new__(mcls, name, bases, namespace, **kwargs):
            return super().__new__(mcls, name, bases, namespace, __inherited_types=types)

    return wrapper
