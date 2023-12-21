import os
import sys
import platform
import locale
import uuid
import tempfile
import typing

import myrrh

import myrrh.warehouse
import myrrh.provider


from .system import Shell, Stream, FileSystem, StreamSystemAPI

__version__ = myrrh.__version__

WINDOWS = sys.platform == "win32"

if WINDOWS:
    import ctypes
    from ctypes import windll  # type: ignore[attr-defined]

    default_shell_encoding = "cp%d" % windll.kernel32.GetConsoleOutputCP()

    def GetUserName(format):
        buf = None
        sz = ctypes.pointer(ctypes.c_ulong(0))
        try:
            ctypes.windll.secur32.GetUserNameExW(format, buf, sz)
            buf = ctypes.create_unicode_buffer(sz.contents.value)
            if windll.secur32.GetUserNameExW(format, buf, sz):
                return buf.value
        finally:
            if buf is not None:
                del buf
            del sz

    username = GetUserName(2) or os.getlogin()
    uid = GetUserName(6)
    gid = None

else:
    default_shell_encoding = "utf-8"
    try:
        username = os.getlogin()
        uid = os.geteuid()  # type: ignore[attr-defined]
        gid = os.getegid()  # type: ignore[attr-defined]
    except OSError:
        username = "unknown"
        uid = -1
        gid = -1


class LocalProviderSettings(myrrh.warehouse.Settings):
    name: typing.Literal["local"]
    cwd: str | None = None


class Provider(myrrh.provider.IProvider):
    """
    Local tools commands
    """

    def __init__(self, settings=None):
        """
        instantiate specific local services
        """
        if settings and settings.cwd:
            cwd = os.path.expandvars(settings.cwd)
            cwd = os.path.expanduser(cwd)
            os.chdir(cwd)

    def services(self):
        return (Stream, Shell, FileSystem, StreamSystemAPI)

    def catalog(self):
        return ("system", "id")

    def deliver(self, name: str) -> dict:
        match name:
            case "system":
                cwd = os.getcwd()
                return myrrh.warehouse.System(  # type: ignore[call-arg]
                    os=os.name,
                    label=platform.node(),
                    description=":".join(platform.uname()),
                    fsencoding=sys.getfilesystemencoding(),
                    localecode=locale.getlocale()[0] or "LC_CTYPE",
                    encoding=locale.getencoding(),
                    default_shell_encoding=default_shell_encoding,
                    shell=os.environ.get("COMSPEC", "cmd.exe") if WINDOWS else "/bin/sh",
                    shellargs=("/c",) if WINDOWS else ("-c",),
                    cwd=cwd,
                    username=username,
                    uid=uid,
                    gid=gid,
                    tmpdir=tempfile.gettempdir(),
                    env=dict(os.environ),
                ).model_dump()

            case "id":
                return myrrh.warehouse.Id(id=platform.node(), uuid=uuid.uuid1()).model_dump()

            case _:
                return dict()


provider = Provider
provider_settings = LocalProviderSettings
