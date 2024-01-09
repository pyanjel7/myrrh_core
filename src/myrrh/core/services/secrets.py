import os
import time
import base64

from cryptography import fernet
from myrrh.core.services import cfg_get, cfg_set, cfg_del

__all__ = [
    "InvalidToken",
    "clean_key_history",
    "clean_all_keys",
    "dump",
    "backup_key",
    "delete_key",
    "get_key",
    "use_key",
    "rename_key",
]


InvalidToken = fernet.InvalidToken


def _cfg_get(key="", default=None):
    return cfg_get(key, default=default, section="secret")


def _cfg_set(key, value, overwrite=True):
    return cfg_set(key, value, section="secret", overwrite=overwrite)


def _cfg_del(key):
    return cfg_del(key, section="secret")


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


def set_key(save=True, backup_name="", key=""):
    old_key = _cfg_get("key")

    if save and old_key:
        backup_key(backup_name, old_key)

    if not key:
        key = base64.urlsafe_b64encode(os.urandom(_cfg_get("key_len", 32))).decode()

    if save:
        _cfg_set("key", key)

    return key


if not _cfg_get("key"):
    set_key()


def get_key(key_name):
    return _cfg_get(_get_real_key_name(key_name))


def clean_key_history():
    secret = _cfg_get() or dict

    for k in secret:
        if k.startswith("key."):
            _cfg_del(k)

    return _cfg_get()


def clean_all_keys():
    secret = _cfg_get() or dict()

    for k in secret:
        if k.startswith("key"):
            _cfg_del(k)

    return _cfg_get()


def dump():
    return _cfg_get()


def backup_key(backup_name="", key=None, overwrite=False):
    if key is None:
        key = _cfg_get("key")

    backup_name = _get_real_key_name(backup_name)
    backup_name = _cfg_get(backup_name) and ".".join((backup_name, str(time.monotonic()))).replace("_", ".") or backup_name

    _cfg_set(_get_real_key_name(backup_name), key, overwrite=overwrite)


def delete_key(key_name):
    _cfg_del(_get_real_key_name(key_name))


def use_key(key_name):
    key = get_key(key_name)
    if key:
        set_key(key=key)


def rename_key(old_key_name, new_key_name):
    old_key_name = _get_real_key_name(old_key_name)
    new_key_name = _get_real_key_name(new_key_name)

    existing_key = _cfg_get(new_key_name)
    key = _cfg_get(old_key_name)

    if key:
        if existing_key:
            backup_key(new_key_name, key=existing_key)
        _cfg_set(new_key_name, key)
        _cfg_del(old_key_name)


PROTO_PLAIN = "plain-text"
PROTO_FERMET = "fernet"
PROTO_SEP = "://"
PROTO_ALL = ("plain-text", "fernet")


def encrypt(url, key_name="key"):
    proto, _, msg = url.rpartition(PROTO_SEP)
    if proto and proto != PROTO_PLAIN:
        return url

    key = get_key(key_name)
    if not key:
        return url

    if not isinstance(msg, bytes):
        msg = msg.encode()

    try:
        return PROTO_FERMET + PROTO_SEP + fernet.Fernet(key).encrypt(msg).decode()
    except InvalidToken:
        pass

    return url


def decrypt(url, key_name="key"):
    proto, _, token = url.rpartition(PROTO_SEP)
    if proto and proto != PROTO_FERMET:
        return url

    key = get_key(key_name)
    if not key:
        return url

    if not isinstance(token, bytes):
        token = token.encode()
    try:
        return fernet.Fernet(key).decrypt(token).decode()
    except InvalidToken:
        pass

    return url
