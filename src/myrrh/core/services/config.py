import os
import shutil
import urllib.parse
import sys
import json
import typing
import warnings
import pathlib
import importlib.metadata

from myrrh import __distname__, __license__, __version__, __copyright__, __file__ as _myrrh_file

from ..interfaces import IConfigSrv, ConfigValueType

from .registry import ServiceRegistry

_JSON_INDENT = 2

MYRRHSYS_INIT_FILENAME = "myrrh_init.msys"

__all__ = ["cfg_prop", "DefaultConfigSrv", "cfg_init", "cfg_get", "cfg_set", "cfg_del", "getsysconfig", "rebase"]


class DefaultConfigSrv(IConfigSrv):
    __single__: "DefaultConfigSrv" = None  # type: ignore[valid-type, assignment]

    def __new__(cls, path: str | None, config: dict[str, typing.Any] | None = None):
        if cls.__single__ is None:
            cls.__single__ = super().__new__(cls)

        return cls.__single__

    def __init__(self, path: str | None, config: dict[str, typing.Any] | None = None):
        self.dconfig = config or dict()
        self.path: pathlib.Path | None = None
        self._uri: str | None = None

        if path:
            disk_path_str = urllib.parse.unquote(urllib.parse.urlparse(path).path) if path.startswith("file://") else path
            disk_path = pathlib.Path(disk_path_str)
            try:
                with open(disk_path) as f:
                    self.dconfig.update(json.load(f))
                self.path = disk_path.absolute()
            except Exception as e:
                warnings.warn(f'file "{path}" found but is invalid: {str(e)}, config will not be saved')
        else:
            dirs = _msys_search_paths()
            self.path, cfg = _search_local_cfg(dirs, MYRRHSYS_INIT_FILENAME)

            self.dconfig.update(cfg)

        if self.path:
            self._uri = self.path.as_uri()

        if not isinstance(self.dconfig, dict):
            raise IOError(f"{path} incompatible configuration file type, dictionary required")

    def _persistent_setcfg(self):
        if not self.path:
            return

        try:
            backup = f"{self.path}.bak"
            if os.path.isfile(self.path):
                shutil.copy(self.path, backup)
            else:
                with open(backup, "w") as f:
                    json.dump(self.dconfig, f, indent=_JSON_INDENT)
        except Exception as e:
            warnings.warn(f"Failed to backup msys config in {self.path}: {str(e)}")

        try:
            with open(self.path, "w") as f:
                json.dump(self.dconfig, f, indent=_JSON_INDENT)

        except Exception as e:
            warnings.warn(f"Failed to save msys config in {self.path}: {str(e)}, config will not be persistante")

    def _persistent_getcfg(self):
        if not self.path:
            return self.dconfig

        try:
            with open(self.path) as f:
                fcfg = json.load(f)

            return fcfg
        except Exception as e:
            warnings.warn(f"Failed to load msys config in{self.path}: {str(e)}, try restore backup")

        try:
            with open(f"{self.path}.bak") as f:
                fcfg = json.load(f)

            self._persistent_setcfg(fcfg)

            return fcfg

        except Exception as e:
            warnings.warn(f"Failed to load backup msys config in{self.path}: {str(e)}, config is lost...")

        return

    def _get_section(self, section: str, create=False) -> dict[str, typing.Any]:
        if not section:
            return self.dconfig

        if not section.startswith("__"):
            section = "__" + section
        if not section.endswith("__"):
            section = section + "__"

        dsect = self.dconfig.get(section)
        if dsect is None:
            dsect = dict()

        if self.dconfig.get(section) is None and create:
            self.dconfig[section] = dsect

        return dsect

    @property
    def uri(self) -> str | None:
        return self._uri

    def init(self, key: str, value: ConfigValueType | None, section: str = ""):
        return self.set(key, value, section, overwrite=False)

    def rm(self, key: str = "", section: str = ""):
        if section.startswith("@"):
            raise ValueError(f'section "{key}" is defined as a runtime section and could not be deleted')

        if key.startswith("@"):
            raise ValueError(f'key "{key}" is defined as a runtime key and could not be deleted')

        self._get_section(section).pop(key, None)

        self._persistent_setcfg()

    def get(self, key: str = "", default: ConfigValueType | None = None, *, section=""):
        if not key:
            return self._get_section(section)

        return self._get_section(section).get(key, default)

    def set(self, key: str, value: ConfigValueType | None, section="", *, overwrite: bool = True):
        if overwrite or key not in self._get_section(section):
            self._get_section(section, create=True)[key] = value
            self._persistent_setcfg()

        return self._get_section(section)[key]


# decorator
class cfg_prop:
    def __init__(self, key: str, default: ConfigValueType | None = None, *, section: str = ""):
        self.key = key
        self.default = default  # type: ignore[var-annotated]
        self.section = section

    def __get__(self, instance, owner=None):
        return cfg_init(self.key, self.default, section=self.section)

    def __set__(self, instance, value):
        cfg_set(self.key, value, section=self.section)


def _validate_key_value(key: str):
    if key.startswith(("@", "__")):
        raise ValueError('key name could not start with "__" or "@" character')


def cfg_init(key: str, value: ConfigValueType | None, section: str = "") -> dict[str, ConfigValueType] | ConfigValueType:
    _validate_key_value(key)

    if key.startswith(("@", "__")):
        raise ValueError('key name could not start with "__" or "@" character')

    return service.init(key, value, section)


def cfg_del(key: str = "", section: str = ""):
    _validate_key_value(key)

    service.rm(key, section)


def cfg_get(key: str = "", default: ConfigValueType | None = None, *, section="") -> dict[str, ConfigValueType] | ConfigValueType:
    if key.startswith("@"):
        if section:
            raise ValueError("no section available when using key is volatile")

        return getsysconfig().get(key, default)

    _validate_key_value(key)
    return service.get(key, default, section=section)


def cfg_set(key: str, value: ConfigValueType, section="", *, overwrite: bool = True) -> ConfigValueType:
    _validate_key_value(key)
    return service.set(key, value, section, overwrite=overwrite)


def getsysconfig() -> dict:
    cfg = getattr(sys, "__msys__", None)
    if cfg is None:
        cfg = dict()
        setattr(sys, "__msys__", cfg)
    return cfg


def rebase(uri: str | None = None):
    global service
    proto = None
    sname = None

    uri = uri or service.get("rebase") or cfg_get("@mbase@")
    if uri:
        url = urllib.parse.urlparse(uri)  # type: ignore[arg-type]
        sname, _, proto = url.scheme.partition("+")

    if not proto:
        uri_no_srv_name = uri
        sname = None
    else:
        uri_no_srv_name = uri[len(sname) + 1 :]  # type: ignore[index,arg-type]

    init_local_config_srv(uri_no_srv_name, sname)  # type: ignore[arg-type]

    return cfg_get()


def _app_dir():
    from click import utils

    app_dir = utils.get_app_dir(__distname__)

    if not os.path.exists(app_dir):
        try:
            os.makedirs(app_dir, exist_ok=True)
        except Exception:
            # ignore errors => no config dir
            pass

    return app_dir


def _msys_search_paths():
    return [os.getcwd(), os.path.expanduser(os.path.join("~", "." + __distname__)), _app_dir()]


def _load_cfg(fpath):
    cfg = {}

    with open(fpath) as f:
        with open(fpath) as f:
            cfg = json.load(f)

    if not isinstance(cfg, dict):
        raise IOError(f"{fpath} incompatible configuration file type, dictionary required")

    return cfg


def _search_local_cfg(paths: list[str], filename: str) -> tuple[pathlib.Path | None, dict[str, typing.Any]]:
    cfg = {k: v for k, v in getsysconfig().items() if not k.startswith("@")}

    for path in paths:
        fpath = pathlib.Path(os.path.join(path, filename) if (os.path.isdir(path)) else path)

        if fpath.exists():
            try:
                cfg = _load_cfg(fpath)
                break
            except Exception as e:
                warnings.warn(f'file "{fpath}" found but is invalid: {str(e)}, try to find another one')
                fpath = None  # type: ignore[assignment]
        else:
            fpath = None  # type: ignore[assignment]

    if fpath is None:
        fpath = pathlib.Path(_app_dir(), filename).absolute()

        if fpath.exists():
            fpath = None
        else:
            try:
                with open(fpath, "w") as f:
                    json.dump(cfg, f, indent=_JSON_INDENT)
                warnings.warn(f'new config file created "{fpath.as_uri()}"')
            except Exception as e:
                warnings.warn(f'unable to create config file "{fpath.as_uri()}", config will not be persistent: {str(e)}')
                fpath = None

    return fpath, cfg


service: IConfigSrv = None  # type: ignore[assignment]


def init_local_config_srv(uri: str | None = None, srv_name: str | None = None):
    global service

    if not srv_name:
        service = DefaultConfigSrv(uri)
    else:
        service = ServiceRegistry().new("configs", srv_name, uri)

    cfg_path = _app_dir()

    sys_cfg: dict[str, typing.Any] = {
        "@mversion@": __version__,
        "@mpath@": os.path.dirname(_myrrh_file),
        "@copyright@": __copyright__,
        "@license@": __license__,
        "@etc@": cfg_get("etc") or cfg_path,
        "@var@": cfg_get("var") or cfg_path,
        "@metadata@": dict(importlib.metadata.metadata("myrrh")),  # type: ignore[arg-type]
        "@entities@": [],
    }

    getsysconfig().update(sys_cfg)

    return service
