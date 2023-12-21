from myrrh.framework.mpython.mbuiltins import AbcBuiltins

__mlib__ = "Builtins"


class Builtins(AbcBuiltins):
    try:
        from builtins import WindowsError  # type: ignore[attr-defined]
    except ImportError:
        WindowsError = OSError
