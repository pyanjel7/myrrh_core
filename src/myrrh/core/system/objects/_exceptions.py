import os
import errno as _errno

__all__ = (
    "MOsError",
    "MIOException",
    "UnexpectedException",
    "FileException",
    "ExecutionFailure",
    "ExecutionFailureCauseErr",
    "ExecutionFailureCauseRVal",
)


class MOsError(OSError):
    def __init__(self, system, errno=-1, strerror="", exc=None, error_translate=None, args=()):
        if strerror and error_translate is None and system:
            if hasattr(system, "error_translate"):
                error_translate = system.error_translate

        if exc is not None:
            errno = exc.errno if hasattr(exc, "errno") and exc.errno is not None else errno
            strerror = exc.strerror if hasattr(exc, "strerror") and exc.strerror is not None else "(%s)" % exc.__class__ + str(exc)
        elif strerror and errno == -1 and error_translate is not None:
            errno = error_translate(strerror)

        super().__init__(errno, strerror, *args)

        if errno is not None and strerror:
            self.strerror = os.strerror(errno) if errno >= 0 else ("undefined exception with %s" % (self.args,))

        self.system = system
        self.exc = exc
        self.args = args

    def raised(self):
        exc_class = OSError(self.errno, self.strerror).__class__
        if not issubclass(MOsError, exc_class):
            exc = type(exc_class.__name__, (exc_class, MOsError), dict())(self.errno, self.strerror, *self.args)
        else:
            exc = self

        __traceback__ = self.exc.__traceback__ if self.exc else None

        raise exc.with_traceback(__traceback__)


class MIOException(MOsError, IOError):
    def __init__(
        self,
        system,
        errno=-1,
        strerror="",
        exc=None,
        filename=None,
        error_translate=None,
    ):
        MOsError.__init__(
            self,
            system,
            errno,
            strerror,
            exc,
            args=(filename,),
            error_translate=error_translate,
        )
        if errno is not None and len(strerror) == 0:
            self.strerror = os.strerror(errno) if errno >= 0 else "undefined exception"

        self.system = system


class UnexpectedException(MOsError):
    def __init__(self, system, errno=0, strerror="unexpected exception"):
        super().__init__(errno, strerror)


class FileException(MOsError):
    def __init__(self, system, errno=0, filename=""):
        strerror = os.strerror(errno or _errno.ENOENT)

        if filename:
            filename = system.myrrh_os.fsdecode(filename)
            args = (str(filename),)

        super().__init__(system, errno=errno or _errno.ENOENT, strerror=strerror, args=args)


class ExecutionFailure(MOsError):
    def __init__(self, system, val, expected_val, msg, *args, errno=-1, error_translate=None):
        super().__init__(system, errno, strerror=msg, error_translate=error_translate, args=args)
        self.__val = val
        try:
            iter(expected_val)
            self.__expected_val = expected_val
        except TypeError:
            self.__expected_val = (expected_val,)

    def check(self):
        if self.__val not in self.__expected_val:
            self.raised()


class ExecutionFailureCauseErr(ExecutionFailure):
    def __init__(self, system, err, expected_err, *args, errno=-1):
        super().__init__(system, err, expected_err, err, *args, errno=errno)
        self.err = err
        self.expected_err = expected_err


class ExecutionFailureCauseRVal(ExecutionFailure):
    def __init__(self, system, err, rval, expected_rval, *args, errno=-1, error_translate=None):
        super().__init__(system, rval, expected_rval, err, *args, errno=errno, error_translate=error_translate)

        self.err = err
        self.rval = rval
        self.expected_rval = expected_rval
