# -*- coding: utf-8 -*-

"""
**Advanced shell**

This module provides advanced shell operations such as polling and predefined runner.

.. seealso:: :class:`myrrh.core.service.IShellService`
"""
import statistics
import threading
import weakref

from myrrh.utils import mtimer, mshlex

from myrrh.core.interfaces import IInStream, IProcess
from myrrh.core.services.system import AbcRuntime, InheritedPropertyClass
from myrrh.utils import mstring

__mlib__ = "AbcAdvSh"

_FAKE_PROC_START_PID = 90000
_fake_proc_count = 0


def _fakepid():
    global _fake_proc_count
    _fake_proc_count += 1
    return _fake_proc_count + _FAKE_PROC_START_PID


class AbcAdvSh(AbcRuntime):
    __frameworkpath__ = "msh.advsh"

    class _AdvShellExpired(Exception):
        def __init__(self, cmd, timeout, output=None, stderr=None):
            self.cmd = cmd
            self.timeout = timeout
            self.output = output
            self.stderr = stderr

        def __repr__(self):
            return "Command '%s' timed out after %s seconds and %s execution%s" % (
                self.cmd,
                self.timeout,
                self.cmd.ncalls,
                not self.cmd.ncalls and "" or "s",
            )

    class TTLExpired(_AdvShellExpired):
        pass

    class TimeoutExpired(_AdvShellExpired):
        pass

    class Abort(Exception):
        pass

    class AbortAndContinue(Abort):
        pass

    class execute(metaclass=InheritedPropertyClass(list)):  # type: ignore[misc]
        def __init__(
            self,
            cmd,
            *,
            path=None,
            encoding=None,
            errors=None,
            count=None,
            during=None,
            interval=None,
            ttl=None,
            timeout=None,
            poll=None,
            raiseonttl=None,
            raiseontimeout=True,
        ):
            self._cmd = cmd
            if isinstance(cmd, (str, bytes)):
                if path:
                    raise ValueError("bytes or string is not supported for cmd when path parameter is set")

                self._cast = encoding and mstring.cast(cmd, encoding=encoding, errors=errors) or self.myrrh_os.shcast(cmd)
                self._args = encoding and mstring.typebytes(encoding, errors)(cmd) or self.myrrh_os.shencode(cmd)
            else:
                if not path:
                    raise ValueError("only bytes or string is supported for cmd when path parameter is not set")
                self._cast = encoding and mstring.cast(cmd, encoding=encoding, errors=errors) or self.myrrh_os.fscast(cmd[0])
                self._args = [(encoding and mstring.typebytes(encoding, errors)(a) or self.myrrh_os.fsencode(a)) for a in cmd]

            self.__poll = poll
            self.__ttl = ttl
            self.__raiseonttl = raiseonttl
            self.__raiseontimeout = raiseontimeout

            eval_count = (not during and 1 or None) if count is None else count

            self.__duration_timer = mtimer.MTimer(timeout=during, step=during and interval or None, raise_on_expired=True)

            self.__global_timer = mtimer.MTimer(
                timeout=timeout,
                count=eval_count,
                step=not during and interval or None,
                raise_on_expired=True,
            )

            self.__ttl_timer = mtimer.MTimer(timeout=ttl, raise_on_expired=True)

            # evaluate cmd
            _, timeout = self._timeout
            self.__oneexecution = (not count and not timeout and not during) or (not poll and not count and eval_count == 1)

            if path:
                self._path = encoding and mstring.typebytes(path, encoding=encoding, errors=errors) or self.myrrh_os.fsencode(path)
            else:
                self._path = None

            if not self._path and timeout is not None:
                args = self.myrrh_os.getdefaultshellb(self._args)
                self._path = args[0]
                self._args = args
            elif path:
                self._args = mshlex.list2cmdlineb(self._args)

            if self.__oneexecution:
                self.values()

        @property
        def _timeout(self):
            # if timeout define and ttl define
            timeout = self.__poll
            timeout_cause = "polling"

            if self.__ttl_timer.timeout is not None:
                timeout = self.__ttl_timer.timeout if timeout is None else min(timeout, self.__ttl_timer.timeleft)
                timeout_cause = timeout_cause if (timeout is None or timeout < self.__ttl_timer.timeleft) else "killed"

            if self.__global_timer.timeout is not None:
                timeout = timeout is not None and min(timeout, self.__global_timer.timeleft) or self.__global_timer.timeleft
                timeout_cause = timeout_cause if (timeout is None or timeout < self.__global_timer.timeleft) else "timeout"

            return timeout_cause, timeout

        def __repr__(self):
            cmd = self._cast(self._path + b" ") or self._cast(b"")
            cmd += self._cast(b" ".join(self._args) if isinstance(self._args, (list, tuple)) else self._args)

            if self.__oneexecution:
                return "<%s> %s" % (cmd, self[0].state)
            return "<%s>*%d in %ds" % (cmd, len(self), self.time)

        def _run(self):
            with self.__global_timer:
                _, timeout = self._timeout

                while True:
                    if not self._path and timeout is None:
                        proc = _AdvshellFakeProc(self, self._args)
                    else:
                        proc = _AdvshellProc(self, self._args, self._path)

                    try:
                        with self.__ttl_timer:
                            try:
                                with _ExecutionInformation(proc=proc, cast=self._cast) as exe:
                                    proc.exec()

                                    self.append(exe)
                                    cause = "polling"
                                    while cause == "polling":
                                        cause, timeout = self._timeout

                                        try:
                                            exe.communicate(timeout=timeout)
                                            cause = "exited"

                                        except mtimer.MTimer.DelayExpired:
                                            if cause == "polling":
                                                yield self[-1]

                                        except Exception:
                                            cause = "exception"

                                yield self[-1]

                                if cause == "killed" and self.__raiseonttl:
                                    raise AdvSh.TTLExpired(
                                        cmd=self,
                                        timeout=self.__ttl,
                                        output=exe.out,
                                        stderr=exe.err,
                                    ) from None

                                self.__duration_timer.idle
                                self.__global_timer.idle

                            except GeneratorExit:
                                if exe.state != "closed":
                                    exe.state = "aborted"
                                break
                            except mtimer.MTimer.CountExpired:
                                break
                            except mtimer.MTimer.DelayExpired as e:
                                if self.__raiseontimeout and not e.timer == self.__duration_timer:
                                    raise AdvSh.TimeoutExpired(
                                        cmd=self,
                                        timeout=self.__global_timer.duration,
                                        output=exe.out,
                                        stderr=exe.err,
                                    ) from None
                                break

                    finally:
                        proc.close()

        def __iter__(self):
            # execution ended
            if self.__global_timer.endtime:
                for exe in self.calls:
                    if self.__oneexecution:
                        yield from exe
                    else:
                        yield exe
            else:
                for exe in self._run():
                    yield exe

        def values(self):
            if not self.__global_timer.endtime:
                for _ in self:
                    pass
            return self

        def iter(self):
            yield self.__iter__()

        def itervalues(self):
            for exe in self.calls:
                yield exe

        # general execution information
        @property
        def cmd(self):
            return self._cast(self._cmd)

        @property
        def ncalls(self):
            return len(self)

        @property
        def calls(self):
            return list.__iter__(self)  # 3.5 fixes

        @property
        def time(self):
            return self.__global_timer.duration

        @property
        def mtime(self):
            try:
                return statistics.mean(map(lambda x: x.time, self.calls))
            except statistics.StatisticsError:
                return 0

        @property
        def vtime(self):
            try:
                return statistics.variance(map(lambda x: x.time, self.calls))
            except statistics.StatisticsError:
                return None


class _AdvshellFakeProc:
    def __init__(self, system: AbcAdvSh, cmd: bytes):
        self.system = weakref.proxy(system)
        self.cmd = cmd
        self._pid = None
        self.closed = False

    def exec(self):
        if self._pid is not None:
            return

        o, e, r = self.system.myrrh_os.shell.execute(self.cmd)
        self._out = o
        self._err = e
        self._rval = r

        self._pid = _fakepid()
        self.closed = True

    def error(self, nbytes=None, timeout=None):
        nbytes = len(self._err) if nbytes is None else min(len(self._err), nbytes)
        res = self._err[:nbytes]
        self._err = self._err[nbytes:]
        return res or None

    def output(self, nbytes=None, timeout=None):
        nbytes = len(self._out) if nbytes is None else min(len(self._out), nbytes)
        res = self._out[:nbytes]
        self._out = self._out[nbytes:]
        return res or None

    @property
    def exit_status(self):
        return self._rval

    @property
    def is_running(self):
        return False

    def terminate(self):
        pass

    @property
    def pid(self):
        return self._pid

    def close(self):
        pass


class _AdvshellProc:
    def __init__(self, system: AbcAdvSh, args: list[bytes], path: bytes):
        self.system = weakref.proxy(system)
        self.args = args
        self.path = path
        self._pid = None
        self.closed = False

    def exec(self):
        if self._pid is not None:
            return

        outr = outw = errr = errw = None
        self._out = self._err = None

        try:
            outr, outw = self.system.myrrh_syscall.open_pipe()
            errr, errw = self.system.myrrh_syscall.open_pipe()

            hproc = self.system.myrrh_syscall.open_process(self.path, self.args, stdout=outw, stderr=errw)

        except:  # noqa: E722
            if outw is not None:
                self.system.myrrh_syscall.close(outr)  # type: ignore[arg-type]
            if errw is not None:
                self.system.myrrh_syscall.close(errr)  # type: ignore[arg-type]
            raise

        finally:
            if outw is not None:
                self.system.myrrh_syscall.close(outw)
            if errw is not None:
                self.system.myrrh_syscall.close(errw)

        self._proc: IProcess = self.system.myrrh_syscall.gethandle(hproc)  # type: ignore
        self._out: IInStream = self.system.myrrh_syscall.gethandle(outr)  # type: ignore
        self._err: IInStream = self.system.myrrh_syscall.gethandle(errr)  # type: ignore

        self._exit_status = None
        self._pid = self._proc.pid

    def error(self, nbytes=None, timeout=None):
        if self._err is None:
            return b""

        if not self.closed and self._err:
            return self._err.read(nbytes, extras={"timeout": timeout})

        raise BrokenPipeError("operation on closed process is not available")

    def output(self, nbytes=None, timeout=None):
        if self._out is None:
            return b""

        if not self.closed:
            return self._out.read(nbytes, extras={"timeout": timeout})

        raise BrokenPipeError("operation on closed process is not available")

    def close(self):
        if not self.closed and self._pid:
            self._proc.close()
            self._out.close()
            self._err.close()
        self.closed = True

    @property
    def exit_status(self):
        if self._exit_status is None and self.closed:
            raise RuntimeError(f"the return value of the process {self._pid} is lost")

        if self._exit_status is None:
            self._exit_status = self._proc.exit_status

        return self._exit_status

    @property
    def is_running(self):
        return self.exit_status is None

    def terminate(self):
        if not self.closed and self._pid:
            self._proc.terminate()
            self._exit_status = self.system.myrrh_syscall.wait(self._proc)

    @property
    def pid(self):
        return self._pid


class _ExecutionInformation:
    MAX_BUFFER_SIZE = 50000

    def __init__(self, proc, cast, **kwargs):
        self._proc = proc
        self._cast = cast
        self._timer = mtimer.MTimer()
        self._state = None

        self._buflock = threading.RLock()
        self._out = bytearray(self.MAX_BUFFER_SIZE)
        self._err = bytearray(self.MAX_BUFFER_SIZE)

        self._closed = False

        for k, v in kwargs:
            setattr(self, k, v)

    def __iter__(self):
        yield from (self.out, self.err, self.rval)

    def __del__(self):
        if not self._closed:
            self._proc.terminate()

    def __getitem__(self, item):
        if hasattr(self, item):
            return getattr(self, item)
        raise KeyError(item)

    def __enter__(self):
        self._timer.reset()
        return self

    def __exit__(self, *_a, **_k):
        self.close()
        self._timer.stop()

    def communicate(self, timeout=None):
        # wait en of proc
        com_timer = mtimer.MBurstTimer(timeout=timeout, raise_on_expired=True)
        self._out.clear()
        self._err.clear()

        while True:
            if self._proc.exit_status is not None:
                break

            try:
                self._out.extend(self._proc.output(timeout=com_timer.timeleft) or b"")
            except TimeoutError:
                ...

            try:
                self._err.extend(self._proc.error(timeout=com_timer.timeleft) or b"")
            except TimeoutError:
                ...
            com_timer.idle

    def close(self):
        if not self._closed:
            self.proc.terminate()
            self._out.extend(self._proc.output() or b"")
            self._err.extend(self._proc.error() or b"")
            self.proc.close()
            self._closed = True

    @property
    def closed(self):
        return self._closed

    @property
    def proc(self):
        return self._proc

    @property
    def time(self):
        return self._timer.duration

    @property
    def starttime(self):
        return self._timer.starttime

    @property
    def endtime(self):
        return self._timer.endtime

    @property
    def state(self):
        state, _, _ = self._state or (None, None, None)
        if self._proc.exit_status is None:
            return "-".join(filter(None, ["running", state]))

        return "-".join(filter(None, ["terminated", state]))

    @state.setter
    def state(self, state):
        self._state = (
            state,
            self._out and len(self._out) or 0,
            self._err and len(self._err) or 0,
        )

    @property
    def out(self):
        return self._cast(self._out)

    @property
    def err(self):
        return self._cast(self._err)

    @property
    def rval(self):
        return self._proc.exit_status


AdvSh = AbcAdvSh

Abort = AdvSh.Abort
AbortAndContinue = AdvSh.AbortAndContinue
TimeoutExpired = AdvSh.TimeoutExpired
TTLExpired = AdvSh.TTLExpired
