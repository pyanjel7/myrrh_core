import shutil
import traceback
import warnings
import sys
import os
import re
import logging

import pkg_resources
import logging.config
import json

from importlib import metadata

__all__ = [
    "rebase",
    "cfg_get",
    "cfg_set",
    "cfg_del",
    "__distname__",
    "__version__",
    "__copyright__",
    "__license__",
]

myrrh_sys = "myrrh.msys"
__distname__ = "myrrh"

try:
    from ...__license__ import copyright as __copyright__, license as __license__
except Exception:
    __copyright__ = ""
    __license__ = ""

_JSON_INDENT = 2

PID = os.getpid()


def _load(f):
    return json.load(f)


def _save(f, cfg):
    json.dump(cfg, f, indent=_JSON_INDENT)


def myrrh_default_cfg_dirs():
    try:
        from click import utils

        cfg_dir = utils.get_app_dir(__distname__)
    except ImportError:
        cfg_dir = os.path.expanduser(os.path.join("~", "." + __distname__))

    if not os.path.exists(cfg_dir):
        try:
            os.makedirs(cfg_dir)
        except Exception:
            pass  # ignore errors => no config dir

    return [cfg_dir]


def myrrh_versioning(file, dist_name):
    try:
        # try to find version from package dist
        version = pkg_resources.get_distribution(dist_name).version
    except Exception:
        version = "0.0.0"

    if version == "0.0.0":
        # try to find version from scm
        try:
            from setuptools_scm import get_version

            return get_version(relative_to=file)
        except Exception:
            pass

    return version


try:
    from ...__version__ import version as __version__
except Exception:
    __version__ = myrrh_versioning(__file__, __distname__)


def _msysfile(fpath):
    msys = {}
    with open(fpath) as f:
        with open(fpath) as f:
            msys = _load(f)

    if not isinstance(msys, dict):
        raise IOError(f"{fpath} incompatible configuration file type, dictionary required")

    msys["@mbase@"] = os.path.abspath(fpath)

    getattr(sys, "__msys__").update(msys)

    return getattr(sys, "__msys__")


def _msys(paths=None):
    if not paths:
        paths = myrrh_default_cfg_dirs()

    for path in paths:
        fpath = os.path.join(path, myrrh_sys) if (os.path.isdir(path)) else path
        if os.path.isfile(fpath):
            try:
                _msysfile(fpath)
            except Exception as e:
                warnings.warn(f'file "{fpath}" found but is invalid: {str(e)}, try to find another one')
            else:
                break
    else:
        try:
            fpath = os.path.join(paths[0], myrrh_sys)
            if not os.path.exists(fpath):
                with open(fpath, "w") as f:
                    _save(f, dict())

                _msysfile(fpath)
        except Exception:
            fpath = None

    if fpath:
        log = logging.getLogger("myrrh")
        log.info(f"system variables found at {fpath}")

    return getattr(sys, "__msys__")


def _rebase_internal(path=None):
    __msys__ = getattr(sys, "__msys__", {})

    path = path or __msys__.get("@mbase@")
    installed_extensions = __msys__.get("@installed_extensions@") or list()
    entities = __msys__.get("@entities@") or list()

    setattr(
        sys,
        "__msys__",
        {
            "@mversion@": __version__,
            "@mpath@": os.path.dirname(__file__),
            "@copyright@": __copyright__,
            "@license@": __license__,
            "@etc@": myrrh_default_cfg_dirs(),
            "@metadata@": dict(metadata.metadata("myrrh")),
            "@loaded_extensions@": [],
            "@failed_extensions@": [],
            "@installed_extensions@": installed_extensions,
            "@actived_ext_groups@": [],
            "@entities@": entities,
        },
    )

    cwd_file = os.path.join(os.getcwd(), myrrh_sys)

    if path and os.path.isfile(path):
        result = _msysfile(path)

    elif path and os.path.isdir(path):
        result = _msys([path])
    elif os.path.isfile(cwd_file):
        result = _msysfile(cwd_file)
    else:
        result = _msys()

    return result


_CONF_OBJ_TYPE = (
    "loggers",
    "handlers",
    "formatters",
    "filters",
)


def configure_log():
    import configparser

    logging_cfg = cfg_get(section="logging")

    cfg = configparser.RawConfigParser()

    for obj_type in _CONF_OBJ_TYPE:
        cfg.add_section(obj_type)
        cfg[obj_type]["keys"] = logging_cfg.get(obj_type) or ""
        keys = filter(None, re.split(" *, *| +| *; *", cfg[obj_type]["keys"]))
        for key in keys:
            obj_name = obj_type.rstrip("s")
            cfg.add_section(f"{obj_name}_{key}")
            for k, v in cfg_get(section=f"logging.{obj_name}.{key}").items():
                cfg[f"{obj_name}_{key}"][k] = v

    logging.config.fileConfig(cfg, disable_existing_loggers=logging_cfg.get("disable_existing_loggers", True))

    if not cfg_get("enable", True, section="logging"):
        logging.disable()


def rebase(path=None):
    global log

    extension_bkup = sys.__msys__["@loaded_extensions@"] + sys.__msys__["@failed_extensions@"] if hasattr(sys, "__msys__") else None
    extension_groups = sys.__msys__["@actived_ext_groups@"] if hasattr(sys, "__msys__") else None

    result = _rebase_internal(path=None)

    if cfg_get("rebase", False):
        result = _rebase_internal(cfg_get("rebase"))

    cfg_init("rebase", "")

    cfg_init("raise_on_failure", False, section="extensions")
    cfg_init("search_for", True, section="extensions")
    cfg_init("default_value", True, section="extensions")

    cfg_init("enable", False, section="logging")
    cfg_init("version", 1, section="logging")
    cfg_init("incremental", False, section="logging")
    cfg_init("disable_existing_loggers", True, section="logging")
    cfg_init("loggers", "root, myrrh", section="logging")
    cfg_init("handlers", "console, myrrh", section="logging")
    cfg_init("formatters", "myrrh", section="logging")
    cfg_init("filters", "", section="logging")

    cfg_init("level", "CRITICAL", section="logging.logger.root")
    cfg_init("handlers", "console", section="logging.logger.root")

    cfg_init("level", "INFO", section="logging.logger.myrrh")
    cfg_init("handlers", "myrrh", section="logging.logger.myrrh")
    cfg_init("qualname", "myrrh", section="logging.logger.myrrh")
    cfg_init("propagate", "0", section="logging.logger.myrrh")

    cfg_init("class", "StreamHandler", section="logging.handler.myrrh")
    cfg_init("level", "DEBUG", section="logging.handler.myrrh")
    cfg_init("formatter", "myrrh", section="logging.handler.myrrh")
    cfg_init("args", "(sys.stdout,)", section="logging.handler.myrrh")

    cfg_init("class", "StreamHandler", section="logging.handler.console")
    cfg_init("level", "CRITICAL", section="logging.handler.myrrh")
    cfg_init("args", "(sys.stdout,)", section="logging.handler.myrrh")

    cfg_init(
        "format",
        "%(relativeCreated).1f - %(name)s:%(threadName)s - %(levelname)s - %(message)s",
        section="logging.formatter.myrrh",
    )

    log.info("myrrh new session")

    find_ext()

    if extension_groups:
        for group in extension_groups:
            load_ext_group(group)

    if extension_bkup:
        for extension in extension_bkup:
            load_ext(extension)

    return {k: v for k, v in result.items() if not (k.startswith("@") and k.endswith("@"))}


def _cfg_get_section(d, section):
    if not section:
        return d

    if not section.startswith(("__", "@__")):
        section = "__" + section
    if not section.endswith(("__", "__@")):
        section = section + "__"

    if not d.get(section):
        d[section] = dict()

    return d[section]


def _persistent_setcfg(cfg_path, cfg):
    try:
        backup = f"{cfg_path}.bak"
        if os.path.isfile(cfg_path):
            shutil.copy(cfg_path, backup)
        else:
            with open(backup, "w") as f:
                _save(f, cfg)
    except Exception as e:
        log.warning(f"Failed to backup msys config in {cfg_path}: {str(e)}")

    try:
        with open(cfg_path, "w") as f:
            _save(f, cfg)
    except Exception as e:
        log.info(f"Failed to save msys config in {cfg_path}: {str(e)}, config will not be persistante")


def _persistent_getcfg(cfg_path):
    try:
        with open(cfg_path) as f:
            fcfg = _load(f)

        return fcfg
    except Exception as e:
        log.info(f"Failed to load msys config in{cfg_path}: {str(e)}, try restore backup")

    try:
        with open(f"{cfg_path}.bak") as f:
            fcfg = _load(f)

        _persistent_setcfg(cfg_path, fcfg)

        return fcfg

    except Exception as e:
        log.info(f"Failed to load backup msys config in{cfg_path}: {str(e)}, config is lost...")

    return


def cfg_init(key, value, section=""):
    return cfg_set(key, value, section, overwrite=False)


def cfg_set(key, value, section="", *, overwrite=True):
    cfg_path = sys.__msys__.get("@mbase@", "")
    fcfg = None

    if section.startswith("@"):
        raise ValueError('section name could not start with "@" character')

    if key.startswith(("@", "__")):
        raise ValueError('key name could not start with "__" or "@" character')

    if cfg_path:
        fcfg = _persistent_getcfg(cfg_path)

    cfg = sys.__msys__ if fcfg is None else fcfg

    if overwrite or key not in _cfg_get_section(cfg, section):
        _cfg_get_section(cfg, section)[key] = value

        if fcfg is not None:
            _persistent_setcfg(cfg_path, cfg)

        if fcfg and cfg_path:
            _rebase_internal(cfg_path)

    return _cfg_get_section(cfg, section)[key]


def cfg_del(key, section=""):
    cfg_path = sys.__msys__.get("@mbase@", "")
    fcfg = None

    if section.startswith("@"):
        raise ValueError(f'section "{key}" is defined as a runtime section and could not be deleted')

    if key.startswith("@"):
        raise ValueError(f'key "{key}" is defined as a runtime key and could not be deleted')

    if cfg_path:
        fcfg = _persistent_getcfg(cfg_path)

    cfg = sys.__msys__ if fcfg is None else fcfg
    _cfg_get_section(cfg, section).pop(key, None)

    if fcfg is not None:
        _persistent_setcfg(cfg_path, cfg)

    if fcfg is not None and cfg_path:
        _rebase_internal(cfg_path)


def cfg_get(key="", default=None, *, section=""):
    if not key:
        return dict(_cfg_get_section(sys.__msys__, section))

    return _cfg_get_section(sys.__msys__, section).get(key, default)


# decorator
def cfg_prop(section=None, key=None):
    def wrapper(func):
        func.section = _section_name(func) if section is None else section
        func.key = key or func.__name__
        func.default = cfg_init(func.key, func(), section=func.section)

        def _get(self):
            return cfg_get(func.key, default=func.default, section=func.section)

        def _set(self, value):
            cfg_set(func.key, value, section=func.section)

        return property(_get, _set)

    return wrapper


def _section_name(obj):
    import inspect

    mod = inspect.getmodule(obj)
    if not mod:
        return ""

    return mod.__package__ or mod.__name__


class DynCfg:
    def __new__(cls, *a, **kwa):
        if not hasattr(cls, "__SECTION__"):
            cls.__SECTION__ = _section_name(cls)

        return super().__new__(cls, *a, **kwa)

    def all(self):
        return cfg_get(section=self.__SECTION__)

    def init(self, key, value):
        return cfg_init(key, value, section=self.__SECTION__)

    def get(self, key, default=""):
        return cfg_get(key, default=default, section=self.__SECTION__)

    def set(self, key, value=""):
        return cfg_set(key, value, section=self.__SECTION__)


def find_ext():
    if not cfg_get("search_for", section="__extensions__", default=True):
        return

    myrrh_exts = {name: exts for name, exts in metadata.entry_points().items() if name.startswith(f"{__distname__}.")}
    sys.__msys__["@installed_extensions@"] = []
    for _, exts in myrrh_exts.items():
        for ext in exts:
            sys.__msys__["@installed_extensions@"].append(_extension_string(ext.group, ext.name, ext.value))


def _extension_string(group, name, value):
    return f"{group}/{name}={value}"


def _extension_partition(extension):
    group, _, extension = extension.partition("/")
    name, _, value = extension.partition("=")

    return group, name, value


def load_ext(extension, name_value=None):
    cfg = cfg_get(section="__extensions__")

    if name_value:
        group = extension
        name, value = name_value
    else:
        group, name, value = _extension_partition(extension)

    extension = _extension_string(group, name, value)

    if extension in sys.__msys__["@loaded_extensions@"]:
        return

    if extension in sys.__msys__["@failed_extensions@"]:
        sys.__msys__["@failed_extensions@"].remove(extension)

    log.debug(f"load extension: {group}, {name}")

    try:
        callable = metadata.EntryPoint(name, f"{group}:{value}", group).load()
        callable(*name.split("-"))
        sys.__msys__["@loaded_extensions@"].append(f"{extension}")
    except (ModuleNotFoundError, ImportError, Exception) as e:
        sys.__msys__["@failed_extensions@"].append(f"{extension}")
        if cfg.get("raise_on_failure"):
            raise
        log.debug(f"load extension failure : {group}, {name}")
        warnings.warn(f"{''.join(traceback.format_tb(e.__traceback__))}\nFailed to load {name}, this extension will be unavailable: {str(e)}")


def load_ext_group(group):
    sys.__msys__["@actived_ext_groups@"].append(group)

    if not (cfg_get(group, section="__extensions__") or cfg_get("default_value", True, section="__extensions__")):
        return

    ext_cfg = cfg_get(section=f"ext.{group}")

    for name, value in ext_cfg.items():
        load_ext(group, (name, value))

    for installed in sys.__msys__["@installed_extensions@"]:
        if installed.startswith(group):
            load_ext(installed)


#
log = logging.getLogger("myrrh")
rebase()
