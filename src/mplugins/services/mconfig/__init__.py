import typing
import configparser
import pathlib
import urllib.parse

from types import NoneType

from myrrh.core.interfaces import IConfigSrv
from myrrh.core.services.config import cfg_get


class ConfigSrv(IConfigSrv):
    def __init__(self, uri: str | None, config: dict[str, typing.Any] | None = None):
        if uri is None:
            path = "/$$cfg"
        else:
            path = urllib.parse.unquote(urllib.parse.urlparse(uri).path)

        if path == "/$$cfg":
            self.path = pathlib.Path(cfg_get("@etc@", ".")) / "myrrh.cfg"  # type: ignore[arg-type]
        else:
            self.path = pathlib.Path(urllib.parse.unquote(urllib.parse.urlparse(uri).path))

        self.config = configparser.RawConfigParser()

        if self.path.is_file():
            self._read()
        else:
            self._write()

        if not self.config.has_section("myrrh"):
            self.config.add_section("myrrh")

    def _write(self):
        with self.path.open("w") as f:
            self.config.write(f)

    def _read(self):
        with self.path.open("r") as f:
            self.config.read_file(f)

    def _set_type(self, value, key, section):
        if isinstance(value, (int, float, bool)):
            self.config.set(section, f"{key}.type", f"{value.__class__.__name__}")

        if isinstance(value, NoneType):
            self.config.set(section, f"{key}.type", "null")
            return ""

        return str(value)

    def _getter(self, key, section):
        type = self.config.get(section, f"{key}.type", fallback="str")

        return {"int": self.config.getint, "boolean": self.config.getboolean, "float": self.config.getfloat, "str": self.config.get}.get(type, self.config.get)

    def uri(self):
        return self.path.absolute().as_uri()

    def init(self, key: str, value: typing.Any, section: str = ""):
        return self.set(key, value, section, overwrite=False)

    def rm(self, key: str = "", section: str = ""):
        if not key and section and section != "myrrh":
            self.config.remove_section(section)
        else:
            self.config.remove_option(section, key)

        self._write()

    def get(self, key: str = "", default: typing.Any = None, *, section=""):
        if not key:
            if section and not self.config.has_section(section):
                return dict()

            if section:
                return dict(self.config[section])

            return dict(self.config)
        _get = self._getter(key, section or "myrrh")
        return _get(section or "myrrh", key, fallback=default)

    def set(self, key: str, value, section="", *, overwrite: bool = True):
        if section and not self.config.has_section(section or "myrrh"):
            self.config.add_section(section)

        if overwrite or key not in self.config[section or "myrrh"]:
            value = self._set_type(value, key, section or "myrrh")
            self.config.set(section or "myrrh", key, value)

            self._write()

        return self.get(key, section=section or "myrrh")
