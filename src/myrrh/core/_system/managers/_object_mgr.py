import errno
import os
import threading
import weakref

from ..objects import MHandle
from ...interfaces import IRuntimeObject, IProcess


__all__ = ("RuntimeObjectManager",)


class RuntimeObjectManager:
    def __init__(self, max_fds: int | None = None) -> None:
        self.max_fds = max_fds

        self.lock = threading.RLock()
        self.fds: list[IRuntimeObject | None] = list()
        self.procs: dict[int, IProcess] = weakref.WeakValueDictionary()  # type: ignore[assignment]

        if max_fds:
            self.fds.extend([None] * max_fds)

    def get_free_hint(self, count=1):
        with self.lock:
            try:
                first = self.fds.index(None)
                while any(map(lambda o: o is not None, self.fds[first : first + count])):
                    first = self.fds.index(None, first + 1)

                if first + count < len(self.fds):
                    return first

            except ValueError:
                ...

            if not self.max_fds:
                first = len(self.fds)
                self.fds.extend([None] * max(len(self.fds), count * 2))

                return first

            raise OSError(errno.EMFILE, os.strerror(errno.EMFILE))

    def geto(self, hint: int | MHandle) -> IRuntimeObject:
        return weakref.proxy(self._geto(hint))

    def _geto(self, hint) -> IRuntimeObject:
        try:
            obj = self.fds[int(hint)]
            if obj is not None:
                return obj
        except IndexError:
            pass

        raise OSError(errno.EBADF, f"{os.strerror(errno.EBADF)}: {int(hint)}")

    def append(self, *objs: IRuntimeObject) -> int:
        with self.lock:
            hint = self.get_free_hint(count=len(objs))

            for i in range(0, len(objs)):
                obj = objs[i]
                try:
                    self.fds[hint + i] = obj
                except Exception:
                    ...

            return hint

    def register_proc(self, hint):
        with self.lock:
            obj = self._geto(hint)
            self.procs[obj.pid] = obj

    def dup(self, hint: int | MHandle):
        with self.lock:
            hint2 = self.get_free_hint()
            object = self._geto(hint)

            self.fds[hint2] = object

            object.__m_ref_count__ += 1

        return hint2

    def dup2(self, hint: int | MHandle, hint2: int | MHandle):
        with self.lock:
            object = self._geto(hint)

            try:
                self.close(hint2)
            except OSError:
                if OSError.errno == errno.EBADF:
                    pass
                raise

            if not self.max_fds and int(hint2) >= len(self.fds):
                inc = int(hint2) - len(self.fds) + 1
                self.fds.extend([None] * inc)

            self.fds[hint2] = object
            object.__m_ref_count__ += 1

        return hint2

    def close(self, hint: int | MHandle):
        obj = self._geto(hint)
        if not obj.__m_ref_count__ and not obj.closed:
            obj.close()
        else:
            obj.__m_ref_count__ -= 1

        self.fds[int(hint)] = None

    def gethandle(self, hint: int | MHandle) -> MHandle:
        return MHandle(int(hint), self)

    def getrefs(self, hint: int | MHandle) -> tuple[int]:
        with self.lock:
            obj = self._geto(hint)
            return tuple(filter(lambda h: self.fds[h] is obj, range(0, len(self.fds))))  # type: ignore[return-value]

    def getprocs(self, pid=0):
        try:
            return (self.procs[pid],)
        except KeyError:
            pass

        raise ChildProcessError
