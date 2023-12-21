import errno
import os
import subprocess
import typing
import signal
import shutil


from myrrh.utils import mshlex
from myrrh.provider import (
    Wiring,
    Protocol,
    Whence,
    Stat,
    IShellService,
    IFileSystemService,
    IStreamService,
    StatField,
)

from myrrh.utils.mhandle import LightHandler

from myrrh.core.services import cfg_init


def _working_dir(cwd):
    cwd = os.fsdecode(cwd) if isinstance(cwd, bytes) else cwd
    return None if cwd is None else os.path.expanduser("~") if len(cwd) == 0 else os.path.join(os.path.expanduser("~"), cwd) if cwd in [os.path.curdir, os.path.pardir] else cwd


_shell = None
_shellargs: tuple[str] | None = None

if os.name == "nt":
    _shell = os.environ.get("COMSPEC", "cmd.exe")
    _shell = shutil.which(_shell)
    _shellarg = "/c"

if os.name == "posix":
    _shell = shutil.which("sh")
    _shellarg = "-c"

_default_shell_encoding = "utf8"

OSErrorEBADF = OSError(errno.EBADF, os.strerror(errno.EBADF))


class Shell(IShellService):
    protocol = Protocol.MYRRH

    def execute(
        self,
        command,
        working_dir=None,
        env=None,
        *,
        extras: dict[str, typing.Any] | None = None,
    ):
        working_dir = _working_dir(working_dir)
        if isinstance(command, list):
            command = b" ".join(command)

        command = os.fsdecode(command)
        env = env if env is None else {os.fsdecode(k): os.fsdecode(v) for k, v in env.items()}

        with subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            shell=True,
            cwd=working_dir,
            env=env,
            text=False,
        ) as process:
            out, err = process.communicate()
            return out, err, process.returncode

    def spawn(
        self,
        command,
        working_dir=None,
        env=None,
        *,
        extras: dict[str, typing.Any] | None = None,
    ):
        working_dir = _working_dir(working_dir)

        command = list(map(os.fsdecode, command))

        env = env if env is None else {os.fsdecode(k): os.fsdecode(v) for k, v in env.items()}

        proc = subprocess.Popen(command, cwd=working_dir, env=env)

        if proc is None:
            raise Exception("can't execute command %s" % command)

        return proc.pid

    def signal(self, proc_id, sig=signal.SIGTERM):
        os.kill(proc_id, sig)


class FileSystem(IFileSystemService):
    """
    Service handle all file system function
    """

    protocol = Protocol.MYRRH

    def exist(self, file_path, *, extras: dict[str, typing.Any] | None = None):
        return os.path.exists(file_path)

    def rm(self, file_path, *, extras: dict[str, typing.Any] | None = None):
        os.remove(file_path)

    def mkdir(self, path, *, extras: dict[str, typing.Any] | None = None):
        if os.path.isdir(path):
            return
        os.makedirs(path)

    def rmdir(self, path, *, extras: dict[str, typing.Any] | None = None):
        os.rmdir(path)

    def is_container(self, path, *, extras: dict[str, typing.Any] | None = None):
        return os.path.isdir(path)

    def list(self, path: bytes, *, extras: dict[str, typing.Any] | None = None):
        raise NotImplementedError

    def stat(self, path: bytes, *, extras: dict | None = None) -> dict:
        stat = os.stat(path)
        return {
            "st_mode": stat.st_mode,
            "st_ino": stat.st_ino,
            "st_dev": stat.st_dev,
            "st_nlink": stat.st_nlink,
            "st_uid": stat.st_uid,
            "st_gid": stat.st_gid,
            "st_size": stat.st_size,
            "st_atime": stat.st_atime,
            "st_mtime": stat.st_mtime,
            "st_ctime": stat.st_ctime,
        }


try:
    import _winapi as winapi
    import msvcrt
except ImportError:
    winapi = False  # type: ignore[assignment]


class StreamPosix(IStreamService):
    protocol = Protocol.POSIX
    chunk_sz = cfg_init("rd_chunk_size", 2048, section="mplugins.provider.local")

    handler = LightHandler()

    def open_file(self, path: bytes, wiring: int, *, extras: dict | None = None) -> tuple[bytes, int]:
        try:
            flags = 0
            mode = 511

            wiring_ = Wiring(wiring)

            if wiring_ & Wiring.INOUT:
                flags |= os.O_RDWR
                if not wiring_ & Wiring.RESET:
                    flags |= os.O_APPEND
            elif wiring_ & Wiring.IN:
                flags |= os.O_RDONLY
            elif wiring_ & Wiring.OUT:
                flags |= os.O_WRONLY
                if not wiring_ & Wiring.RESET:
                    flags |= os.O_APPEND

            if wiring_ & Wiring.CREATE:
                flags |= os.O_CREAT

            if hasattr(os, "O_BINARY"):
                flags |= os.O_BINARY

            if extras:
                flags = extras.get("flags", wiring)
                mode = extras["mode"]

            fd = os.open(os.fsdecode(path), flags, mode)
            handle = self.handler.new(path, fd, None)

            return path, handle

        except KeyError as e:
            raise TypeError(f"open() missing required argument {e}") from None

    def open_process(
        self,
        path: bytes,
        wiring: int,
        args: list[bytes],
        working_dir: bytes | None = None,
        env: dict[bytes, bytes] | None = None,
        *,
        extras: dict | None = None,
    ) -> tuple[bytes, int, int, int, int]:
        import subprocess

        stdin = stdout = stderr = None
        process_group = gid = gids = uid = None
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if winapi else 0  # type: ignore[attr-defined]
        umask = -1
        wiring = Wiring(wiring)

        if wiring & Wiring.IN:
            stdin = subprocess.PIPE
        if wiring & Wiring.OUT:
            stdout = subprocess.PIPE
        if wiring & Wiring.ERR:
            stderr = subprocess.PIPE

        if extras:
            process_group = extras.get("process_group")
            gid = extras.get("gid")
            gids = extras.get("gids")
            uid = extras.get("uid")
            umask = extras.get("umask") or umask
            creationflags = extras.get("creationflags") or creationflags

        env_: dict[str, str] | None = env and {os.fsencode(k): os.fsencode(v) for k, v in env.items()}  # type: ignore[assignment]

        proc = subprocess.Popen(executable=path, args=args, cwd=working_dir, env=env_, stdin=stdin, stdout=stdout, stderr=stderr, creationflags=creationflags, process_group=process_group, group=gid, extra_groups=gids, user=uid, umask=umask, close_fds=False)  # type: ignore[misc]

        if proc.stdin:
            hin = self.handler.new(path, proc.stdin.fileno(), proc.stdin)
        else:
            hin = None

        if proc.stdout:
            hout = self.handler.new(path, proc.stdout.fileno(), proc.stdout)

        else:
            hout = None

        if proc.stderr:
            herr = self.handler.new(path, proc.stderr.fileno(), proc.stderr)
        else:
            herr = None

        hproc = self.handler.new(path, -1, proc)

        return path, hproc, hin, hout, herr

    def read(self, handle: int, nbytes: int, *, extras: dict[str, typing.Any] | None = None) -> bytearray:
        fd = self.handler.h(handle, 1)

        return bytearray(os.read(fd, nbytes))

    def readall(self, handle: int, *, extras: dict | None = None) -> bytearray:
        fd = self.handler.h(handle, 1)

        sz = os.stat(fd).st_size
        return bytearray(os.read(fd, sz))

    def readchunk(self, handle: int, *, extras: dict | None = None) -> bytearray:
        fd = self.handler.h(handle, 1)

        return bytearray(os.read(fd, self.chunk_sz))

    def write(self, handle: int, data: bytes, *, extras: dict[str, typing.Any] | None = None):
        fd = self.handler.h(handle, 1)

        return os.write(fd, data)

    def close(self, handle: int, *, extras: dict[str, typing.Any] | None = None) -> None:
        try:
            manager = self.handler.h(handle, 2)
        except OSError:
            manager = None

        fd = self.handler.close(handle, 1)
        try:
            if fd > 0:
                if manager and hasattr(manager, "close"):
                    manager.close()
                else:
                    os.close(fd)
        except OSError:
            pass

    def seek(
        self,
        handle: int,
        pos: int,
        whence: int,
        *,
        extras: dict[str, typing.Any] | None = None,
    ) -> int:
        fd = self.handler.h(handle, 1)
        whence = Whence(whence)

        match whence:
            case Whence.SEEK_CUR:
                whence_ = os.SEEK_CUR
            case Whence.SEEK_SET:
                whence_ = os.SEEK_SET
            case Whence.SEEK_END:
                whence_ = os.SEEK_END

        return os.lseek(fd, pos, whence_)

    def sync(self, handle: int, *, extras: dict[str, typing.Any] | None = None) -> None:
        fd = self.handler.h(handle, 1)

        return os.fsync(fd)

    def flush(self, handle: int, *, extras: dict[str, typing.Any] | None = None) -> bytearray:
        self.handler.h(handle, 1)

        return bytearray()

    def truncate(self, handle: int, length: int, *, extras: dict | None = None) -> None:
        fd = self.handler.h(handle, 1)
        return os.truncate(fd, length)

    def stat(
        self,
        handle: int,
        fields: int = StatField.ALL.value,
        *,
        extras: dict | None = None,
    ) -> dict:
        path = self.handler.h(handle, 0)

        st = Stat()

        exit_status = None
        pid = None

        fields = StatField(fields)

        if fields & StatField.STATUS or fields & StatField.PID:
            try:
                proc: subprocess.Popen = self.handler.h(handle, 2)

                pid = proc.pid

                try:
                    exit_status = proc._wait(0)  # type: ignore[attr-defined]
                except subprocess.TimeoutExpired:
                    pass

            except OSError:
                pass

        if fields & ~(StatField.STATUS | StatField.PID):
            st = os.stat(path)  # type: ignore[assignment]

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
                pid,
                exit_status,
            )
        )._asdict()

    def terminate(self, handle: int, *, extras: dict | None = None) -> None:
        proc: subprocess.Popen = self.handler.h(handle, 2)
        if winapi:
            subprocess.check_call(f'cmd /C "taskkill /pid {proc.pid} /F /T 1> nul 2> nul"')
        proc.terminate()


if winapi:

    class StreamWinAPi(IStreamService):
        protocol = Protocol.WINAPI
        chunk_sz = cfg_init("rd_chunk_size", 2048, section="mplugins.provider.local")

        handles: dict[int, typing.Any] = dict()

        def _h(self, handle) -> tuple[bytes, int]:
            info = self.handles[handle]
            if info is None:
                raise OSErrorEBADF

            return handle, *info

        def open_file(self, path: bytes, wiring: int, *, extras: dict | None = None) -> tuple[bytes, int]:
            extras = extras or dict()
            wiring = Wiring(wiring)

            desired_access = 0
            create_disposition = 3  # open existing
            file_attributes = 0x80  # FILE_ATTRIBUTE_NORMAL
            template_file = 0  # no template

            if wiring & Wiring.IN:
                desired_access |= winapi.GENERIC_READ  # type: ignore[attr-defined]
            if wiring & Wiring.OUT:
                desired_access |= winapi.GENERIC_READ  # type: ignore[attr-defined]
            if wiring & Wiring.CREATE:
                if wiring & Wiring.RESET:
                    create_disposition = 2  # create always
                else:
                    create_disposition = 1  # create new
            path = os.fsdecode(path)
            handle = winapi.CreateFile(  # type: ignore[attr-defined]
                path,
                extras.get("desired_access", desired_access),
                extras.get("share_mode", 0),
                extras.get("security_attributes", 0),
                extras.get("creation_disposition", create_disposition),
                extras.get("flags_and_attributes", file_attributes),
                extras.get("template_file", template_file),
            )

            self.handles[handle] = (path, None)

            return os.fsencode(path), handle

        def open_process(
            self,
            path: bytes,
            wiring: int,
            args: list[bytes],
            working_dir: bytes | None = None,
            env: dict[bytes, bytes] | None = None,
            *,
            extras: dict | None = None,
        ) -> tuple[bytes, int, int | None, int | None, int | None]:
            args = mshlex.list2cmdlineb(args)
            args = os.fsdecode(args)
            wiring = Wiring(wiring)

            extras = extras or {}

            working_dir = _working_dir(working_dir)
            env = env if env is None else {os.fsdecode(k): os.fsdecode(v) for k, v in env.items()}

            creation_flags = extras.get("creation_flags", 0)

            stdin_r = stdin_w = stdout_r = stdout_w = stderr_r = stderr_w = None
            stdin_proc = stdout_proc = stderr_proc = None
            toclose = list()
            tokeep = list()
            if wiring & Wiring.IN:
                stdin_r, stdin_w = winapi.CreatePipe(None, 0)  # type: ignore[attr-defined]
                toclose.append(stdin_r)
                tokeep.append(stdin_w)
                stdin_proc = winapi.DuplicateHandle(winapi.GetCurrentProcess(), stdin_r, winapi.GetCurrentProcess(), 0, 1, winapi.DUPLICATE_SAME_ACCESS)  # type: ignore
                toclose.append(stdin_proc)

            if wiring & Wiring.OUT:
                stdout_r, stdout_w = winapi.CreatePipe(None, 0)  # type: ignore[attr-defined]
                toclose.append(stdout_w)
                tokeep.append(stdout_r)
                stdout_proc = winapi.DuplicateHandle(winapi.GetCurrentProcess(), stdout_w, winapi.GetCurrentProcess(), 0, 1, winapi.DUPLICATE_SAME_ACCESS)  # type: ignore
                toclose.append(stdout_proc)

            if wiring & Wiring.ERR:
                stderr_r, stderr_w = winapi.CreatePipe(None, 0)  # type: ignore[attr-defined]
                toclose.append(stderr_w)
                tokeep.append(stderr_r)
                stderr_proc = winapi.DuplicateHandle(winapi.GetCurrentProcess(), stderr_w, winapi.GetCurrentProcess(), 0, 1, winapi.DUPLICATE_SAME_ACCESS)  # type: ignore
                toclose.append(stderr_proc)

            startup_info = subprocess.STARTUPINFO(  # type: ignore[attr-defined]
                dwFlags=extras.get("startup_info.flags", 0 if not wiring else winapi.STARTF_USESTDHANDLES), hStdInput=stdin_proc, hStdOutput=stdout_proc, hStdError=stderr_proc, lpAttributeList={"handle_list": []}, wShowWindow=extras.get("startup_info.show_window", 0)  # type: ignore[attr-defined]
            )

            env_ = env and {os.fsdecode(k): os.fsdecode(v) for k, v in env.items()} or dict()

            try:
                hp, ht, pid, _tid = winapi.CreateProcess(None, args, None, None, int(wiring.value != 0), creation_flags, env_, working_dir, startup_info)  # type: ignore

                winapi.CloseHandle(ht)  # type: ignore[attr-defined]

            except:  # noqa: E722
                for h in tokeep:
                    winapi.CloseHandle(h)  # type: ignore[attr-defined]

                raise

            finally:
                for h in toclose:
                    winapi.CloseHandle(h)  # type: ignore[attr-defined]

            self.handles[hp] = (path, pid)
            if stdin_w is not None:
                self.handles[stdin_w] = (path, pid)
            if stdout_r is not None:
                self.handles[stdout_r] = (path, pid)
            if stderr_r is not None:
                self.handles[stderr_r] = (path, pid)

            return path, hp, stdin_w, stdout_r, stderr_r

        def read(
            self,
            handle: int,
            nbytes: int,
            *,
            extras: dict[str, typing.Any] | None = None,
        ) -> bytearray:
            handle, _, _ = self._h(handle)  # type: ignore[misc]
            data, _ = winapi.ReadFile(handle, nbytes, False)  # type: ignore[attr-defined]
            return bytearray(data)

        def readall(self, handle: int, *, extras: dict | None = None) -> bytearray:
            handle, _, _ = self._h(handle)  # type: ignore[misc]

            raise NotImplementedError

        def readchunk(self, handle: int, *, extras: dict | None = None) -> bytearray:
            handle, _, _ = self._h(handle)  # type: ignore[misc]
            return self.read(handle, self.chunk_sz, extras=extras)

        def write(
            self,
            handle: int,
            data: bytes,
            *,
            extras: dict[str, typing.Any] | None = None,
        ):
            handle, _, _ = self._h(handle)  # type: ignore[misc]
            sz, _ = winapi.WriteFile(handle, data, False)  # type: ignore[attr-defined]
            return sz

        def close(self, handle: int, *, extras: dict[str, typing.Any] | None = None) -> None:
            handle, _, _ = self._h(handle)  # type: ignore[misc]
            self.handles.pop(handle)
            winapi.CloseHandle(handle)  # type: ignore[attr-defined]

        def sync(self, handle: int, *, extras: dict[str, typing.Any] | None = None) -> None:
            handle, _, _ = self._h(handle)  # type: ignore[misc]
            fd = msvcrt.open_osfhandle(handle, os.O_RDONLY)  # type: ignore[attr-defined]

            os.fsync(fd)

        def flush(self, handle: int, *, extras: dict[str, typing.Any] | None = None) -> bytearray:
            handle, _, _ = self._h(handle)  # type: ignore[misc]
            return bytearray()

        def truncate(
            self,
            handle: int,
            length: int | None = None,
            *,
            extras: dict[str, typing.Any] | None = None,
        ) -> None:
            handle, _, _ = self._h(handle)  # type: ignore[misc]
            raise NotImplementedError

        def seek(
            self,
            handle: int,
            pos: int,
            whence: int,
            *,
            extras: dict[str, typing.Any] | None = None,
        ) -> int:
            handle, _, _ = self._h(handle)  # type: ignore[misc]
            whence = Whence(whence)

            match whence:
                case Whence.SEEK_CUR:
                    whence_ = os.SEEK_CUR
                case Whence.SEEK_SET:
                    whence_ = os.SEEK_SET
                case Whence.SEEK_END:
                    whence_ = os.SEEK_END

            fd = msvcrt.open_osfhandle(handle, os.O_RDONLY)  # type: ignore[attr-defined]

            return os.lseek(fd, pos, whence_)

        def stat(
            self,
            handle: int,
            fields: int = StatField.ALL.value,
            *,
            extras: dict | None = None,
        ) -> dict:
            st = Stat()
            exit_status = None
            fields = StatField(fields)

            handle, path, pid = self._h(handle)  # type: ignore[misc]

            if fields & ~(StatField.STATUS | StatField.PID):
                st = os.stat(path)  # type: ignore[assignment]
                exit_status = None

            if pid and fields & StatField.STATUS:
                exit_code = winapi.GetExitCodeProcess(handle)  # type: ignore[attr-defined]
                if exit_code != winapi.STILL_ACTIVE:  # type: ignore[attr-defined]
                    exit_status = exit_code

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
                    pid,
                    exit_status,
                )
            )._asdict()

        def terminate(self, handle: int, *, extras: dict | None = None) -> None:
            try:
                exit_code = extras and extras.get("exit_code", 1) or 1
                winapi.TerminateProcess(handle, exit_code)  # type: ignore[attr-defined]
            except PermissionError:
                if winapi.GetExitCodeProcess(handle) == winapi.STILL_ACTIVE:  # type: ignore[attr-defined]
                    raise

    class StreamSystemAPI(StreamWinAPi):
        ...

else:

    class StreamSystemAPI(StreamPosix):  # type: ignore[no-redef]
        ...


class Stream(StreamPosix):
    protocol = Protocol.MYRRH
