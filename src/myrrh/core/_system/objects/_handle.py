from ...interfaces import IMHandle, IRuntimeObject

__all__ = ("MHandle",)


class MHandle(IMHandle):
    __slots__ = ("val", "_omgr", "_closed", "obj")

    def __new__(cls, val, omgr):
        cls = type(
            cls.__name__,
            (cls,),
            {"obj": omgr.geto(val), "val": int(val), "_omgr": omgr, "_closed": False},
        )

        return object.__new__(cls)

    def __enter__(self):
        return self

    def __exit__(self, _t, _v, _tb):
        self.close()

    def __int__(self):
        return self.val

    def __del__(self):
        try:
            if not self._closed:
                self.close()
        # flake8: noqa: E722
        except:
            pass

    def __repr__(self):
        return f'{self.__class__.__name__}({int(self)}{":closed" if self.closed else ""})->{str(self.obj)}'

    def __getattr__(self, attr):
        return getattr(self.obj, attr)

    def __setattr__(self, attr, value):
        if attr in self.__slots__:
            return super().__setattr__(attr, value)

        return setattr(self.obj, attr, value)

    def close(self):
        if not self._closed:
            self._omgr.close(self)
            self._closed = True

    def detach(self) -> int:
        self._closed = True
        return int(self)

    @property
    def closed(self):
        return self._closed or self.obj.closed


IRuntimeObject.register(MHandle)  # type: ignore[type-abstract]
