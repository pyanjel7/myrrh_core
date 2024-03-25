import os
import time
import base64

from cryptography import fernet


from .registry import ServiceRegistry
from .config import cfg_get, cfg_set, cfg_del

from ..interfaces import ISecretSrv


def set_key(save: bool = True, backup_name: str = "", key: str = "") -> None:
    service.set_key(save, backup_name, key)


def get_key(key_name: str) -> str:
    return service.get_key(key_name)


def use_key(key_name: str) -> None:
    service.use_key(key_name)


def delete_key(key_name: str) -> None:
    service.use_key(key_name)


def backup_key(backup_name: str = "", key: str | None = None, overwrite: bool = False) -> None:
    service.backup_key(backup_name, key, overwrite)


def rename_key(old_key_name: str, new_key_name: str) -> None:
    service.backup_key(old_key_name, new_key_name)


def clean_key_history(self) -> None:
    service.clean_key_history()


def clean_all_keys(self) -> None:
    service.clean_all_keys()


def dump(self) -> dict[str, str]:
    return service.dump()


def encrypt(url: str, key_name: str | None = None) -> str:
    return service.encrypt(url, key_name)


def decrypt(url: str, key_name: str | None = None) -> str:
    return service.decrypt(url, key_name)


InvalidToken = fernet.InvalidToken


def _cfg_get(key="", default=None) -> dict | str:
    return cfg_get(key, default=default, section=ISecretSrv.DEFAULT_CFG_SECTION)


def _cfg_set(key, value, overwrite=True):
    return cfg_set(key, value, section=ISecretSrv.DEFAULT_CFG_SECTION, overwrite=overwrite)


def _cfg_del(key):
    return cfg_del(key, section=ISecretSrv.DEFAULT_CFG_SECTION)


def _get_real_key_name(key_name):
    if not key_name:
        return f"key.{str(time.monotonic())}"

    if key_name == "key":
        return key_name

    if key_name.startswith(("key.", "key_")):
        return key_name

    if key_name.startswith((".", "_")):
        return "".join(("key", key_name))

    return "_".join(("key", key_name))


PROTO_PLAIN = "plain-text"
PROTO_FERMET = "fernet"
PROTO_SEP = "://"
PROTO_ALL = ("plain-text", "fernet")


class DefaultSecretSrv(ISecretSrv):
    def set_key(self, save: bool = True, backup_name: str = "", key: str = "") -> str:
        old_key: str = _cfg_get("key")  # type: ignore[assignment]

        if save and old_key:
            self.backup_key(backup_name, old_key)

        if not key:
            key = base64.urlsafe_b64encode(os.urandom(_cfg_get("key_len", 32))).decode()  # type: ignore[arg-type]

        if save:
            _cfg_set("key", key)

        return key

    def get_key(self, key_name: str | None) -> str:
        return _cfg_get(_get_real_key_name(key_name))  # type: ignore[return-value]

    def use_key(self, key_name: str) -> None:
        key = self.get_key(key_name)
        if key:
            self.set_key(key=key)

    def delete_key(self, key_name: str) -> None:
        _cfg_del(_get_real_key_name(key_name))

    def backup_key(self, backup_name: str = "", key: str | None = None, overwrite: bool = False) -> None:
        if key is None:
            key = _cfg_get("key")  # type: ignore[assignment]

        backup_name = _get_real_key_name(backup_name)
        backup_name = _cfg_get(backup_name) and ".".join((backup_name, str(time.monotonic()))).replace("_", ".") or backup_name

        _cfg_set(_get_real_key_name(backup_name), key, overwrite=overwrite)

    def rename_key(self, old_key_name: str, new_key_name: str) -> None:
        old_key_name = _get_real_key_name(old_key_name)
        new_key_name = _get_real_key_name(new_key_name)

        existing_key = _cfg_get(new_key_name)
        key = _cfg_get(old_key_name)

        if key:
            if existing_key:
                self.backup_key(new_key_name, key=existing_key)  # type: ignore[arg-type]
            _cfg_set(new_key_name, key)  # type: ignore[arg-type]
            _cfg_del(old_key_name)

    def clean_key_history(self) -> None:
        secret = _cfg_get() or dict

        for k in secret:  # type: ignore[union-attr]
            if k.startswith("key."):
                _cfg_del(k)

    def clean_all_keys(self) -> None:
        secret = _cfg_get() or dict()

        for k in secret:
            if k.startswith("key"):
                _cfg_del(k)

    def dump(self) -> dict[str, str]:
        return _cfg_get()  # type: ignore[return-value]

    def encrypt(self, url: str, key_name: str | None = None) -> str:
        key_name = key_name or "key"

        proto, _, msg = url.rpartition(PROTO_SEP)
        if proto and proto != PROTO_PLAIN:
            return url

        key = self.get_key(key_name)  # type: ignore[return-value]
        if not key:
            return url

        if not isinstance(msg, bytes):
            msg = msg.encode()  # type: ignore[arg-type,assignment]

        try:
            return PROTO_FERMET + PROTO_SEP + fernet.Fernet(key).encrypt(msg).decode()  # type: ignore[arg-type,assignment]
        except InvalidToken:
            pass

        return url

    def decrypt(self, url: str, key_name: str | None = None) -> str:
        key_name = key_name or "key"

        proto, _, token = url.rpartition(PROTO_SEP)
        if proto and proto != PROTO_FERMET:
            return url

        key = self.get_key(key_name)
        if not key:
            return url

        if not isinstance(token, bytes):
            token = token.encode()  # type: ignore[assignment]
        try:
            return fernet.Fernet(key).decrypt(token).decode()
        except InvalidToken:
            pass

        return url


service: ISecretSrv = DefaultSecretSrv()


def init_secret_srv(name: str | None = None, *a, **kwa):
    global service

    service_name = name or cfg_get("use", "default", section=ISecretSrv.DEFAULT_CFG_SECTION)
    if service_name != "default":
        try:
            service = ServiceRegistry().new("secrets", service_name, *a, **kwa)
        except Exception as e:
            import warnings

            warnings.warn(f"unable to get secret service {service_name}, use default: {str(e)}")

    if not service.get_key("key"):
        service.set_key(key="key")


def __getattr__(name):
    return getattr(service, name)


init_secret_srv()
