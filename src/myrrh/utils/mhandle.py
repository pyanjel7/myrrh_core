import errno
import os
import threading
import typing


class LightHandler:
    _handles: dict[int, typing.Any] = dict()
    _key = 4
    _lock = threading.RLock()

    def new(self, *info):
        with self._lock:
            handle = self._key

            self._handles[self._key] = info
            self._key += 1

            return handle

    def _info(self, info, ninfo):
        if info and ninfo is not None:
            try:
                info = info[ninfo]
            except IndexError:
                info = None

        if info is None:
            raise OSError(errno.EBADF, os.strerror(errno.EBADF))

        return info

    def close(self, handle, ninfo=None):
        with self._lock:
            info = self._handles.pop(handle, None)
            return self._info(info, ninfo)

    def h(self, handle, ninfo=None):
        with self._lock:
            info = self._handles.get(handle)
            return self._info(info, ninfo)
