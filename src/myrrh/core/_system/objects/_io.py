import os
import sys
import threading
import typing

from myrrh.core.interfaces import ICoreStreamService

from ...interfaces import (
    IFileInOutStream,
    IFileInStream,
    IFileOutStream,
    IInStream,
    IOutStream,
    ITask,
    IRuntimeObject,
    Stat,
    ABCDelegation,
)

from ....provider import Whence, StatField

from ._objects import RuntimeObject
from ._pipe import _Lock, Buffer

__all__ = (
    "FileStream",
    "FileInStreamAsync",
    "FileOutStreamAsync",
    "FileInOutStream",
    "FileInStream",
    "FileOutStream",
    "InPipe",
    "OutPipe",
    "PipeInStreamAsync",
    "PipeOutStreamAsync",
    "InputIo",
)


class FileStream(RuntimeObject, IFileInOutStream):
    _eot = False
    service: ICoreStreamService

    def __init__(self, handle: int, path: bytes, name: bytes, service: ICoreStreamService):
        super().__init__(handle, path, name, service)

    @property
    def protocol(self):
        return self.service.protocol

    @property
    def eot(self):
        return self._eot

    def send_eot(self, eot, id=None):
        self._eot = eot

    def read(self, nbytes: int | None = 0, *, extras: dict[str, typing.Any] | None = None) -> bytearray:
        if nbytes is None:
            return self.service.readchunk(self.ehandle, extras=extras)
        if nbytes == 0:
            return self.service.readall(self.ehandle, extras=extras)
        return self.service.read(self.ehandle, nbytes, extras=extras)

    def write(self, data: bytes, *, extras: dict[str, typing.Any] | None = None):
        return self.service.write(self.ehandle, data, extras=extras)

    def close(self, *, extras: dict[str, typing.Any] | None = None) -> None:
        if not self.closed:
            try:
                self.service.close(self.ehandle, extras=extras)
            except OSError:
                ...
            RuntimeObject.close(self)

    def seek(
        self,
        pos: int,
        whence: int = os.SEEK_SET,
        *,
        extras: dict[str, typing.Any] | None = None,
    ) -> int:
        try:
            whence = {
                os.SEEK_CUR: Whence.SEEK_CUR,
                os.SEEK_SET: Whence.SEEK_SET,
                os.SEEK_END: Whence.SEEK_END,
            }[whence].value

            return self.service.seek(self.ehandle, pos, whence, extras=extras)

        except KeyError:
            pass

        raise ValueError(f"Unknown whence method: {whence}")

    def sync(self, *, extras: dict[str, typing.Any] | None = None) -> None:
        return self.service.sync(self.ehandle, extras=extras)

    def flush(self, *, extras: dict[str, typing.Any] | None = None) -> bytearray:
        return self.service.flush(self.ehandle, extras=extras)

    def truncate(self, length: int, *, extras: dict[str, typing.Any] | None = None) -> None:
        return self.service.truncate(self.ehandle, length, extras=extras)

    def stat(self, *, extras: dict[str, typing.Any] | None = None) -> Stat:
        return Stat(**self.service.stat(self.ehandle, fields=StatField.FILE.value))


class FileInStream(IFileInStream, ABCDelegation):
    __delegated__ = (IFileInStream, IRuntimeObject)

    def __init__(self, stream: FileStream):
        self.__delegate__(IFileInStream, stream)
        self.__delegate__(IRuntimeObject, stream)


class FileOutStream(IFileOutStream, ABCDelegation):
    __delegated__ = (IFileOutStream, IRuntimeObject)

    def __init__(self, stream: FileStream):
        self.__delegate__(IFileOutStream, stream)
        self.__delegate__(IRuntimeObject, stream)


class FileInOutStream(IFileInOutStream, ABCDelegation):
    __delegated__ = (IFileInOutStream, IRuntimeObject)

    def __init__(self, stream: IFileInOutStream):
        self.__delegate__(IFileInOutStream, stream)
        self.__delegate__(IRuntimeObject, stream)


class _Pipe(IRuntimeObject, ABCDelegation):
    __delegated__ = (IRuntimeObject,)

    def __init__(self, buffer: Buffer | None = None):
        self.buffer = buffer or Buffer()
        self._eot = False
        self.__delegate__(IRuntimeObject, self.buffer)

    def send_eot(self, val: bool, id_: int | None = None):
        if self._eot != val:
            self.buffer.send_eot(val, id_ or id(self))
            self._eot = val


class InPipe(_Pipe, IInStream, ABCDelegation):
    __delegated__ = (IInStream,)

    def __init__(self, buffer: Buffer | None = None):
        super().__init__(buffer)
        self.__delegate__(IInStream, self.buffer)


class OutPipe(_Pipe, IOutStream, ABCDelegation):
    __delegated__ = (IOutStream,)

    def __init__(self, buffer: Buffer | None = None):
        super().__init__(buffer)
        self.__delegate__(IOutStream, self.buffer)


class PipeInStreamAsync(ITask, ABCDelegation):
    def __init__(self, stream: FileStream, pipe: InPipe):
        self.data = bytearray()
        self.din_lock = _Lock(threading.RLock())
        self.pipe = pipe
        self.stream = stream
        self.exc = None
        self.pipe.send_eot(False)

    def __str__(self):
        return f"<{self.stream.eref}({self.stream.ename})"

    def _eot(self, eot):
        with self.din_lock:
            if self.pipe.eot != eot:
                self.pipe.send_eot(eot)
                self.din_lock.notify_all()

                if eot:
                    self.close()

    def task(self):
        try:
            with self.din_lock:
                if not self.stream.closed:
                    self.data = bytearray(self.stream.read(nbytes=None))
                    if not len(self.data):
                        self._eot(True)

            with self.pipe.buffer.wr_lock:
                p = 0
                try:
                    while p < len(self.data):
                        p += self.pipe.buffer.write(self.data[p:])
                finally:
                    self.data = self.data[p:]

        except Exception as e:
            self.exc = e
            self._eot(True)
            raise

    def sync(self, *, extras: dict[str, typing.Any] | None = None) -> None:
        if self.exc:
            raise self.exc

        with self.din_lock:
            self.stream.sync(extras=extras)

    def close(self, *, extras: dict[str, typing.Any] | None = None):
        try:
            with self.din_lock:
                try:
                    self.pipe.send_eot(True)
                    self.sync()
                except Exception:
                    pass
                finally:
                    self.pipe.close()

        finally:
            try:
                self.stream.close(extras=extras)
            except OSError:
                ...

            with self.din_lock:
                self.din_lock.notify_all()

    def terminated(self):
        return int(self.stream.closed) or None


class PipeOutStreamAsync(ITask, ABCDelegation):
    def __init__(self, stream: FileStream, pipe: OutPipe):
        self.data = bytearray()
        self.dout_lock = _Lock(threading.RLock())
        self.pipe = pipe
        self.stream = stream
        self.exc = None

    def __str__(self):
        return f">{self.stream.eref}({self.stream.ename})"

    def _eot(self):
        self.close()

    def task(self):
        try:
            self.data = self.pipe.buffer.read()
            if not self.data:
                self._eot()
            else:
                self._write()
        except Exception as e:
            self.exc = e
            self._eot()
            raise

    def _write(self, *, extras: dict[str, typing.Any] | None = None):
        p = 0
        with self.dout_lock:
            try:
                while p < len(self.data):
                    p += self.stream.write(self.data[p:], extras=extras)
            finally:
                self.data = self.data[p:]

    def close(self, *, extras: dict[str, typing.Any] | None = None):
        try:
            with self.pipe.buffer.rd_lock:
                with self.dout_lock:
                    try:
                        self.pipe.send_eot(True)
                        self.sync()
                    except Exception:
                        pass
                    finally:
                        self.pipe.close()
        finally:
            try:
                self.stream.close(extras=extras)
            except OSError:
                pass

            with self.dout_lock:
                self.dout_lock.notify_all()

    def sync(self, *, extras: dict[str, typing.Any] | None = None) -> None:
        if self.exc:
            raise self.exc

        with self.pipe.buffer.rd_lock:
            with self.dout_lock:
                self.data.extend(self.pipe.flush())
                assert self.pipe.buffer.rd_size == 0, self.pipe.buffer.rd_size
                self._write(extras=extras)

    def terminated(self):
        return int(self.stream.closed) or None


class FileInStreamAsync(PipeInStreamAsync, IFileInStream, ABCDelegation):
    __delegated__ = (IFileInStream,)

    def __init__(self, stream: FileStream, pipe: InPipe | None = None):
        super().__init__(stream, pipe or InPipe())
        self.__delegate__(IFileInStream, stream)
        self.tell = self.stream.seek(0, os.SEEK_CUR)
        self.pipe.send_eot(False)

    def _eot(self, eot):
        with self.din_lock:
            if self.pipe.eot != eot:
                self.pipe.send_eot(eot)
                self.din_lock.notify_all()

    def flush(self, *, extras: dict[str, typing.Any] | None = None) -> bytearray:
        with self.din_lock:
            with self.pipe.buffer.wr_lock:
                data = self.data
                self.data = bytearray()
                data.extend(self.pipe.flush())
                data.extend(self.stream.flush(extras=extras))
                self._eot(False)
            return data

    def seek(
        self,
        offset: int = 0,
        whence=os.SEEK_SET,
        *,
        timeout: float | None = None,
        extras: dict[str, typing.Any] | None = None,
    ) -> int:
        match whence:
            case os.SEEK_SET | os.SEEK_CUR:
                offset = offset + self.tell if whence == os.SEEK_CUR else offset

                if self.tell == offset:
                    ...
                else:
                    with self.din_lock:
                        self.flush()
                        self.tell = self.stream.seek(offset, os.SEEK_SET, extras=extras)
                        self._eot(False)

            case os.SEEK_END:
                with self.din_lock:
                    self.flush()
                    self.tell = self.stream.seek(offset, whence, extras=extras)
                    self._eot(False)

            case _:
                raise ValueError(whence)

        return self.tell

    def read(self, nbytes=None, *, extras: dict[str, typing.Any] | None = None) -> bytearray:
        if self.exc:
            raise self.exc

        data = self.pipe.read(nbytes)

        self.tell += len(data)

        return data


class FileOutStreamAsync(PipeOutStreamAsync, IFileOutStream, ABCDelegation):
    __delegated__ = (IFileOutStream,)

    def __init__(self, stream: FileStream, pipe: OutPipe | None = None):
        super().__init__(stream, pipe or OutPipe())
        self.__delegate__(IFileOutStream, stream)
        self.tell = self.stream.seek(0, os.SEEK_CUR)

    def _eot(self):
        pass  # no auto close

    def flush(self, *, extras: dict[str, typing.Any] | None = None) -> bytearray:
        if self.exc:
            raise self.exc

        with self.dout_lock:
            data = self.data
            self.data = bytearray()
            data.extend(self.stream.flush(extras=extras))

        return data

    def seek(
        self,
        offset: int = 0,
        whence=os.SEEK_SET,
        *,
        extras: dict[str, typing.Any] | None = None,
    ) -> int:
        if self.exc:
            raise self.exc

        match whence:
            case os.SEEK_SET | os.SEEK_CUR:
                offset = offset + self.tell if whence == os.SEEK_CUR else offset

                if self.tell != offset:
                    with self.dout_lock:
                        self.sync()
                        self.tell = self.stream.seek(offset, os.SEEK_SET, extras=extras)

            case os.SEEK_END:
                with self.dout_lock:
                    self.sync()
                    self.tell = self.stream.seek(offset, whence, extras=extras)

            case _:
                raise ValueError(whence)

        return self.tell

    def truncate(self, length: int, *, extras: dict[str, typing.Any] | None = None) -> None:
        if self.exc:
            raise self.exc

        with self.dout_lock:
            self.sync()
            self.stream.truncate(length, extras=extras)

    def write(
        self,
        data,
        *,
        extras: dict[str, typing.Any] | None = None,
        timeout: float | None = None,
    ) -> int:
        sz = 0

        if self.exc:
            raise self.exc

        try:
            sz += self.pipe.write(data)
        finally:
            self.tell += sz

        return sz


class InputIo(IInStream):
    ehandle = -1
    epath = b""
    eref = ""
    ename = b"stdin"

    @property
    def closed(self):
        return False

    @property
    def eot(self) -> bool:
        return False

    def send_eot(self, eot, id=None):
        return

    def sync(self, *, extras: dict[str, typing.Any] | None = None) -> None:
        return

    def flush(self, *, extras: dict[str, typing.Any] | None = None) -> bytearray:
        return bytearray(b"")

    def stat(self, *, extras: dict[str, typing.Any] | None = None) -> Stat:
        st = os.stat(sys.stdin.fileno())
        return Stat._make(
            (
                st.st_mode,
                st.st_ino,
                st.st_dev,
                st.st_nlink,
                st.st_uid,
                st.st_gid,
                st.st_size,
                st.st_atime,
                st.st_mtime,
                st.st_ctime,
                0,
                None,
            )
        )

    def read(self, nbytes: int | None = None, *, extras: dict[str, typing.Any] | None = None) -> bytearray:
        import _winapi

        stdin = _winapi.GetStdHandle(_winapi.STD_INPUT_HANDLE)  # type: ignore[attr-defined]
        data, _, _ = _winapi.PeekNamedPipe(stdin)  # type: ignore[misc,attr-defined]

        return bytearray(data)

    def close(self):
        self.pinput.__exit__()
