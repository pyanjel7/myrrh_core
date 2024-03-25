import typing
import pydantic

from myrrh.core.services import secrets

from ..item import BaseItem, DecodedStr, Optional


class Credential(BaseItem[typing.Literal["credential"]]):
    model_config = pydantic.ConfigDict(extra="forbid")

    login: DecodedStr
    email: Optional[DecodedStr]
    domain: Optional[DecodedStr]
    role: Optional[DecodedStr]
    password: Optional[str]
    private_key: Optional[str]  # type: ignore[valid-type]

    @pydantic.field_validator("password")
    def password_validator(cls, password, info):
        return secrets.encrypt(password)


class Credentials(BaseItem[typing.Literal["credentials"]]):
    """
    Credentials attach to an entity.
    """

    credentials: list[Credential] = pydantic.Field(default_factory=list)
