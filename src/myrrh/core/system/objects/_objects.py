from ...interfaces import IRuntimeObject, IECoreService

__all__ = ("RuntimeObjectProxy", "RuntimeObject")


class RuntimeObject(IRuntimeObject):
    __slots__ = ("epath", "ename", "ehandle", "eref")

    epath: str
    ename: str
    ehandle: int
    eref: str

    closed = False

    def __init__(self, handle: int, path: str, name: str, service: IECoreService | None):
        self.ehandle: int = handle
        self.service = service
        self.epath = path
        self.ename = name

        if service:
            self.eref = "/".join((service.eref(), str(self.ehandle)))
        else:
            self.eref = f"./{id(self)}"

    def __del__(self):
        self.close()

    def close(self):
        self.closed = True


class RuntimeObjectProxy(RuntimeObject):
    def __init__(self, obj, stream):
        handle = getattr(obj, "fileno", lambda: -777)()
        name = getattr(obj, "name", "")
        path = getattr(obj, "path", "")

        super().__init__(handle, path, name, stream)

        self.obj = obj

    def __getattr__(self, name):
        return getattr(self.obj, name)
