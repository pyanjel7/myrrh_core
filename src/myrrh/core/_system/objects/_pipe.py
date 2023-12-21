import threading
import os
import stat

from ...services import cfg_init
from ...interfaces import IInOutStream, IInStream, IOutStream, ITask, ABCDelegation

from ._objects import RuntimeObject

PIPE_BUFFER_SIZE = cfg_init("pipe_buffer_size", 1024 * 1024, section="myrrh.core")
PIPE_CHUNK_SIZE = cfg_init("pipe_chunk_size", 2048, section="myrrh.core")

__all__ = ["Buffer", "Pipe"]


class _Lock:
    def __init__(self, lock: threading._RLock | None = None, name: str | None = None):
        self.name = name
        self.cond = threading.Condition(lock) if lock is not None else threading.Condition()

    def __enter__(self):
        self.acquire()

    def __exit__(self, *a, **kwa):
        self.release()

    def acquire(self, blocking=True, timeout=-1):
        return True if self.cond is None else self.cond.acquire(blocking, timeout)

    def release(self):
        if self.cond:
            self.cond.release()

    def wait(self, timeout=None):
        return True if self.cond is None else self.cond.wait(timeout)

    def wait_for(self, predicate, timeout=None):
        return predicate() if self.cond is None else self.cond.wait_for(predicate, timeout)

    def notify(self, n=1):
        if self.cond is not None:
            self.cond.notify(n)

    def notify_all(self):
        if self.cond is not None:
            self.cond.notify_all()


class Buffer(IInOutStream, RuntimeObject):
    def __init__(
        self,
        lock_wr=None,
        lock_rd=None,
        size=PIPE_BUFFER_SIZE,
        chunk_size=PIPE_CHUNK_SIZE,
    ):
        super().__init__(-1, b"", f"buffer-{id(self)}", None)

        self.wr_lock = _Lock(lock_wr, "write")
        self.rd_lock = _Lock(lock_rd, "read")

        self.max_buf_size = size
        self._chunk_size = chunk_size

        self.rd_size = 0
        self.wr_size = self.max_buf_size

        self.rd_pos = 0
        self.wr_pos = 0

        self.to_write_len = 0
        self.to_read_len = 0

        self._buffer = memoryview(bytearray(self.max_buf_size))
        self.closed = False

        self._eot = False
        self._writer_eot = {}

    def __str__(self):
        return f'Buffer(size={self.max_buf_size}){" -> closed" if self.closed else " -> eot" if self.eot else ""}'

    @property
    def eot(self):
        return self._eot

    def send_eot(self, eot, _id=None):
        with self.rd_lock, self.wr_lock:
            self._writer_eot[_id] = eot
            self._eot = all(self._writer_eot.values())

            self.rd_lock.notify_all()
            self.wr_lock.notify_all()

    def write(self, data, *, extras=None):
        timeout = extras.get("timeout") if extras else None

        if self.closed:
            raise BrokenPipeError(f"try to write on closed myrrh io buffer : {self.ehandle}")

        with self.wr_lock:
            while not self.wr_size and not self.closed and not self.eot:
                if not self.wr_lock.wait(timeout):
                    raise TimeoutError

            if self.closed or self.eot:
                raise BrokenPipeError

            self.to_write_len = min(len(data), self._chunk_size)
            self.to_write_len = min(self.to_write_len, self.wr_size)

            from_size_len = min(self.max_buf_size - self.wr_pos, self.to_write_len)

            self._buffer[self.wr_pos : from_size_len + self.wr_pos] = data[:+from_size_len]

            if self.to_write_len > from_size_len:
                self._buffer[0 : self.to_write_len - from_size_len] = data[from_size_len : self.to_write_len]

            self.wr_pos = (self.to_write_len + self.wr_pos) % self.max_buf_size
            self.wr_size -= self.to_write_len

        with self.rd_lock:
            if self.to_write_len:
                self.rd_size += self.to_write_len
                write_len = self.to_write_len
                self.to_write_len = 0
                self.rd_lock.notify_all()

        return write_len

    def flush(self, *, extras=None):
        with self.rd_lock, self.wr_lock:
            self.rd_size += self.to_write_len
            self.to_write_len = 0
            data = bytearray()
            to_read = self.rd_size
            while len(data) < to_read:
                data += self.read(self.rd_size)

        return data

    def sync(self, *, extras=None):
        return

    def read(self, nbytes=None, *, extras=None):
        timeout = extras.get("timeout") if extras else None

        data = memoryview(bytearray(self._chunk_size))

        with self.rd_lock:
            if nbytes == 0:
                return data.obj[:0]

            while not self.rd_size and not self.closed and not self.eot:
                if not self.rd_lock.wait(timeout=timeout):
                    raise TimeoutError

            if (self.closed or self.eot) and self.rd_size == 0:
                return data.obj[:0]

            self.to_read_len = min(self.rd_size, self._chunk_size)

            if nbytes is not None and not nbytes < 0:
                self.to_read_len = min(nbytes, self.to_read_len)

            from_pos_len = min(self.max_buf_size - self.rd_pos, self.to_read_len)
            data[:from_pos_len] = self._buffer[self.rd_pos : from_pos_len + self.rd_pos]

            if from_pos_len < self.to_read_len:
                data[from_pos_len : self.to_read_len] = self._buffer[0 : self.to_read_len - from_pos_len]

            self.rd_pos = (self.rd_pos + self.to_read_len) % self.max_buf_size
            self.rd_size -= self.to_read_len

        with self.wr_lock:
            if self.to_read_len:
                self.wr_size += self.to_read_len
                read_len = self.to_read_len
                self.to_read_len = 0
                self.wr_lock.notify_all()

        return data.obj[:read_len]

    def close(self, *, extras=None):
        with self.wr_lock:
            with self.rd_lock:
                if self.closed:
                    return

                self.closed = True

                self.wr_lock.notify_all()
                self.rd_lock.notify_all()

    def stat(self, *, extras=None):
        return os.stat_result((stat.S_IFIFO, 0, 0, 0, 0, 0, 0, 0, 0, 0))


class Pipe(ITask, ABCDelegation):
    def __init__(self, instream: IInStream, outstream: IOutStream):
        self.instream = instream
        self.outstream = outstream

        self.terminated_by_exception = False
        self.closed = False
        self.outstream.send_eot(False, id(self))

    def __str__(self):
        return f"pipe->{str(self.instream.eref)}, {str(self.outstream.eref)}"

    def task(self):
        try:
            data = self.instream.read(None)
            if data:
                self.outstream.write(data)
            else:
                self.outstream.send_eot(True, id(self))

        except Exception:
            self.terminated_by_exception = True
            self.outstream.send_eot(True, id(self))

            raise

    def terminated(self):
        return (self.terminated_by_exception and (self.instream.closed and self.outstream.closed)) or None
