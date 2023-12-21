import contextlib
import sys
import threading
import importlib
import re

from myrrh.core.services.system import _mlib_

_lock = threading.RLock()


def _modname(name):
    return re.sub("(_*)(.+)", r"\g<1>m\g<2>", name)


class MLibModule(threading.local):
    __slots__ = ["__package__", "__name__", "py", "_mlib_mod"]

    __path__ = "(Mlib)"
    __loader__ = __loader__  # type: ignore[name-defined]
    __doc__ = __doc__
    __file__ = __file__
    __spec__ = __spec__  # type: ignore[name-defined]

    def __init__(self, name, *, module=None, package="", parent=None):
        self.__package__ = package
        self.__name__ = name
        self._mlib_mod = module

        if not parent:
            self._mlib_systems = list()
        else:
            self._mlib_systems = parent._mlib_systems

    def _mlib_cls(self, s, *, func=lambda mod: mod):
        if self._mlib_mod is None:
            return MLibModule
        return _mlib_(self._mlib_mod, lambda s: func(self._mlib_mod))(s)

    def __repr__(self):
        return f"<MlibModule> {repr(_mlib_(self._mlib_mod, self._mlib_mod))}"

    def __setattr__(self, name, value):
        with _lock:
            if name in (
                "__package__",
                "__name__",
                "__spec__",
                "__loader__",
                "__file__",
                "__path__",
                "_mlib_mod",
                "_mlib_systems",
                "__finder__",
            ):
                return super().__setattr__(name, value)

            if not self._mlib_mod:
                return super().__setattr__(name, value)

            setattr(
                _mlib_(self._mlib_mod, self._mlib_mod),
                name,
                getattr(value, "_mlib_mod", value),
            )

    def __getattr__(self, name):
        with _lock:
            if self._mlib_systems:
                system = self.mlib_current()
                try:
                    mod = self._mlib_cls(system)
                except (NotImplementedError, AttributeError, TypeError) as e:
                    raise ImportError(f"invalid module {repr(self._mlib_mod)} : {e}")

                result = getattr(mod, name)

                try:
                    return _mlib_(result, lambda s: result)(system)

                except (NotImplementedError, AttributeError, TypeError) as e:
                    raise ImportError(f"invalid module {repr(result)} : {e}")

            mod = _mlib_(self._mlib_mod, self._mlib_mod)
            mod = getattr(mod, name)
            return _mlib_(mod, mod)

    @contextlib.contextmanager
    def mlib_select(self, system):
        try:
            self.mlib_push(system)
            yield system
        finally:
            self.mlib_pop()

    def mlib_push(self, system):
        self._mlib_systems.append(system)

    def mlib_pop(self):
        self._mlib_systems.pop()

    def mlib_current(self):
        if self._mlib_systems:
            return self._mlib_systems[-1]


class MLibModuleLoader:
    def __init__(self, name, spec, *, package="", parent=None):
        self.module_name = name
        self.module_spec = spec
        self.module_package = package
        self.module_parent = parent

    def create_module(self, spec):
        _lock.acquire()
        try:
            module = sys.modules.get(self.module_spec.name)
            spec.loader_state = not module
            if not module:
                module = importlib.util.module_from_spec(self.module_spec)
            else:
                module.__spec__.loader_state = True

            module = MLibModule(
                self.module_name,
                module=module,
                parent=self.module_parent,
                package=self.module_package,
            )
            module.__spec__ = spec

            return module
        except:  # noqa: E722
            _lock.release()
            raise

    def exec_module(self, module):
        try:
            if module.__spec__.loader_state:
                mlib_mod = module._mlib_mod
                mlib_mod.__loader__.exec_module(mlib_mod)
                sys.modules[mlib_mod.__spec__.name] = mlib_mod
        finally:
            _lock.release()


class MLibSubModuleFinder:
    packages: dict[str, str] = dict()

    def find_spec(self, fullname, path, target=None):
        package, _, name = fullname.rpartition(".")

        if package not in (__module__.__name__, __name__):
            return

        if name in self.packages:
            module_parent = sys.modules[package]
            module_path = self.packages[name]
            spec = importlib.util.find_spec(module_path)

            if spec is not None:
                module_spec = importlib.machinery.ModuleSpec(
                    fullname,
                    MLibModuleLoader(fullname, spec, package=module_path, parent=module_parent),
                )
                return module_spec


class MLibModuleFinder:
    def find_spec(self, fullname, path, target=None):
        if fullname.startswith((__module__.__name__, __name__)):
            try:
                package, _, name = fullname.rpartition(".")
                module_parent = sys.modules[package]

                if isinstance(module_parent, MLibModule):
                    parent_package = module_parent.__package__
                    module_name = _modname(name)
                    module_package = ".".join((parent_package, module_name))

                    spec = importlib.util.find_spec(module_package)

                    if spec is not None:
                        module_spec = importlib.machinery.ModuleSpec(
                            fullname,
                            MLibModuleLoader(
                                fullname,
                                spec,
                                package=module_package,
                                parent=module_parent,
                            ),
                        )
                        return module_spec

                    arch = None
                    current = __module__.mlib_current()
                    module_arch_package = None

                    if current is not None:
                        try:
                            arch = current.myrrh_os.cfg.system.os
                        except Exception:
                            ...

                    if arch:
                        parent_package = "myrrh.framework.arch." + arch + parent_package.removeprefix("myrrh.framework")
                        module_arch_package = ".".join((parent_package, module_name))

                    if module_arch_package:
                        try:
                            spec = importlib.util.find_spec(module_arch_package)
                        except ModuleNotFoundError:
                            pass

                    if spec is not None:
                        module_spec = importlib.machinery.ModuleSpec(
                            fullname,
                            MLibModuleLoader(
                                fullname,
                                spec,
                                package=module_arch_package,
                                parent=module_parent,
                            ),
                        )
                        return module_spec

                    # python special case
                    if fullname.startswith("mlib.py."):
                        module_package = fullname[len("mlib.py.") :]
                        spec = importlib.util.find_spec(module_package)
                        if spec is not None:
                            return importlib.machinery.ModuleSpec(
                                fullname,
                                MLibModuleLoader(
                                    fullname,
                                    spec,
                                    package=module_package,
                                    parent=module_parent,
                                ),
                            )

            except KeyError:
                pass


__subfinder__ = MLibSubModuleFinder()
__finder__ = MLibModuleFinder()


__module__ = MLibModule("mlib", package="myrrh.framework.mlib")
__module__.__finder__ = __subfinder__

sys.modules["mlib"] = __module__  # type: ignore[assignment]
sys.modules[__name__] = __module__  # type: ignore[assignment]

sys.meta_path.append(__subfinder__)
sys.meta_path.append(__finder__)
