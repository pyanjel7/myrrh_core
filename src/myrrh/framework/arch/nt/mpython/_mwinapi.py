import stat
import typing

from concurrent.futures import CancelledError

from myrrh.core.services import PID
from myrrh.core.services.system import AbcRuntime, Protocol
from myrrh.utils import mshlex


__mlib__ = "AbcWinAPI"


# copy of STARTUPINFO from python subprocess module
#
# Copyright (c) 2003-2005 by Peter Astrand <astrand@lysator.liu.se>
#
# Licensed to PSF under a Contributor Agreement.
class STARTUPINFO:
    def __init__(
        self,
        *,
        dwFlags=0,
        hStdInput=None,
        hStdOutput=None,
        hStdError=None,
        wShowWindow=0,
        lpAttributeList=None,
    ):
        self.dwFlags = dwFlags
        self.hStdInput = hStdInput
        self.hStdOutput = hStdOutput
        self.hStdError = hStdError
        self.wShowWindow = wShowWindow
        self.lpAttributeList = lpAttributeList or {"handle_list": []}

    def copy(self):
        attr_list = self.lpAttributeList.copy()
        if "handle_list" in attr_list:
            attr_list["handle_list"] = list(attr_list["handle_list"])

        return STARTUPINFO(
            dwFlags=self.dwFlags,
            hStdInput=self.hStdInput,
            hStdOutput=self.hStdOutput,
            hStdError=self.hStdError,
            wShowWindow=self.wShowWindow,
            lpAttributeList=attr_list,
        )


class AbcWinAPI(AbcRuntime):
    __frameworkpath__ = "mpython._mwinapi"

    ABOVE_NORMAL_PRIORITY_CLASS = 32768
    BELOW_NORMAL_PRIORITY_CLASS = 16384

    CREATE_BREAKAWAY_FROM_JOB = 16777216
    CREATE_DEFAULT_ERROR_MODE = 67108864
    CREATE_NO_WINDOW = 134217728
    CREATE_NEW_CONSOLE = 16
    CREATE_NEW_PROCESS_GROUP = 512
    DETACHED_PROCESS = 8
    DUPLICATE_CLOSE_SOURCE = 1
    DUPLICATE_SAME_ACCESS = 2
    ERROR_ALREADY_EXISTS = 183
    ERROR_BROKEN_PIPE = 109
    ERROR_IO_PENDING = 997
    ERROR_MORE_DATA = 234
    ERROR_NETNAME_DELETED = 64
    ERROR_NO_DATA = 232
    ERROR_NO_SYSTEM_RESOURCES = 1450
    ERROR_OPERATION_ABORTED = 995
    ERROR_PIPE_BUSY = 231
    ERROR_PIPE_CONNECTED = 535
    ERROR_SEM_TIMEOUT = 121

    FILE_FLAG_FIRST_PIPE_INSTANCE = 524288
    FILE_FLAG_OVERLAPPED = 1073741824
    FILE_GENERIC_READ = 1179785
    FILE_GENERIC_WRITE = 1179926
    FILE_MAP_ALL_ACCESS = 983071
    FILE_MAP_COPY = 1
    FILE_MAP_EXECUTE = 32
    FILE_MAP_READ = 4
    FILE_MAP_WRITE = 2
    FILE_TYPE_CHAR = 2
    FILE_TYPE_DISK = 1
    FILE_TYPE_PIPE = 3
    FILE_TYPE_REMOTE = 32768
    FILE_TYPE_UNKNOWN = 0

    GENERIC_READ = 2147483648
    GENERIC_WRITE = 1073741824
    HIGH_PRIORITY_CLASS = 128
    INFINITE = 4294967295
    INVALID_HANDLE_VALUE = 18446744073709551615
    IDLE_PRIORITY_CLASS = 64
    NORMAL_PRIORITY_CLASS = 32
    REALTIME_PRIORITY_CLASS = 256
    NMPWAIT_WAIT_FOREVER = 4294967295
    MEM_COMMIT = 4096
    MEM_FREE = 65536
    MEM_IMAGE = 16777216
    MEM_MAPPED = 262144
    MEM_PRIVATE = 131072
    MEM_RESERVE = 8192

    NULL = 0
    OPEN_EXISTING = 3

    PIPE_ACCESS_DUPLEX = 3
    PIPE_ACCESS_INBOUND = 1
    PIPE_READMODE_MESSAGE = 2
    PIPE_TYPE_MESSAGE = 4
    PIPE_UNLIMITED_INSTANCES = 255
    PIPE_WAIT = 0

    PAGE_EXECUTE = 16
    PAGE_EXECUTE_READ = 32
    PAGE_EXECUTE_READWRITE = 64
    PAGE_EXECUTE_WRITECOPY = 128
    PAGE_GUARD = 256
    PAGE_NOACCESS = 1
    PAGE_NOCACHE = 512
    PAGE_READONLY = 2
    PAGE_READWRITE = 4
    PAGE_WRITECOMBINE = 1024
    PAGE_WRITECOPY = 8

    PROCESS_ALL_ACCESS = 2097151
    PROCESS_DUP_HANDLE = 64

    SEC_COMMIT = 134217728
    SEC_IMAGE = 16777216
    SEC_LARGE_PAGES = 2147483648
    SEC_NOCACHE = 268435456
    SEC_RESERVE = 67108864
    SEC_WRITECOMBINE = 1073741824
    STARTF_USESHOWWINDOW = 1
    STARTF_USESTDHANDLES = 256
    STD_ERROR_HANDLE = 4294967284
    STD_INPUT_HANDLE = 4294967286
    STD_OUTPUT_HANDLE = 4294967285
    STILL_ACTIVE = 259
    SW_HIDE = 0
    SYNCHRONIZE = 1048576
    WAIT_ABANDONED_0 = 128
    WAIT_OBJECT_0 = 0
    WAIT_TIMEOUT = 258

    class Overlapped:
        event: int

        def GetOverlappedResult(self, __wait: bool) -> tuple[int, int]:
            raise NotImplementedError

        def cancel(self) -> None:
            raise NotImplementedError

        def getbuffer(self) -> bytes | None:
            raise NotImplementedError

    def CloseHandle(self, handle: int) -> None:
        if handle != 0:
            self.myrrh_syscall.gethandle(handle).close()

    def CreateFile(
        self,
        __file_name: str,
        __desired_access: int,
        __share_mode: int,
        __security_attributes: int,
        __creation_disposition: int,
        __flags_and_attributes: int,
        __template_file: int,
    ) -> int:
        extras = {
            "desired_access": __desired_access,
            "share_mode": __share_mode,
            "security_attributes": __security_attributes,
            "creation_disposition": __creation_disposition,
            "flags_and_attributes": __flags_and_attributes,
            "template_file": __template_file,
        }

        wiring = self.myrrh_syscall.Wiring.OFF
        if __desired_access & self.GENERIC_READ:
            wiring |= self.myrrh_syscall.Wiring.IN
        if __desired_access & self.GENERIC_WRITE:
            wiring |= self.myrrh_syscall.Wiring.OUT

        return self.myrrh_syscall.open_file(
            self.myrrh_os.fsencode(__file_name),
            wiring,
            extras=extras,
            protocol=Protocol.WINAPI,
        )

    def ConnectNamedPipe(self, handle: int, overlapped=True):
        raise NotImplementedError

    def CreateNamedPipe(
        self,
        __name: str,
        __open_mode: int,
        __pipe_mode: int,
        __max_instances: int,
        __out_buffer_size: int,
        __in_buffer_size: int,
        __default_timeout: int,
        __security_attributes: int,
    ) -> int:
        raise NotImplementedError

    def CreatePipe(self, __pipe_attrs: typing.Any, __size: int) -> tuple[int, int]:
        rd, wr = self.myrrh_syscall.open_pipe()

        return rd, wr

    def CreateJunction(self, __src_path: str, __dst_path: str) -> None:
        raise NotImplementedError

    def CreateProcess(
        self,
        __application_name: str | None,
        __command_line: str | None,
        __proc_attrs: typing.Any,
        __thread_attrs: typing.Any,
        __inherit_handles: bool,
        __creation_flags: int,
        __env_mapping: dict[
            str,
            str,
        ],
        __current_directory: str | None,
        __startup_info: STARTUPINFO,
    ) -> tuple[int, int, int, int]:
        args = mshlex.split(__command_line, False)
        if __application_name is None:
            __application_name = args[0]

        path = self.myrrh_os.p(__application_name)
        args = [self.myrrh_os.fsencode(arg) for arg in args]
        working_dir = self.myrrh_os.p(__current_directory) if __current_directory else None
        env = {self.myrrh_os.fsencode(k): self.myrrh_os.fsencode(v) for k, v in __env_mapping.items()} if __env_mapping else None

        stdin = __startup_info.hStdInput
        stdout = __startup_info.hStdOutput
        stderr = __startup_info.hStdError

        hproc = self.myrrh_syscall.open_process(
            path,
            args,
            working_dir,
            env,
            stdin,
            stdout,
            stderr,
            extras={
                "creation_flags": __creation_flags,
                "inherit_handles": __inherit_handles,
                "startup_info.flags": __startup_info.dwFlags,
                "startup_info.show_windows": __startup_info.wShowWindow,
            },
            protocol=Protocol.WINAPI,
        )

        handle = self.myrrh_syscall.gethandle(hproc, True)

        pid = handle.pid

        return hproc, 0, pid, 0

    def DuplicateHandle(
        self,
        __source_process_handle: int,
        __source_handle: int,
        __target_process_handle: int,
        __desired_access: int,
        __inherit_handle: bool,
        __options: int = 0,
    ) -> int:
        return self.myrrh_syscall.dup(__source_handle)

    def ExitProcess(self, __ExitCode: int) -> None:
        raise NotImplementedError

    def GetACP(self) -> int:
        raise NotImplementedError

    def GetFileType(self, handle: int) -> int:
        handle = self.myrrh_syscall.gethandle(handle, True)
        mode = handle.stat().st_mode
        if stat.S_ISFIFO(mode):
            return self.FILE_TYPE_CHAR
        if stat.S_ISREG(mode) or stat.S_ISDIR(mode) or stat.S_ISLNK(mode):
            return self.FILE_TYPE_DISK
        if stat.S_ISCHR(mode):
            return self.FILE_TYPE_CHAR

        return self.FILE_TYPE_UNKNOWN

    def GetCurrentProcess(self) -> int:
        return PID

    def GetExitCodeProcess(self, __process: int) -> int:
        handle = self.myrrh_syscall.gethandle(__process, True)
        return handle.exit_status

    def GetLastError(self) -> int:
        raise NotImplementedError

    def GetModuleFileName(self, __module_handle: int) -> str:
        raise NotImplementedError

    def GetStdHandle(self, __std_handle: int) -> int:
        match __std_handle:
            case self.STD_INPUT_HANDLE:
                return self.myrrh_syscall.hin
            case self.STD_OUTPUT_HANDLE:
                return self.myrrh_syscall.hout
            case self.STD_ERROR_HANDLE:
                return self.myrrh_syscall.herr

        raise ValueError(f"Invalid std handle value: {__std_handle}")

    def GetVersion(self) -> int:
        raise NotImplementedError

    def OpenProcess(self, __desired_access: int, __inherit_handle: bool, __process_id: int) -> int:
        raise NotImplementedError

    def PeekNamedPipe(self, __handle: int, __size: int = ...) -> tuple[int, int] | tuple[bytes, int, int]:
        raise NotImplementedError

    def SetNamedPipeHandleState(
        self,
        __named_pipe: int,
        __mode: int | None,
        __max_collection_count: int | None,
        __collect_data_timeout: int | None,
    ) -> None:
        raise NotImplementedError

    def TerminateProcess(self, __handle: int, __exit_code: int) -> None:
        handle = self.myrrh_syscall.gethandle(__handle, True)
        handle.terminate(extras={"exit_code": __exit_code})

    def WaitForMultipleObjects(
        self,
        __handle_seq: typing.Sequence[int],
        __wait_flag: bool,
        __milliseconds: int = ...,
    ) -> int:
        raise NotImplementedError

    def WaitForSingleObject(self, __handle: int, __milliseconds: int) -> int:
        try:
            timeout = None if __milliseconds == self.INFINITE else __milliseconds / 1000
            self.myrrh_syscall.wait(__handle, timeout)

            return self.WAIT_OBJECT_0
        except TimeoutError:
            return self.WAIT_TIMEOUT
        except CancelledError:
            return self.WAIT_ABANDONED_0
        except Exception:
            raise

    def WaitNamedPipe(self, __name: str, __timeout: int) -> None:
        raise NotImplementedError

    def ReadFile(self, handle: int, size: int, overlapped=False) -> tuple[bytes, int]:
        return (
            self.myrrh_syscall.gethandle(handle).read(size, extras={"overlapped": overlapped}),
            0,
        )

    def WriteFile(self, handle: int, buffer: bytes, overlapped=False) -> tuple[int, int]:
        return (
            self.myrrh_syscall.gethandle(handle).write(buffer, extras={"overlapped": overlapped}),
            0,
        )
