from ..interfaces import (
    ABCDelegation,
    ICoreFileSystemService,
    ICoreStreamService,
    ICoreShellService,
)

__all__ = ["ShellService", "FileSystemService", "StreamService"]


class FileSystemService(ICoreFileSystemService, ABCDelegation):
    __delegated__ = (ICoreFileSystemService,)

    def __init__(self, ifs):
        self.__delegate__(ICoreFileSystemService, ifs)

    def list(self, path: bytes, *, extras: dict | None = None) -> list[bytes]:
        assert isinstance(path, bytes), f"path argument must be of type bytes not {path.__class__.__name__}"

        return self._delegate_.list(path, extras=extras)

    def stat(self, path: bytes, *, extras: dict | None = None) -> dict:
        assert isinstance(path, bytes), f"path argument must be of type bytes not {path.__class__.__name__}"

        return self._delegate_.stat(path)

    def rm(self, path: bytes, *, extras: dict | None = None) -> None:
        assert isinstance(path, bytes), f"path argument must be of type bytes not {path.__class__.__name__}"

        return self._delegate_.rm(path, extras=extras)

    def mkdir(self, path: bytes, *, extras: dict | None = None) -> None:
        assert isinstance(path, bytes), f"path argument must be of type bytes not {path.__class__.__name__}"

        return self._delegate_.mkdir(path, extras=extras)

    def rmdir(self, path: bytes, *, extras: dict | None = None) -> None:
        assert isinstance(path, bytes), f"path argument must be of type bytes not {path.__class__.__name__}"

        return self._delegate_.rmdir(path, extras=extras)

    def is_container(self, path: bytes, *, extras: dict | None = None) -> bool:
        assert isinstance(path, bytes), f"path argument must be of type bytes not {path.__class__.__name__}"

        return self._delegate_.is_container(path, extras=extras)

    def exist(self, path: bytes, *, extras: dict | None = None) -> bool:
        assert isinstance(path, bytes), f"path argument must be of type bytes not {path.__class__.__name__}"

        return self._delegate_.exist(path, extras=extras)


def _assert_env(env):
    if env is not None:
        if not hasattr(env, "items"):
            return (
                False,
                "invalid env type detected, env must be of type dict not %s" % (env.__class__.__name__),
            )
        for k, v in env.items():
            if not isinstance(k, bytes):
                return (
                    False,
                    "invalid key type detected in env, argument must be of type bytes not %s" % (k.__class__.__name__),
                )
            if not isinstance(v, bytes):
                return (
                    False,
                    "invalid value type detected in env, argument must be of type bytes not %s" % (v.__class__.__name__),
                )
    return True, "ok"


def _assert_cmd_bytes(cmd):
    return (
        isinstance(cmd, bytes),
        f"command argument must be of type bytes not {cmd.__class__.__name__}",
    )


def _assert_working_dir(working_dir):
    return (
        working_dir is None or isinstance(working_dir, bytes),
        f"working_dir argument must be of type bytes not {working_dir.__class__.__name__}",
    )


def _assert_cmd_list(cmd):
    if len(cmd) == 0:
        return False, "invalid command value, command must not be empty"

    if not isinstance(cmd, (list, tuple)):
        return (
            False,
            f"command argument must be of type bytes not {cmd.__class__.__name__}",
        )

    for arg in cmd:
        if not isinstance(arg, bytes):
            return (
                False,
                f"invalid argument type detected in command, argument must be of type bytes not {arg.__class__.__name__}",
            )

    return True, "ok"


class ShellService(ICoreShellService, ABCDelegation):
    __delegated__ = (ICoreShellService,)

    def __init__(self, ishell):
        self.__delegate__(ICoreShellService, ishell)

    def execute(
        self,
        command: bytes,
        working_dir: bytes | None = None,
        env: dict | None = None,
        *,
        extras: dict | None = None,
    ) -> tuple[bytes, bytes, bytes]:
        assert all(m := _assert_cmd_bytes(command)), m
        assert all(m := _assert_working_dir(working_dir)), m
        assert all(m := _assert_env(env)), m

        return self._delegate_.execute(command, working_dir, env, extras=extras)

    def spawn(
        self,
        command: bytes,
        working_dir: bytes | None = None,
        env: dict | None = None,
        *,
        extras: dict | None = None,
    ) -> int:
        assert all(m := _assert_cmd_list(command)), m
        assert all(m := _assert_working_dir(working_dir)), m
        assert all(m := _assert_env(env)), m

        return self._delegate_.spawn(command, working_dir, env)


class StreamService(ICoreStreamService, ABCDelegation):
    __delegated__ = (ICoreStreamService,)

    def __init__(self, istream):
        self.__delegate__(ICoreStreamService, istream)

    def open_file(self, path: bytes, wiring: int, *, extras: dict | None = None) -> tuple[bytes, int]:
        assert isinstance(path, bytes), f"path argument must be of type bytes not {path.__class__.__name__}"

        return self._delegate_.open_file(path, wiring, extras=extras)

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
        assert isinstance(path, bytes), f"path argument must be of type bytes not {path.__class__.__name__}"

        return self._delegate_.open_process(path, wiring, args, working_dir, env, extras=extras)

    def write(self, handle: int, data: bytes, *, extras: dict | None = None):
        assert isinstance(data, (bytes, bytearray)), f"data argument must be of type bytes not {data.__class__.__name__}"

        return self._delegate_.write(handle, data, extras=extras)
