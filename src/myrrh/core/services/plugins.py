import warnings
import traceback

import importlib.metadata

from myrrh import __distname__
from .config import cfg_init, cfg_get, getsysconfig

__all__ = ["PluginSrv", "init_pluggin_srv", "load_ext", "load_ext_group"]


"""
json config:

```json
{
    ext_load_auto: true or false,

    __extensions__ {
        "group/module_name=kind" : "ondemand" or "always" or "try" or "never"
    }
}
```

"""


class PluginSrv:
    def _extension_string(self, group, name, value):
        return f"{group}/{name}={value}"

    def _extension_partition(self, extension):
        group, _, extension = extension.partition("/")
        name, _, value = extension.partition("=")

        return group, name, value

    def load_ext(self, extension, *, type: str | None = None, kind="", raise_on_failure=False):
        type = type or cfg_get(extension, "ondemand", section="extensions")

        if type == "never":
            return

        if extension in cfg_get("@loaded_extensions@"):  # type: ignore[operator]
            return

        group, ext_value, ext_kind = self._extension_partition(extension)
        if kind and ext_kind != kind:
            return

        if extension in cfg_get("@failed_extensions@"):  # type: ignore[operator, uniion-attr]
            cfg_get("@failed_extensions@").remove(extension)  # type: ignore[union-attr]

        try:
            callable = importlib.metadata.EntryPoint(ext_value, f"{group}:{ext_kind}", group).load()
            callable(*ext_value.split("-"))
            cfg_get("@loaded_extensions@").append(f"{extension}")  # type: ignore[union-attr]
        except (ModuleNotFoundError, ImportError, Exception) as e:
            cfg_get("@failed_extensions@").append(f"{extension}")  # type: ignore[union-attr]
            if kind == "always" or (raise_on_failure and type not in ("try", "ondemand")):
                raise RuntimeError(f"Failed to load {ext_value}: {str(e)}")
            else:
                warnings.warn(f"{''.join(traceback.format_tb(e.__traceback__))}\nFailed to load {ext_value}, this extension will be unavailable: {str(e)}")

    def load_ext_group(self, group: str, *, kind: str = "", raise_on_failure=False):
        for installed, type_ in cfg_get("@installed_extensions@").items():  # type: ignore[union-attr]
            if installed.startswith(group):
                self.load_ext(installed, kind=kind, raise_on_failure=raise_on_failure, type=type_)  # type: ignore[union-attr, arg-type]

    def find_extensions(self):
        getsysconfig()["@loaded_extensions@"] = list()
        getsysconfig()["@failed_extensions@"] = list()

        if cfg_init("extension_auto", True):
            myrrh_exts = {name: exts for name, exts in importlib.metadata.entry_points().items() if name.startswith(f"{__distname__}.")}
            myrrh_exts = {self._extension_string(ext.group, ext.name, ext.value): "ondemand" for _, exts in myrrh_exts.items() for ext in exts}
        else:
            myrrh_exts = cfg_get(section="extensions")

        getsysconfig()["@installed_extensions@"] = myrrh_exts


service: PluginSrv | None = None


def init_pluggin_srv() -> PluginSrv:
    global service

    service = PluginSrv()
    service.find_extensions()

    return service


def __getattr__(name: str):
    return getattr(service, name)


def load_ext(extension: str, *, kind=""):
    return service.load_ext(extension, raise_on_failure=cfg_init("extension_raise_on_failure", False))  # type: ignore[union-attr]


def load_ext_group(group: str, *, kind: str = ""):
    return service.load_ext_group(group, kind=kind, raise_on_failure=cfg_init("ext_raise_on_failure", False))  # type: ignore[union-attr]
