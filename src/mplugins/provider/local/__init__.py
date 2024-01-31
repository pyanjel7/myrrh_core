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

    def _session():
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

        return username, uid, gid

    shell_encoding = "cp%d" % windll.kernel32.GetConsoleOutputCP()

else:
    shell_encoding = "utf-8"

    def _session():
        try:
            username = os.getlogin()
            uid = os.geteuid()  # type: ignore[attr-defined]
            gid = os.getegid()  # type: ignore[attr-defined]
        except OSError:
            username = "unknown"
            uid = -1
            gid = -1

        return username, uid, gid


class LocalProviderSettings(myrrh.warehouse.Settings):
    name: typing.Literal["local"]
    cwd: str | None = None


class LocalProvider(myrrh.provider.IProvider):
    """
    Local tools commands
    """

    _name_ = "local"

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
        return ("system", "id", "shell", "vars", "session", "vendor")

    def deliver(self, name: str) -> dict:
        match name:
            case "system":
                return myrrh.warehouse.System(  # type: ignore[call-arg]
                    os=os.name,
                    label=platform.node(),
                    description=":".join(platform.uname()),
                    version=platform.version(),
                    machine=platform.machine(),
                    fsencoding=sys.getfilesystemencoding(),
                    localecode=locale.getlocale()[0] or "LC_CTYPE",
                    encoding=locale.getencoding(),
                    cwd=os.getcwd(),
                    tmpdir=tempfile.gettempdir(),
                ).model_dump()

            case "shell":
                return myrrh.warehouse.Shell(
                    os=os.name,
                    shell=os.environ.get("COMSPEC", "cmd.exe") if WINDOWS else "/bin/sh",
                    shellargs=("/c",) if WINDOWS else ("-c",),
                    encoding=shell_encoding,
                ).model_dump()

            case "vars":
                return myrrh.warehouse.Vars(
                    defined=dict(os.environ),
                ).model_dump()

            case "session":
                username, uid, gid = _session()
                return myrrh.warehouse.Session(
                    login=username,
                    uid=uid,
                    gid=gid
                ).model_dump()

            case "vendor":
                import sysconfig
                return myrrh.warehouse.Vendor(
                    system_ext=sysconfig.get_config_vars(),
                    attrs={
                        'local_provider.version': __version__,
                    }
                )
            case "id":
                return myrrh.warehouse.Id(id=platform.node(), uuid=uuid.uuid1()).model_dump()

            case _:
                return dict()


Provider = LocalProvider
ProviderSettings = LocalProviderSettings
