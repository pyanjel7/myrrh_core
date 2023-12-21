import typing

import pydantic

from .item import BaseItem


class System(BaseItem[typing.Literal["system"]]):
    os: str = ""
    label: str = ""
    description: str = ""
    fsencoding: str = ""
    fsencodeerrors: str = ""
    encoding: str = ""
    encoding_errors: str = ""
    localecode: str = ""
    default_shell_encoding: str = ""

    max_size: int | None = None
    username: int | str | None = None
    uid: int | str | None = None
    gid: int | str | None = None
    groups: list[int] | None = pydantic.Field(default_factory=list)

    shell: str = pydantic.Field("")
    shellargs: tuple[str] = pydantic.Field(
        default_factory=list,
    )
    cwd: str = pydantic.Field(
        "",
    )
    tmpdir: str = pydantic.Field("")
    devnull: str = pydantic.Field("")
    defpath: str = pydantic.Field("")
    rdenv: list[str] = pydantic.Field(default_factory=list)
    env: dict[str, str] = pydantic.Field(default_factory=dict)
    bin: dict[str, str] = pydantic.Field(default_factory=dict)

    @pydantic.field_validator(
        "shell",
        "shellargs",
        "cwd",
        "tmpdir",
        "devnull",
        "defpath",
        "rdenv",
        "env",
        "bin",
        mode="before",
    )
    def decode_after(cls, value, info):
        encoding = info.data.get("encoding")
        encoding_errors = info.data.get("encoding_errors")
        return cls._decode(value, encoding, encoding_errors)

    @property
    def shellb(cls) -> str:
        return cls._encode(cls.shell, cls.encoding, cls.encoding_errors)  # type: ignore[return-value]

    @property
    def shellargsb(cls) -> list[str]:
        return cls._encode(cls.shellargs, cls.encoding, cls.encoding_errors)  # type: ignore[return-value]

    @property
    def cwdb(cls) -> bytes:
        return cls._encode(cls.cwd, cls.encoding, cls.encoding_errors)  # type: ignore[return-value]

    @property
    def tmpdirb(cls) -> bytes:
        return cls._encode(cls.tmpdir, cls.encoding, cls.encoding_errors)  # type: ignore[return-value]

    @property
    def devnullb(cls) -> bytes:
        return cls._encode(cls.devnull, cls.encoding, cls.encoding_errors)  # type: ignore[return-value]

    @property
    def defpathb(cls) -> bytes:
        return cls._encode(cls.defpath, cls.encoding, cls.encoding_errors)  # type: ignore[return-value]

    @property
    def rdenvb(cls) -> list[bytes]:
        return cls._encode(cls.rdenv, cls.encoding, cls.encoding_errors)  # type: ignore[return-value]

    @property
    def envb(cls) -> dict[bytes, bytes]:
        return cls._encode(cls.env, cls.encoding, cls.encoding_errors)  # type: ignore[return-value]

    @property
    def binb(cls) -> dict[bytes, bytes]:
        return cls._encode(cls.bin, cls.encoding, cls.encoding_errors)  # type: ignore[return-value]

    @classmethod
    def _encode(cls, value, encoding, encode_errors) -> bytes | list[bytes] | dict[bytes, bytes]:
        if isinstance(value, bytes):
            return value

        if isinstance(value, (list, tuple)):
            return [cls._encode(s, encoding, encode_errors) for s in value]  # type: ignore[misc]

        if isinstance(value, dict):
            return {cls._encode(k, encoding, encode_errors): cls._encode(v, encoding, encode_errors) for k, v in value.items()}  # type: ignore[misc]

        if isinstance(value, str):
            return value.encode(encoding or "utf8", errors=encode_errors)

        return value

    @classmethod
    def _decode(cls, value, encoding, encode_errors) -> str | list[str] | dict[str, str]:
        if isinstance(value, str):
            return value

        if isinstance(value, (list, tuple)):
            return [cls._decode(b, encoding, encode_errors) for b in value]  # type: ignore[misc]

        if isinstance(value, dict):
            return {cls._decode(k, encoding, encode_errors): cls._decode(v, encoding, encode_errors) for k, v in value.items()}  # type: ignore[misc]

        if isinstance(value, bytes):
            return value.decode(encoding or "utf8", errors=encode_errors)

        return value
