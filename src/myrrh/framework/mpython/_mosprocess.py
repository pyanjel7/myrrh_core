# -*- coding: utf-8 -*-

import sys
import threading
import warnings
import os
import signal

# from myrrh.utils import getch

from myrrh.core.services.system import MOsError, AbcRuntime, ImplPropertyClass

from . import mimportlib

# TODO
# from mlib.sh import ansi

__mlib__ = "AbcOsProcess"


class AbcOsProcess(AbcRuntime):
    __frameworkpath__ = "mpython._mosprocess"

    __all__ = [
        "SIGABRT",
        "SIGFPE",
        "SIGINT",
        "SIGILL",
        "SIGTERM",
        "SIGSEGV",
        "P_WAIT",
        "P_NOWAIT",
        "waitpid",
        "spawnv",
        "spawnve",
        "spawnl",
        "spawnle",
        "kill",
        "system",
        "pipe",
    ]

    SIGABRT = signal.SIGABRT
    SIGFPE = signal.SIGFPE
    SIGINT = signal.SIGINT
    SIGILL = signal.SIGILL
    SIGTERM = signal.SIGTERM
    SIGSEGV = signal.SIGSEGV

    P_WAIT = os.P_WAIT
    P_NOWAIT = os.P_NOWAIT
    P_INTERACT = -1

    WNOHANG = P_NOWAIT

    _POLL_READ_TIMEOUT = 0.01
    _POLL_EXIT_TIMEOUT = 0.1

    osfs = mimportlib.module_property("_mosfs")

    def _try_decode(self, out):
        try:
            if self.myrrh_os.defaultencoding():
                out = out.decode(self.myrrh_os.defaultencoding(), errors="ignore")
        except Exception:
            pass

        return out

    def _proc_stdin_listener(self, to_func, stop, chIt, emergency):
        raise NotImplementedError
        """
        getc = keymap(self, chIt)
        while not stop.is_set():
            try:
                c = next(getc)
                if c:
                    to_func(c.encode())
            except KeyboardInterrupt:
                emergency()
            except (StopIteration, BrokenPipeError):
                break
            except Exception as e:
                break
        """

    def _proc_stdout_listener(self, proc):
        out = b""
        err = b""
        cont = True

        while cont:
            try:
                out = proc.output(timeout=self._POLL_READ_TIMEOUT)
                if out is not None:
                    sys.stdout.write(self._try_decode(out))
            except Exception:
                out = None

            try:
                err = proc.error(timeout=self._POLL_READ_TIMEOUT)
                if err is not None:
                    sys.stderr.write(self._try_decode(err))
            except Exception:
                err = None

            cont = out is not None or err is not None or proc.exit_status is None

    def _spawnve(self, mode, path, args, env) -> int:
        raise NotImplementedError

        if mode not in [self.P_NOWAIT, self.P_WAIT, self.P_INTERACT]:
            raise ValueError("invalid mode")
        if not isinstance(args, (list, tuple)):
            raise ValueError("invalid type for arg")
        if args is None or len(args) == 0 or args[0] is None or len(args[0]) == 0:
            raise ValueError("spawn() arg 2 cannot be empty")

        path = self.osfs.myrrh_os.p(path)

        if len(args) > 0 and self.osfs.myrrh_os.p(args[0]) != path:
            warnings.warn("not implemented yet args0 redefinition : arg0 must be equal to path")

        stream = ""

        if mode is self.P_WAIT:
            stream += "r"
        if mode is self.P_INTERACT:
            stream += "w"

        handle = self.myrrh_syscall.openprocess(
            [path] + [self.myrrh_os.fsencode(a) for a in args[1:]],
            stream,
            env=None if env is None else {self.myrrh_os.fsencode(k): self.myrrh_os.fsencode(v) for k, v in env.items()},
        )

        th_out = threading.Thread(
            name="_spawnve_stdout_listener",
            target=self._proc_stdout_listener,
            args=(handle,),
        )
        th_out.daemon = True
        th_out.start()

        if mode is self.P_INTERACT:
            # chIt = getch.getchIt().__enter__()
            stopEvent = threading.Event()
            # th_in = threading.Thread(name="_spawnve_stdin_listener", target=self._proc_stdin_listener, args=(proc.input, stopEvent, chIt, handle.terminate))
            # th_in.daemon = True
            # th_in.start()

        if mode is self.P_WAIT or mode is self.P_INTERACT:
            try:
                _, exit_code = self.waitpid(int(handle))
                th_out.join()
                return exit_code >> 8
            except Exception:
                # try to clean
                try:
                    handle.signal(self.SIGTERM)
                except Exception:
                    pass

            finally:
                if mode is self.P_INTERACT:
                    stopEvent.set()
                    # chIt = getch.getchIt().__exit__()
                    # th_in.join()

        return handle.detach()

    def pipe(self):
        return self.myrrh_syscall.open_pipe()

    def waitpid(self, pid, options=None):
        exit_status = 0

        if pid in (0, -1):
            procs = self.myrrh_syscall.getallproc()
        else:
            procs = (self.myrrh_syscall.getproc(pid),)

        for p in procs:
            if options is not None:
                self.myrrh_os.shell.signal(p.pid, options)

            exit_status = self.myrrh_syscall.waitobj(p)

        if pid == -1:
            pid = 0

        return (pid, exit_status)

    def waitstatus_to_exitcode(self, status):
        if not isinstance(status, int):
            raise TypeError("an integer is required")
        return status >> 8

    def spawnv(self, mode, file, args):
        return self._spawnve(mode, file, args, env=None)

    def spawnve(self, mode, file, args, env):
        return self._spawnve(mode, file, args, env)

    def spawnl(self, mode, file, *args):
        return self._spawnve(mode, file, args, env=None)

    def spawnle(self, mode, file, *args):
        env = args[-1]
        return self._spawnve(mode, file, args[:-1], env)

    def kill(self, pid, sig):
        try:
            self.myrrh_os.shell.signal(pid, sig)

        except (OSError, IOError):
            raise
        except Exception as e:
            MOsError(self, strerror=str(e)).raised()

    class _wrap_close(metaclass=ImplPropertyClass):
        def __init__(self, stream, proc):
            self._stream = stream
            self._proc = proc

        def close(self):
            self._stream.close()
            returncode = self._proc.wait()
            if returncode == 0:
                return None
            if self.__rself__.cfg.system.os == "nt":
                return returncode
            else:
                return returncode << 8

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

        def __getattr__(self, name):
            return getattr(self._stream, name)

        def __iter__(self):
            return iter(self._stream)

    def system(self, command):
        shell = list(self.getdefaultshellb(command))

        rval = self._spawnve(self.P_INTERACT, shell[0], shell, env=None)
        return rval
