import os
import sys
import platform
import locale
import tempfile
import uuid

import myrrh
import myrrh.warehouse

from myrrh.provider import EProtocol, IEWarehouseService

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


class Warehouse(IEWarehouseService):
    """
    EService handle all file system function
    """

    protocol = EProtocol.MYRRH

    def catalog(self):
        return ("system", "id", "shell", "vars", "session", "vendor", "directory")

    def deliver(self, data: dict, name: str) -> dict:
        match name:
            case "system":
                return {
                    "os": os.name,
                    "label": ' '.join((platform.system(), platform.release(), platform.machine())),
                    "description": ":".join(platform.uname()),
                    "version": platform.version(),
                    "machine": platform.machine(),
                    "locale": locale.getlocale()[0] or "LC_CTYPE",
                    "encoding": locale.getencoding(),
                }

            case "directory":
                return {
                    "devnull": os.devnull,
                    "bindirs": os.defpath,
                    "tmpdirs": os.pathsep.join(tempfile._candidate_tempdir_list()),  # type: ignore[attr-defined]
                    "encoding": sys.getfilesystemencoding(),
                    "curdir": os.path.curdir,
                    "pardir": os.path.pardir,
                    "extsep": os.path.extsep,
                    "pathsep": os.path.pathsep,
                }

            case "shell":
                return {
                    "path": os.environ.get("COMSPEC", "cmd.exe") if WINDOWS else "/bin/sh",
                    "args": ("/c",) if WINDOWS else ("-c",),
                    "encoding": shell_encoding,
                }

            case "vars":
                return {
                    "defined": dict(os.environ),
                }

            case "session":
                username, uid, gid = _session()
                return {
                    "login": username,
                    "uid": uid,
                    "gid": gid,
                    "cwd": os.getcwd(),
                    "homedir": os.path.expanduser("~"),
                    "tmpdir": tempfile.gettempdir(),
                }

            case "vendor":
                import sysconfig

                return {
                    "system_ext": sysconfig.get_config_vars(),
                    "attrs": {
                        "local_provider.version": myrrh.__version__,
                    },
                }
            case "id":
                return {
                    "id": platform.node(),
                    "uuid": hex(uuid.getnode()),
                }

            case _:
                return dict()
