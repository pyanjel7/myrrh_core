import typing

from myrrh.core.interfaces import abstractmethod, ABC
from myrrh.core.services.system import AbcRuntimeDelegate

from myrrh.framework.mpython import mbuiltins

__mlib__ = "AbcSupport"


class _interface(ABC):
    import test.support as local_support

    catch_unraisable_exception = local_support.catch_unraisable_exception

    @abstractmethod
    def findfile(self, filename, subdir=None) -> str:
        ...

    @abstractmethod
    def requires(self, resource, msg=None) -> None:
        ...

    @abstractmethod
    def gc_collect(self) -> None:
        ...

    @abstractmethod
    def detect_api_mismatch(self, ref_api, other_api, *, ignore=()) -> set[str]:
        ...

    @abstractmethod
    def cpython_only(self, test) -> typing.Any:
        ...

    @abstractmethod
    def swap_attr(self, obj, attr, new_val) -> typing.ContextManager[typing.Any | None]:
        ...

    @abstractmethod
    def no_tracing(self, func) -> typing.Callable:
        ...

    @abstractmethod
    def is_resource_enabled(self, resource) -> bool:
        ...

    @abstractmethod
    def requires_resource(self, resource) -> typing.Any:
        ...

    @abstractmethod
    def requires_fork(self) -> typing.Any:
        ...

    @abstractmethod
    def bigmemtest(self, size, memuse, dry_run=True) -> typing.Callable:
        ...

    @abstractmethod
    def requires_gzip(self, size, memuse, dry_run=True) -> typing.Callable:
        ...

    @abstractmethod
    def requires_zlib(self, size, memuse, dry_run=True) -> typing.Callable:
        ...

    @abstractmethod
    def requires_bz2(self, size, memuse, dry_run=True) -> typing.Callable:
        ...

    @abstractmethod
    def requires_lzma(self, size, memuse, dry_run=True) -> typing.Callable:
        ...

    @abstractmethod
    def requires_subprocess(self) -> typing.Callable:
        ...

    @abstractmethod
    def _force_run(self, path, func, *args) -> typing.Callable:
        ...

    @abstractmethod
    def skip_if_pgo_task(self) -> typing.Callable:
        ...

    @abstractmethod
    def refcount_test(self) -> typing.Callable:
        ...

    @abstractmethod
    def reap_children(self) -> typing.Callable:
        ...

    @abstractmethod
    def get_attribute(self, obj, name) -> typing.Any:
        ...

    @abstractmethod
    def captured_stdout(self) -> typing.Any:
        ...

    @abstractmethod
    def check__all__(self, test_case, module, name_of_module=None, extra=(), not_exported=()) -> typing.Any:
        ...

    @abstractmethod
    def check_impl_detail(self, **guards) -> bool:
        ...

    @abstractmethod
    def check_sanitizer(self, *, address=False, memory=False, ub=False) -> bool:
        ...

    @abstractmethod
    def requires_mac_ver(self, *min_version) -> typing.Callable:
        ...

    @abstractmethod
    def captured_stderr(self) -> typing.Any:
        ...

    @property
    @abstractmethod
    def PGO(self) -> bool:
        ...

    @property
    @abstractmethod
    def has_subprocess_support(self) -> bool:
        ...

    @property
    @abstractmethod
    def _4G(self):
        return self.local_support._4G

    @property
    @abstractmethod
    def PIPE_MAX_SIZE(self):
        return self.local_support.PIPE_MAX_SIZE

    @property
    @abstractmethod
    def use_resources(self) -> list | None:
        ...

    @property
    @abstractmethod
    def real_max_memuse(self) -> int:
        ...

    @property
    @abstractmethod
    def verbose(self) -> local_support.verbose:
        ...

    @property
    @abstractmethod
    def is_emscripten(self) -> bool:
        ...

    @property
    @abstractmethod
    def is_android(self) -> bool:
        ...

    @property
    @abstractmethod
    def is_wasi(self) -> bool:
        ...


class AbcSupport(_interface, AbcRuntimeDelegate):
    __frameworkpath__ = "mpython.mtest.msupport"

    __all__ = [
        # globals
        "PIPE_MAX_SIZE",
        "verbose",
        "max_memuse",
        "use_resources",
        "failfast",
        # exceptions
        "Error",
        "TestFailed",
        "TestDidNotRun",
        "ResourceDenied",
        # io
        "record_original_stdout",
        "get_original_stdout",
        "captured_stdout",
        "captured_stdin",
        "captured_stderr",
        # unittest
        "is_resource_enabled",
        "requires",
        "requires_freebsd_version",
        "requires_linux_version",
        "requires_mac_ver",
        "check_syntax_error",
        "BasicTestRunner",
        "run_unittest",
        "run_doctest",
        "requires_gzip",
        "requires_bz2",
        "requires_lzma",
        "bigmemtest",
        "bigaddrspacetest",
        "cpython_only",
        "get_attribute",
        "requires_IEEE_754",
        "requires_zlib",
        "has_fork_support",
        "requires_fork",
        "has_subprocess_support",
        "requires_subprocess",
        "has_socket_support",
        "requires_working_socket",
        "anticipate_failure",
        "load_package_tests",
        "detect_api_mismatch",
        "check__all__",
        "skip_if_buggy_ucrt_strfptime",
        "check_disallow_instantiation",
        "check_sanitizer",
        "skip_if_sanitizer",
        # sys
        "is_jython",
        "is_android",
        "is_emscripten",
        "is_wasi",
        "check_impl_detail",
        "unix_shell",
        "setswitchinterval",
        # network
        "open_urlresource",
        # processes
        "reap_children",
        # miscellaneous
        "run_with_locale",
        "swap_item",
        "findfile",
        "infinite_recursion",
        "swap_attr",
        "Matcher",
        "set_memlimit",
        "SuppressCrashReport",
        "sortdict",
        "run_with_tz",
        "PGO",
        "missing_compiler_executable",
        "ALWAYS_EQ",
        "NEVER_EQ",
        "LARGEST",
        "SMALLEST",
        "LOOPBACK_TIMEOUT",
        "INTERNET_TIMEOUT",
        "SHORT_TIMEOUT",
        "LONG_TIMEOUT",
    ]

    __doc__ = _interface.local_support.__doc__

    __delegated__ = {_interface: _interface.local_support}
    __delegate_check_type__ = False

    def __init__(self, *a, **kwa):
        mod = mbuiltins.wrap_module(self.local_support, self)

        self.__delegate__(_interface, mod)

    def local_findfile(self, filename, subdir=None):
        import os
        import sys
        import test.support

        TEST_SUPPORT_DIR = os.path.dirname(os.path.abspath(test.support.__file__))
        TEST_HOME_DIR = os.path.dirname(TEST_SUPPORT_DIR)

        if os.path.isabs(filename):
            return filename

        if subdir is not None:
            filename = os.path.join(subdir, filename)
        path = [TEST_HOME_DIR] + sys.path
        for dn in path:
            fn = os.path.join(dn, filename)
            if os.path.exists(fn):
                return fn

        return filename

    def findfile(self, filename, subdir=None):
        _cast_ = self.myrrh_os.fscast(filename)
        local_filename = self.local_findfile(filename, subdir)
        try:
            with open(local_filename) as f:
                self.myrrh_syscall.stream_out(self.myrrh_os.fsencode(filename), f.buffer)
        except FileNotFoundError:
            pass

        return _cast_(self.myrrh_os.getpathb(filename))
