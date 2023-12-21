import threading
import time
import typing

from concurrent.futures import Future, CancelledError, InvalidStateError

from ...services import log
from ...interfaces import ITask, IRuntimeTaskManager
from ....utils import mtimer


__all__ = ("RuntimeTask",)

PENDING = "PENDING"
RUNNING = "RUNNING"
IDLE = "IDLE"
CANCELLED = "CANCELLED"
CANCELLED_AND_NOTIFIED = "CANCELLED_AND_NOTIFIED"
FINISHED = "FINISHED"


# copy of "Future" source code in concurrent.futures
# adapted to support idle state
# (consult the PSF for licence agreement)
class TaskFuture(Future):
    def __enter__(self):
        return self._condition.__enter__()

    def __exit__(self, *args):
        return self._condition.__exit__(*args)

    def idle(self, timeout=None):
        try:
            with self._condition:
                if self._state in [CANCELLED, CANCELLED_AND_NOTIFIED]:
                    raise CancelledError()
                elif self._state in [IDLE, FINISHED]:
                    return super().result()

                self._condition.wait(timeout)

                if self._state in [CANCELLED, CANCELLED_AND_NOTIFIED]:
                    raise CancelledError()
                elif self._state in [IDLE, FINISHED]:
                    return super().result()
                else:
                    raise TimeoutError()
        finally:
            self = None

    def result(self, timeout=None):
        try:
            with self._condition:
                if self._state in [CANCELLED, CANCELLED_AND_NOTIFIED]:
                    raise CancelledError()
                elif self._state == FINISHED:
                    return super().result()

                timer = mtimer.MTimer(timeout=timeout)
                while self._state in [RUNNING, IDLE, PENDING]:
                    self._condition.wait(timer.timeleft)

                if self._state in [CANCELLED, CANCELLED_AND_NOTIFIED]:
                    raise CancelledError()
                elif self._state == FINISHED:
                    return super().result()
                else:
                    raise TimeoutError()
        finally:
            self = None

    def running(self):
        with self._condition:
            return self._state in [RUNNING, IDLE]

    def idled(self):
        with self._condition:
            return self._state == IDLE

    def set_idle(self, result):
        with self._condition:
            if self._state in {CANCELLED, CANCELLED_AND_NOTIFIED, FINISHED}:
                raise InvalidStateError("{}: {!r}".format(self._state, self))
            self._result = result
            self._state = IDLE
            for waiter in self._waiters:
                waiter.add_result(self)
            self._condition.notify_all()
        self._invoke_callbacks()

    def notify_all(self):
        with self._condition:
            for waiter in self._waiters:
                waiter.add_result(self)
            self._condition.notify_all()
        self._invoke_callbacks()

    def wait(self, timeout):
        with self._condition:
            if not self._condition.wait(timeout):
                raise TimeoutError()


class RuntimeTask:
    def __init__(self, task: ITask, manager: IRuntimeTaskManager):
        self.future = TaskFuture()
        self.runtime_time = 0
        self.manager = manager
        self.task = task

    def __del__(self):
        try:
            self.future.set_result(None)
        except InvalidStateError:
            pass

    def run(self):
        ct = threading.current_thread()
        self.manager
        ct.name = f"{self.manager.name}{str(self.task)}"

        if not self.future.idled:
            self.future.set_running_or_notify_cancel()

        st_time = time.monotonic()

        try:
            value = self.task.task()
        except Exception as exc:
            log.debug(f"myrrh task {ct.name} ended with exception: {exc}")

            endtime = time.monotonic() - st_time
            self.runtime_time += endtime

            try:
                self.future.set_exception(exc)
            except InvalidStateError:
                pass

            self = None

            ct.name = f"{ct.name}(exception)"

        else:
            endtime = time.monotonic() - st_time
            self.runtime_time += endtime

            with self.future:
                result = self.task.terminated()
                if result is not None:
                    self.future.set_result(result)
                    ct.name = f"{ct.name}(terminated)"
                else:
                    self.future.set_idle(value)
                    ct.name = f"{ct.name}(idle)"

            try:
                if self.future.idled():
                    try:
                        self.manager.submit(self)
                    except RuntimeError as exc:
                        log.debug(f"myrrh task {ct.name} can not leave idle state: {exc}")

                        self.future.set_exception(exc)

            except InvalidStateError:
                pass

    def join(self, timeout: float | None = None) -> typing.Any:
        return self.future.result(timeout)
