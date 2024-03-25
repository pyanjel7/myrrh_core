import abc
import typing

__all__ = ["ISecretSrv", "IConfigSrv", "ConfigValueType"]

ConfigValueType = typing.TypeVar("ConfigValueType", int, float, bool, str)


class IConfigSrv(abc.ABC):
    @abc.abstractmethod
    def init(self, key: str, value: ConfigValueType | None, section: str = "") -> dict[str, ConfigValueType] | ConfigValueType: ...

    @abc.abstractmethod
    def rm(self, key: str = "", section: str = ""): ...

    @abc.abstractmethod
    def get(self, key: str = "", default: ConfigValueType | None = None, *, section: str = "") -> dict[str, ConfigValueType] | ConfigValueType: ...

    @abc.abstractmethod
    def set(self, key: str, value: ConfigValueType | None, section: str = "", *, overwrite: bool = True): ...

    @property
    @abc.abstractmethod
    def uri(self) -> str | None: ...


class ISecretSrv(abc.ABC):
    DEFAULT_CFG_SECTION = "myrrh.core.services.secret"

    @abc.abstractmethod
    def set_key(self, save: bool = True, backup_name: str = "", key: str = "") -> str: ...

    @abc.abstractmethod
    def get_key(self, key_name: str) -> str: ...

    @abc.abstractmethod
    def use_key(self, key_name: str) -> None: ...

    @abc.abstractmethod
    def delete_key(self, key_name: str) -> None: ...

    @abc.abstractmethod
    def backup_key(self, backup_name: str = "", key: str | None = None, overwrite: bool = False) -> None: ...

    @abc.abstractmethod
    def rename_key(self, old_key_name: str, new_key_name: str) -> None: ...

    @abc.abstractmethod
    def clean_key_history(self) -> None: ...

    @abc.abstractmethod
    def clean_all_keys(self) -> None: ...

    @abc.abstractmethod
    def dump(self) -> dict[str, str]: ...

    @abc.abstractmethod
    def encrypt(self, url: str, key_name: str | None = None) -> str: ...

    @abc.abstractmethod
    def decrypt(self, url: str, key_name: str | None = None) -> str: ...
