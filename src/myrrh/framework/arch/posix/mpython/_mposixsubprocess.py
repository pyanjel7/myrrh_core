import typing

from myrrh.core.services.system import AbcRuntime

__mlib__ = "AbcPosixSubprocess"


class AbcPosixSubprocess(AbcRuntime):
    __frameworkpath__ = "mpython._mposixsubprocess"

    def cloexec_pipe(self) -> tuple[int, int]:
        raise NotImplementedError()

    def fork_exec(
        self,
        __process_args: list[str | bytes] | None,
        __executable_list: list[bytes],
        __close_fds: bool,
        __fds_to_keep: tuple[int, ...],
        __cwd_obj: str,
        __env_list: list[bytes] | None,
        __p2cread: int,
        __p2cwrite: int,
        __c2pred: int,
        __c2pwrite: int,
        __errread: int,
        __errwrite: int,
        __errpipe_read: int,
        __errpipe_write: int,
        __restore_signals: int,
        __call_setsid: int,
        __pgid_to_set: int,
        __gid_object: int | None,
        __groups_list: list[int] | None,
        __uid_object: int | None,
        __child_umask: int,
        __preexec_fn: typing.Callable[[], None],
        __allow_vfork: bool,
    ) -> int:
        raise NotImplementedError()
