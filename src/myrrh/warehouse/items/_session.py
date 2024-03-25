import typing


from ..item import BaseItem, DecodedStr, Optional


class Session(BaseItem[typing.Literal["session"]]):
    _volatile = True

    login: Optional[int | DecodedStr]
    domain: Optional[int | DecodedStr]
    uid: Optional[int | DecodedStr]
    gid: Optional[int | DecodedStr]

    groups: Optional[DecodedStr]
    privileges: Optional[DecodedStr]

    cwd: Optional[DecodedStr]
    tmpdir: Optional[DecodedStr]
    homedir: Optional[DecodedStr]
