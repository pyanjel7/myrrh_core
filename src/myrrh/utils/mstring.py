"""
**String manipulation and translation helper module**

-----------------
"""

import pathlib
import re
import typing


def str2int(str, default=None):
    if isinstance(str, int):
        return str

    str = str and str.strip()

    if not str:
        return default

    try:
        int_str = str if len(str) > 0 and str[0] != "0" or str.startswith("0x") else "0x%s" % str
        return int(int_str, 0)
    except ValueError:
        return str if default is None else default


def cast(_val, encoding="utf-8", errors="surrogateescape"):
    if isinstance(_val, bytes):
        return typebytes(encoding, errors)
    if isinstance(_val, str):
        return typestr(encoding, errors)
    if isinstance(_val, bytearray):
        return typebytearray(encoding, errors)
    if isinstance(_val, memoryview):
        return typememoryview(encoding, errors)
    if isinstance(_val, pathlib.PurePath):
        return typestr(encoding, errors)
    if hasattr(_val, "path"):
        return cast(_val.path, encoding, errors)
    raise TypeError("invalid parameter type")


def typebytes(encoding="utf-8", errors="surrogateescape"):
    class wrapper(bytes):
        def __new__(cls, val: str | bytes):
            if isinstance(val, bytes):
                return val
            try:
                return val.encode(encoding, errors=errors)
            except AttributeError:
                if isinstance(val, (bytearray, memoryview)):
                    return bytes(val)
                return val

        revert = typestr(encoding=encoding, errors=errors)

    return wrapper


def typestr(encoding="utf-8", errors="surrogateescape"):
    class wrapper(str):
        def __new__(cls, val: str | bytes):
            if isinstance(val, str):
                return val
            try:
                return val.decode(encoding, errors=errors)
            except AttributeError:
                if isinstance(val, memoryview):
                    return val.tobytes().decode(encoding, errors=errors)
                return val

    return wrapper


def typebytearray(encoding="utf-8", errors="surrogateescape"):
    class wrapper(bytearray):
        def __new__(cls, val: str | bytes):
            val = typebytes(encoding, errors)(val)
            try:
                return bytearray(val)
            except (AttributeError, UnicodeDecodeError):
                return val

    return wrapper


def typememoryview(encoding="utf-8", errors="surrogateescape"):
    def wrapper(val: str | bytes):
        val = typebytes(encoding, errors)(val)
        try:
            return memoryview(val)
        except (AttributeError, UnicodeDecodeError):
            return val

    return wrapper


def hr_size_toint(str):
    if str is None or str == "" or isinstance(str, (int, float)):
        return str

    gr = re.match(r"([\d\.]+)(?:([BKMGTbkmgt])(i)?[bB]?)?", str)
    if not gr:
        raise ValueError('can not parse string "%s" in bytes' % str)

    val, unit, bi = gr
    val = str2int(val)
    unit = unit.lower() if unit else "b"
    bi = 1024 if bi else 1000

    return val * {"b": 1, "k": bi, "m": bi**2, "g": bi**3, "t": bi**4}.get(unit)


def hr_size(size: int) -> str:
    """
    convert byte size to human readable string
    """
    for unit in ["", "Ki", "Gi"]:
        if abs(size) < 1024:
            break
        size = int(size / 1024)

    return "%.1f%sB" % (size, unit if size < 1024 else "T")


# copy from client.py
def bytestohostport(host, port=None):
    # host contains port only
    try:
        return b"", int(host)
    except ValueError:
        pass

    i = host.rfind(b":")
    j = host.rfind(b"]")  # ipv6 addresses have [...]
    if i > j:
        try:
            port = int(host[i + 1 :])
        except ValueError:
            if host[i + 1 :] != "":  # http://foo.com:/ == http://foo.com/
                raise ValueError("nonnumeric port: '%s'" % host[i + 1 :]) from None
        host = host[:i]
    else:
        port = port

    if host and host[0] == "[" and host[-1] == "]":
        host = host[1:-1]

    return (host, port)


def encode(value, encoding: str = "utf8", errors: str = "strict") -> bytes | list[bytes] | dict[bytes, bytes]:
    if isinstance(value, bytes):
        return value

    if isinstance(value, (list, tuple)):
        return [encode(s, encoding, errors) for s in value]  # type: ignore[misc]

    if isinstance(value, dict):
        return {encode(k, encoding, errors): encode(v, encoding, errors) for k, v in value.items()}  # type: ignore[misc]

    if isinstance(value, str):
        return value.encode(encoding, errors=errors)

    return value


def decode(value, encoding: str = "utf8", errors: str = "strict") -> str | list[str] | dict[str, str]:
    if isinstance(value, str):
        return value

    if isinstance(value, (list, tuple)):
        return [decode(b, encoding, errors) for b in value]  # type: ignore[misc]

    if isinstance(value, dict):
        return {decode(k, encoding, errors): decode(v, encoding, errors) for k, v in value.items()}  # type: ignore[misc]

    if isinstance(value, bytes):
        return value.decode(encoding, errors=errors)

    return value


def encoder(encoding: str = "utf8", errors: str = "strict"):
    def wrapper(value):
        return encode(value, encoding, errors)

    return wrapper


def decoder(encoding: str = "utf8", errors: str = "strict"):
    def wrapper(value):
        return decode(value, encoding, errors)

    return wrapper


DecodedTypeVar = typing.TypeVar("DecodedTypeVar", str, list, dict, bytes)


def DecodedType(cls, encoding, errors):
    import types

    return types.new_class(
        f"{cls.__name__}.{encoding}.{errors}",
        bases=(cls,),
        kwds={"_encodings": (encoding, errors)},
    )


class Decoded(typing.Generic[DecodedTypeVar]):
    _encodings: tuple[str, str] = ("utf8", "strict")

    def __new__(cls, *a, **kwa):
        if a:
            value = decode(a[0], *cls._encodings)

            return super().__new__(cls, value, *a[1:], **kwa)

        return super().__new__(cls, *a, **kwa)

    def __init__(self, *a, **kwa) -> None:
        if a:
            value = decode(a[0], *self._encodings)
            super().__init__(value, *a[1:], **kwa)  # type: ignore[call-arg]
            return

        super().__init__(*a, **kwa)

    def __init_subclass__(cls, **kwa) -> None:
        cls._encodings = kwa.get("_encodings") or cls._encodings

    @property
    def e(self) -> bytes | list[bytes] | dict[bytes, bytes]:
        return encode(self, *self._encodings)

    @property
    def d(self) -> str | list[str] | dict[str, str]:
        return decode(self, *self._encodings)


class MString(Decoded[str], str):
    def encode(self, encoding: str = "", errors: str = "strict") -> bytes:
        if not encoding and not errors:
            return self.e  # type: ignore[return-value]

        encoding = encoding or "utf8"

        return super().encode(encoding, errors)

    def __init__(self, *a, **kwa) -> None: ...


class MList(Decoded[list], list): ...


class MDict(Decoded[dict], dict): ...
