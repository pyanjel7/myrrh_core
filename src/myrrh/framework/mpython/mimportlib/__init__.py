import functools
import typing

import mlib

from myrrh.core.interfaces import abstractmethod, ABC
from myrrh.core.services.system import AbcRuntimeDelegate, _mlib_

__mlib__ = "AbcImportLib"


def module_property(module, default=None):
    def get_str(self):
        importlib = AbcImportLib(self)
        try:
            return importlib.import_module(module)
        except ImportError:
            if default is not None:
                return default
            raise

    def get_mod(self):
        try:
            Abc = _mlib_(module)
            return Abc(self)
        except ImportError:
            if default is not None:
                return default
            raise

    if isinstance(module, str):
        return functools.cached_property(get_str)

    return functools.cached_property(get_mod)


class _interface(ABC):
    import importlib as local_importlib
    import importlib.util

    @abstractmethod
    def invalidate_caches(self) -> None:
        ...

    @abstractmethod
    def find_loader(name, path=None) -> typing.Any:
        ...

    @abstractmethod
    def import_module(name, package=None) -> typing.Any:
        ...

    @abstractmethod
    def reload(module) -> typing.Any:
        ...

    @abstractmethod
    def __import__(name, globals=None, locals=None, fromlist=(), level=0) -> typing.Any:
        ...


class AbcImportLib(_interface, AbcRuntimeDelegate):
    __frameworkpath__ = "mpython.mimportlib"

    __all__ = ["invalidate_caches", "find_loader", "reload", "__import__"]

    __doc__ = _interface.local_importlib.__doc__

    __delegated__ = {_interface: _interface.local_importlib}
    __delegate_check_type__ = False

    sys = module_property("sys")

    def __init__(self, *a, **kwa):
        mod = _interface.importlib.util.module_from_spec(self.local_importlib.__spec__)
        assert mod is not self.local_importlib
        mod.__loader__.exec_module(mod)

        mod.import_module = self._myrrh_import_module
        mod.__import__ = self._myrrh__import__

        self.__delegate__(_interface, mod)

    def _myrrh_import_module(self, name, package=None):
        package = f"mlib.py.{package}" if package else "mlib.py"

        mod = self.local_importlib.import_module(f".{name}", package)

        try:
            return mod._mlib_cls(self)
        except (NotImplementedError, TypeError, AttributeError):
            raise ImportError

    def _myrrh__import__(self, name, globals=None, locals=None, fromlist=(), level=0):
        if level:
            globals_ = globals if globals is not None else {}
            package = self.local_importlib._bootstrap._calc___package__(globals_)
            name = self.local_importlib._bootstrap._resolve_name(name, package, level)

        if not fromlist:
            mod_name = name.partition(".")[0]
        else:
            mod_name = name

        if self.sys.modules.get(name) is None:
            mlib_name = f"mlib.py.{name}" if name else "mlib.py"

            with mlib.mlib_select(self):
                _mod = self.local_importlib.__import__(mlib_name, globals, locals, fromlist, 0)

                if not fromlist:
                    mod = getattr(_mod.py._mlib_cls(self), mod_name)
                else:
                    mod = _mod._mlib_cls(self)

                try:
                    new_mod = _mlib_(mod, lambda s: mod)(self)
                    if getattr(new_mod, "__name__", "").startswith("myrrh.framework.mpython"):
                        new_mod = mlib.__class__(
                            mod_name,
                            module=new_mod,
                            package=".".join((mlib.py.__package__, mod_name)),
                            parent=mlib.py,
                        )
                    self.sys.modules[mod_name] = new_mod
                except (NotImplementedError, TypeError, AttributeError) as e:
                    raise ImportError(e)

                mod = mlib.py
                fulln = ""
                for n in name.split("."):
                    fulln = fulln + n
                    mod = getattr(_mlib_(mod, mod), n)
                    if self.sys.modules.get(fulln) is None:
                        new_mod = _mlib_(mod, lambda s: mod)(self)
                        if getattr(new_mod, "__name__", "").startswith(mlib.py.__package__):
                            new_mod = mlib.__class__(
                                mod_name,
                                module=new_mod,
                                package=".".join((mlib.py.__package__, mod_name)),
                                parent=mlib.py,
                            )

                        self.sys.modules[fulln] = new_mod
                    fulln = fulln + "."

        return self.sys.modules[mod_name]
