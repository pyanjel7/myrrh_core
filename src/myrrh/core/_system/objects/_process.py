from ...interfaces import IProcess, Stat, ICoreStreamService
from ...services import cfg_init
from ....provider import StatField

from ._objects import RuntimeObject

POLL_STEP = cfg_init("process_poll_delay", 0.01, section="myrrh.core")

__all__ = ("Process",)


class Process(RuntimeObject, IProcess):
    pid = 0
    service: ICoreStreamService

    def __init__(
        self,
        handle: int,
        path: bytes,
        name: bytes,
        service: ICoreStreamService,
        hin: int | None,
        hout: int | None,
        herr: int | None,
    ):
        super().__init__(handle, path, name, service)

        if service.stat(handle, StatField.PID.value).get("st_pid") is None:
            raise RuntimeError(f'Unable to get pid of process: {path.decode(errors="ignore")}')

        self.pid = service.stat(handle, StatField.PID.value).get("st_pid")  # type: ignore[assignment]

        self._exit_status = None
        self.hs = (hin, hout, herr)

    def __str__(self):
        return f"{self.eref}->proc"

    def task(self):
        try:
            st = self.stat(StatField.STATUS)
            self._exit_status = st.st_status

            return self._exit_status

        except Exception:
            self._exit_status = -1
            raise

    @property
    def exit_status(self):
        return self._exit_status

    def terminate(self, *, extras=None):
        return self.service.terminate(self.ehandle, extras=extras)

    def stat(self, fields=StatField.ALL, *, extras=None) -> Stat:
        return Stat(**self.service.stat(self.ehandle, fields, extras=extras))

    def close(self):
        if not self.closed:
            self.closed = True
            self.service.close(self.ehandle)

    def terminated(self):
        return self._exit_status
