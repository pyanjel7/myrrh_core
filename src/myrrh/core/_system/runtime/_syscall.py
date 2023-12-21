# flake8: noqa: E722
import sys
import typing

from io import BytesIO

from ..managers import runtime_cached_property
from ..managers import RuntimeTaskManager, RuntimeObjectManager

from ...interfaces import IMyrrhOs, IRuntimeObject, IFileInStream, IFileOutStream
from ....provider import Wiring

from ..objects import (
    FileStream,
    FileInOutStream,
    FileInStreamAsync,
    FileOutStreamAsync,
    PipeInStreamAsync,
    PipeOutStreamAsync,
    FileInStream,
    FileOutStream,
    Process,
    InPipe,
    OutPipe,
    Buffer,
    Pipe,
    MHandle,
    InputIo,
)

from ...services.entity import Entity
from ...services import cfg_init
from ....provider import Protocol as _Protocol, Wiring as _Wiring


class RuntimeSyscall:
    MAX_FDS = cfg_init("max_fds", None, section="myrrh.core.services.system")
    POOL_SIZE = cfg_init("system_max_concurren_tasks", 10, section="myrrh.core.services.system")
    IDLE_TIMEOUT = cfg_init("runtime_task_idle_timeout", 0.01, section="myrrh.core.services.system")
    CHUNK_SIZE = cfg_init("runtime_stream_chunk_size", 65535, section="myrrh.core.services.system")

    Wiring = _Wiring
    Protocol = _Protocol

    def __init__(self, myrrh_os: IMyrrhOs):
        self.myrrh_os = myrrh_os

    @runtime_cached_property("fds", init_at_creation_time=True)
    def objects(self) -> RuntimeObjectManager:
        mngr = RuntimeObjectManager(self.MAX_FDS)

        self.hin = mngr.append(
            InputIo(),
            FileStream(sys.stdout.fileno(), b"", b"stdout", getattr(Entity, ".").system.stream),
            FileStream(sys.stderr.fileno(), b"", b"stderr", getattr(Entity, ".").system.stream),
        )
        self.hout = self.hin + 1
        self.herr = self.hin + 2

        return mngr

    @runtime_cached_property("tasks", init_at_creation_time=True)
    def tasks(self) -> RuntimeTaskManager:
        return RuntimeTaskManager(self.POOL_SIZE, self.myrrh_os.cfg.eid)

    def _a_(self, *obj):
        hint = self.objects.append(*obj)
        self.tasks.append(*obj)
        return hint

    def _make_obj_in(self, hint, filestream):
        handle = self.gethandle(self.dup(hint), False)
        if isinstance(handle, InPipe):
            task = PipeOutStreamAsync(filestream, handle)
        else:
            task = Pipe(handle, filestream)

        return task

    def _make_obj_out(self, hint, filestream):
        handle = self.gethandle(self.dup(hint), False)

        if isinstance(handle, OutPipe):
            task = PipeInStreamAsync(filestream, handle)
        else:
            task = Pipe(filestream, handle)

        return task

    def open_file(
        self,
        path: bytes,
        wiring: _Wiring,
        use_async=True,
        extras: dict | None = None,
        protocol: _Protocol | str | None = None,
    ) -> int:
        path = self.myrrh_os.p(path)
        stream = self.myrrh_os.Stream(protocol)

        path, handle = stream.open_file(path, wiring.value, extras=extras)

        filestream = None

        try:
            filestream = FileStream(
                handle,
                self.myrrh_os.dirname(path),
                self.myrrh_os.basename(path),
                self.myrrh_os.stream,
            )

            StreamCls = (FileInStream, FileOutStream) if use_async else (FileInStreamAsync, FileOutStreamAsync)

            match wiring & self.Wiring.INOUT:
                case self.Wiring.INOUT:
                    obj = FileInOutStream(filestream)
                case self.Wiring.IN:
                    obj = StreamCls[0](filestream)
                case self.Wiring.OUT:
                    obj = StreamCls[1](filestream)
                case _:
                    raise TypeError(f"open() invalid mode 0x{wiring.value:x}")

        except:
            try:
                if filestream:
                    filestream.close()
                else:
                    self.myrrh_os.stream.close(handle)
            except:
                pass
            raise

        try:
            return self._a_(obj)
        except:
            try:
                obj.close()
            except:
                pass

            raise

    def open_pipe(self) -> tuple[int, int]:
        buffer = Buffer()

        stream_rd = InPipe(buffer)
        stream_wr = OutPipe(buffer)

        hint = self._a_(stream_rd, stream_wr)
        return hint, hint + 1

    def open_process(
        self,
        path: bytes,
        args: list[bytes] = [],
        working_dir: bytes | None = None,
        env: dict | None = None,
        stdin: int | None = None,
        stdout: int | None = None,
        stderr: int | None = None,
        *,
        extras: dict | None = None,
        protocol: _Protocol | str | None = None,
    ) -> int:
        wiring = Wiring.OFF
        if stdin is not None:
            wiring |= Wiring.IN
        if stdout is not None:
            wiring |= Wiring.OUT
        if stderr is not None:
            wiring |= Wiring.ERR

        if path is None:
            raise ValueError("executable file path can not be None")

        stream = self.myrrh_os.Stream(protocol)
        path, hproc, hin, hout, herr = stream.open_process(path, wiring.value, args, working_dir, env, extras=extras)

        name = self.myrrh_os.basename(path)
        path = self.myrrh_os.dirname(path)

        if hin is not None:
            stdin = self._make_obj_in(stdin, FileStream(hin, path, name, stream))

        if hout is not None:
            stdout = self._make_obj_out(stdout, FileStream(hout, path, name, stream))

        if herr is not None:
            stderr = self._make_obj_out(stderr, FileStream(herr, path, name, stream))

        proc = Process(hproc, path, name, stream, hin, hout, herr)
        hproc = self._a_(proc)
        self.tasks.append(stdin, stdout, stderr)
        self.objects.register_proc(hproc)

        return hproc

    def stream_in(
        self,
        file_path: bytes,
        stream: BytesIO,
        *,
        extras: dict | None = None,
        protocol: _Protocol | str | None = None,
    ):
        fd = self.open_file(file_path, wiring=Wiring.IN, extras=extras, protocol=protocol)
        chunk_size = self.CHUNK_SIZE
        if extras:
            chunk_size = extras.get("chunk_size", chunk_size)

        with self.gethandle(fd) as handle:
            while buf := handle.read(chunk_size):
                sz = 0
                ln = len(buf)
                while sz < ln:
                    sz += stream.write(buf[sz:])

    def stream_out(
        self,
        file_path: bytes,
        stream: BytesIO,
        *,
        extras: dict | None = None,
        protocol: _Protocol | str | None = None,
    ):
        fd = self.open_file(
            file_path,
            wiring=Wiring.OUT | Wiring.CREATE | Wiring.RESET,
            extras=extras,
            protocol=protocol,
        )
        chunk_size = self.CHUNK_SIZE
        if extras:
            chunk_size = extras.get("chunk_size", chunk_size)

        with self.gethandle(fd) as handle:
            while buf := stream.read(chunk_size):
                sz = 0
                ln = len(buf)
                while sz < ln:
                    sz += handle.write(buf[sz:])

    def gethandle(self, hint: int, detach=False) -> MHandle:
        handle = self.objects.gethandle(hint)

        if detach:
            handle.detach()

        return handle

    def getallproc(self) -> tuple[Process]:
        return tuple(self.objects.procs.values())

    def getproc(self, pid: int) -> Process:
        try:
            return self.objects.getprocs(pid)
        except KeyError:
            pass

        raise ChildProcessError(f"unknown child process pid:{pid}")

    def waitobj(self, obj: IRuntimeObject, timeout: float | None = None) -> None:
        task = self.tasks.tget(obj.ehandle)
        if task:
            return task.join(timeout)

    def close(self, handle: MHandle | int) -> None:
        if isinstance(handle, MHandle):
            return handle.close()

        return self.objects.close(handle)

    def dup(self, handle: MHandle | int) -> int:
        return self.objects.dup(handle)

    def dup2(self, handle1: MHandle | int, handle2: MHandle | int) -> int:
        return self.objects.dup2(handle1, handle2)

    def wait(self, handle: int | MHandle, timeout: float | None = None) -> None:
        if not isinstance(handle, MHandle):
            handle = self.gethandle(handle, True)

        if handle.terminated() is None:
            return self.waitobj(handle, timeout)  # type: ignore[arg-type]

        return handle.terminated()

    def read(self, handle: int | MHandle, size, *, extras: dict | None = None):
        if not isinstance(handle, MHandle):
            handle = self.gethandle(handle, True)

        return handle.read(size, extras=extras)

    def write(self, handle: int, data: bytes, *, extras: dict | None = None):
        if not isinstance(handle, MHandle):
            handle = self.gethandle(handle, True)  # type: ignore[arg-type, assignment]

        return handle.write(data, extras=extras)  # type: ignore[attr-defined]
