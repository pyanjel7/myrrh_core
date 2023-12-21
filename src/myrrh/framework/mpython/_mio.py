from myrrh.core.services.system import AbcRuntime

__mlib__ = "AbcIo"


class AbcIo(AbcRuntime):
    __frameworkpath__ = "mpython._mio"

    from _io import FileIO  # type: ignore

    class FileIO(FileIO):  # type: ignore[no-redef]
        def open(*a, **kwa):
            ...
