import pydantic
import typing

SettingsT = typing.TypeVar("SettingsT")


class Settings(pydantic.BaseModel):
    def attrs(self) -> dict[str, typing.Any]:
        return super().model_dump(
            exclude={
                "name",
            }
        )


class Supply(pydantic.BaseModel, typing.Generic[SettingsT]):
    settings: list[SettingsT] = pydantic.Field(default_factory=list)

    paths: list[str]

    pre: list = pydantic.Field(default_factory=list)
    post: list = pydantic.Field(default_factory=list)
