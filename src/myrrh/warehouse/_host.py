import pydantic
import urllib
import typing

from .item import BaseItem


class Host(BaseItem[typing.Literal["host"]]):
    scheme: str | None = None
    host: str | None = None
    port: int | None = None
    user: str | None = None
    password: str | None = None
    path: str | None = None

    url: pydantic.AnyUrl | None = None

    @pydantic.field_validator("url")
    def url_validate(cls, url, values):
        scheme = values.get("scheme") or ""
        host = values.get("host") or "."

        if not url and not scheme:
            return host

        if not url:
            url = pydantic.AnyUrl.build(
                scheme=scheme,
                host=host,
                port=values.get("port"),
                user=values.get("user"),
                password=values.get("password"),
                path=values.get("path"),
            )
            return url

        user = values.get("user")
        if user and url.user != user:
            raise ValueError

        return url

    def attrs(self, name=None, default=None):
        return self.attributes.get(name, default)

    def geturlsimple(self):
        url = ""
        if self.user:
            user = ":".join(filter(None, (self.user, self.pwd))) if self.user else ""
            url = f"{user}@"
        url = "".join((url, self.hostname))
        if self.port:
            url = ":".join((url, str(self.port)))

        return urllib.parse.urlunsplit(
            (
                self.url.scheme,
                url,
                len(self.url.path) > 1 and self.url.path or "",
                "",
                "",
            )
        )

    def getip(self):
        import socket

        return socket.gethostbyname(self.hostname)
