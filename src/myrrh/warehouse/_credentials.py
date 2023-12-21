import typing
import pydantic

from myrrh.utils import secrets

from .item import BaseItem


class Credential(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")

    login: str = pydantic.Field()
    email: str | None = None
    domain: str | None = None
    role: str | None = None
    password: str | None = None
    private_key: str = ""

    @pydantic.field_validator("password")
    def password_validator(cls, password, info):
        return secrets.encrypt(password)


class Credentials(BaseItem[typing.Literal["credentials"]]):
    """
    Credentials attach to an entity.
    """

    credentials: list[Credential] = pydantic.Field(default_factory=list)
