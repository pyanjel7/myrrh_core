import os
import glob
import time
import signal
import logging
import collections
import functools

from traceback import format_exc

from myrrh import factory
from myrrh.core.services import cfg_init
from myrrh.core.services.logging import log
from myrrh.framework import Runtime
from myrrh.utils import mshlex
from myrrh.utils.filemode import filemode

from myrrh.framework.msh import madvsh

from myrrh.core.interfaces import IHost
from myrrh.core.services import groups

from ._bmy_internal import entities
from ._bmy_entity import BmyEntity
from ._bmy_exceptions import (
    BmyNotReady,
    BmyException,
    BmyMyrrhFailure,
    BmyInvalidParameter,
    BmyInvalidEid,
    BmyExecutionFailure,
)

__all__ = [
    "load",
    "save",
    "eids",
    "isgroup",
    "groupkeys",
    "groupvalues",
    "isbuilt",
    "current",
    "next",
    "previous",
    "entity",
    "select",
    "unselect",
    "new",
    "build",
    "debug",
    "system",
    "edit",
    "push",
    "get",
    "rm",
    "rmdir",
    "mkdir",
    "chdir",
    "lsdir",
    "info",
    "setinfo",
    "reboot",
    "boot",
    "halt",
    "snap",
    "resnap",
    "desnap",
    "fstat",
    "joinpath",
    "realpath",
    "basename",
    "dirname",
    "abspath",
    "read",
    "write",
    "cp",
    "cptree",
    "pwd",
    "get",
    "push",
    "transfer",
    "move",
    "execute",
    "execute_mem_c",
    "execute_mem_ce",
    "launch",
    "kill",
    "which",
    "csnap",
    "snaps",
    "resnap",
    "list_providers",
    "bmy_func",
]

FILE_EXT = cfg_init("myrrh_file_ext", ".emyrrh", section="myrrh.framework.bmy")
BMY_ASYNC = cfg_init("use_async_group_for_bmy", True, section="myrrh.framework.bmy")
EXEC_MEMORY_LEN = cfg_init("execute_memory_len", 200, section="myrrh.framework.bmy")

if BMY_ASYNC:
    _func = groups.myrrh_group_async
else:
    _func = groups.myrrh_group


def bmy_func(valid_eid_required=True, attr_name="eid", attr_type=None):
    def _(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            eid = kwargs.pop(attr_name, None)

            if valid_eid_required:
                eid = entities.current(eid)
                if not (eid):
                    raise BmyInvalidEid(eid=eid)

            if attr_type:
                eid = entities.get(eid=eid)
                if attr_type != "entity":
                    eid = getattr(eid, attr_type)

            try:
                if entities.isgroup(eid):
                    return _func(func)(*args, **kwargs, eid=groups.MyrrhGroup(keys=eid))

                kwargs[attr_name] = eid
                return func(*args, **kwargs)

            except BmyException as exc:
                exc.eid = exc.eid or str(hasattr(eid, "cfg") and eid.cfg.id or eid)
                exc.func = func.__name__
                raise
            except OSError:
                raise
            except Exception as exc:
                raise BmyExecutionFailure(eid, func.__name__, msg=str(exc)).with_traceback(exc.__traceback__) from None

        wrapper.__doc__ = "".join(
            [
                wrapper.__doc__ or "",
                """
                Notice: When the eid parameter is None the default entity is used.
                """,
            ]
        )

        wrapper.__annotations__["eid"] = str

        return wrapper

    return _


def eids() -> list[str]:
    """List available eids

    Returns:
        list[str]: A list containing all the 'eid' managed by bmy
    """
    return entities.eids


def isgroup(eid: str | tuple | groups.MyrrhGroup) -> bool:
    """Return true if eid is a group

    Args:
        eid (str | tuple | groups.MyrrhGroup): Single eid or group.

    Returns:
        bool: true if eid is a group
    """
    return entities.isgroup(eid)


def groupkeys(group: str | tuple | groups.MyrrhGroup) -> tuple:
    """Return a tuple containing eid or group keys.

    Args:
        group (str | tuple | groups.MyrrhGroup): Single eid or group.

    Returns:
        tuple: A tuple containing group keys
    """
    return entities.groupkeys(group)


def groupvalues(group: groups.MyrrhGroup) -> tuple:
    """Return a tuple with all the values contained in group.

    Args:
        group (groups.MyrrhGroup): Single eid or group.

    Returns:
        tuple:  A tuple containing group values
    """
    return entities.groupvalues(group)


def current(eid=None, ident=None):
    """Get the current entity id

    Args:
        eid (str|tuple, optional): Entity id. Defaults to None.
        ident (int, optional): thread ident. Defaults to None.

    Returns:
        str|tuple:  default entity id if eid is None else eid
    """
    return entities.current(eid, ident)


def next():
    """
    Go to next selected entity id
    """
    entities.history.goto_next()


def previous():
    """
    Return to previous selected entity id in history
    """
    entities.history.goto_previous()


def entity(eid: str | tuple | None = None) -> BmyEntity:
    """Returns the entity object associated with the eid

    Args:
        eid (str | tuple | None, optional): Single eid or group. Defaults to None.

    Returns:
        BmyEntity: entity object
    """
    return entities[current(eid)]


class _select:
    _prev_eid: str | None = None

    def __init__(self, args, eid, use_import=None):
        if args and eid is not None:
            raise ValueError("select does not support positional and eid keyword parameters")

        if len(args) == 1:
            eid = current(args[0])
        elif args:
            eid = current(args)
        else:
            eid = current(eid)

        self._eid = eid

        if not self._eid:
            # do nothing just return
            return
        use_import = isbuilt(eid) if use_import is None else use_import
        self._use_import = use_import
        self._prev_eid = entities.history.get_current()
        entities.eid = eid

    def __call__(self):
        if self._eid:
            return entity()

    def __enter__(self):
        if self._eid and self._use_import:
            import mlib

            try:
                mlib.mlib_push(self().system)
            except (BmyNotReady, OSError):
                raise

        if self._eid:
            return entity(self._eid)

    def __str__(self):
        return self._eid

    def __repr__(self):
        return "bmy.select<%s> at 0x%x" % (self._eid, id(self))

    def __exit__(self, _t=None, _v=None, _tb=None):
        if self._eid:
            entities.eid = self._prev_eid
            if self._use_import:
                import mlib

                mlib.mlib_pop()


def select(*args, eid=None, use_import=True):
    """
    Select the provided entity identifier as the default entity

    The default entity can be set temporary when the method is called using a with statement.
    If use_import is False, the mlib package is not available

    Args:
        eid (str): entity id
        use_import (bool): enable or disable mlib import (default:True)

    Returns:
        context manager: select context manager
    """
    return _select(args, eid, use_import)


def unselect():
    """
    Unselect default entity

    No more default entity selected in bmy
    """
    entities.eid = None


@bmy_func(attr_type="entity")
def isbuilt(*, eid: BmyEntity):
    """
    Checked build state of an entity

    Returns:
        bool: True if eid is already built else False

    """

    return eid.built


@bmy_func(valid_eid_required=False)
def new(path: str | list[str], eid, *, warehouse=[], pre=[], post=[], **kwargs):
    """
    Instantiates an entity


    Args:
        path (str): provider path
        eid (str): eid for the new entity
        warehouse (List) : list of warehouse items
        **kwargs: keyword arguments to pass to the provider

    Returns:
        str: eid of the newly created entity

    """
    if isinstance(path, str):
        paths = [path]

    settings = list()
    for p in paths:
        settings.append({"name": factory.Assembly.provider_name(p), **kwargs})

    supply = factory.Assembly.Supply(paths=paths, settings=settings, pre=pre, post=post)  # type: ignore[call-arg]
    assembly = factory.Assembly(supply, warehouse=warehouse)

    try:
        return entities.append(assembly, eid)
    except BmyException as e:
        e.func = "new"
        raise
    except (RuntimeError, Exception) as e:
        raise BmyMyrrhFailure(func="new", msg="new entity failure") from e


@bmy_func(attr_type="entity")
def save(path=None, full=False, *, eid):
    if os.path.isdir(path):
        path = os.path.join(path, "".join((eid.eid, FILE_EXT)))

    if not path:
        path = "".join(eid, ".emyyrh")

    with open(path, "w") as f:
        f.write(eid._assembly.fromEntity(eid, only_predefined=not full).json(indent=2))


def load(path=None, eid=None):
    f"""
    Loads an entity information file ('{FILE_EXT}' file)

    This function is similar to:func:`bmy.new` excepts that the list of predefined warehouse is loaded from an emyrrh file

    Args:
        path (str|list|tuple): path to entity "{FILE_EXT}" file
        eid (str|list|tuple): entity eid
    Returns:
        str|list: eid of the newly created entity

    """
    if not path:
        path = os.getcwd()

    if os.path.isdir(path):
        paths = glob.glob(os.path.join(path, f"*{FILE_EXT}"))
        path = []
    else:
        paths = [path]

    if not paths:
        raise BmyMyrrhFailure(func="load", msg="load failure no file found")

    if not isinstance(eid, (list, tuple)):
        eids = (eid,) + (None,) * (len(paths) - 1)
    else:
        eids = tuple(eid) + (None,) * (len(paths) - len(eid))

    results = list()
    for p, eid in zip(paths, eids):
        try:
            assembly = factory.Assembly.fromFile(p)
            if eid is None:
                eid, _, _ = os.path.basename(p).partition(".")

            results.append(entities.append(assembly, eid))

        except BmyException as e:
            e.func = "load"
            raise
        except Exception as e:
            log.debug("load entity failed with exception\n%s" % format_exc())
            raise BmyMyrrhFailure(func="load", msg="load failure for %s: %s" % (p, e))

    return results if isinstance(path, (list, tuple)) or isinstance(eid, (list, tuple)) or len(results) > 1 else results[0]


@bmy_func()
def build(eid):
    """
    build an entity


    Args:
        eid(str): entity to builf

    Returns:
        str: eid of the newly created entity

    """
    try:
        entity(eid).build()
    except BmyException as e:
        e.func = "build"
        raise
    except Exception as e:
        log.debug("build entity failed with exception\n%s" % format_exc())
        raise BmyMyrrhFailure(msg="%s" % e)

    return eid


def debug(level="?"):
    """
    Set/unset Myrrh myrrh.logging

    Args:
        level (str): log level (ie: DEBUG, WARNING, INFO, ERROR, CRITICAL)

    Returns:
        int: current level or None if log is disabled

    """
    if level == "?":
        return log.level

    log.disabled = not level

    if log.disabled:
        return None

    level = logging.getLevelName(level.upper()) if hasattr(level, "upper") else level

    try:
        log.setLevel(level)
    except (ValueError, TypeError) as e:
        raise BmyInvalidParameter(msg='"%s" is not a valid level' % level) from e

    return log.level


@bmy_func()
def system(cmd, *, eid):
    """
    Executes a shell command on the entity

    Args:
        cmd (str): command line to execute on the entity
        eid (str): entity id

    Returns:
        int: cmd error code
    """
    with select(eid):
        from mlib.py import os

    return os.system(cmd)


@bmy_func()
def execute(
    cmd,
    *,
    path: str | None = None,
    count: int | None = None,
    duration: float | None = None,
    interval: float | None = None,
    ttl: float | None = None,
    timeout: float | None = None,
    poll: float | None = None,
    raiseonttl: bool = False,
    raiseontimeout: bool = True,
    executein: bool = True,
    eid=None,
):
    """Run a command on an entity.

    This function supports many arguments to manage repeat and duration cases.
    Like python Popen, the first 'execute' argument should be a sequence of program arguments or a single string.

    When executein is True, the command is immediately called. Otherwise, the command is executed during iteration calls.

    Args:
        cmd (str|list): shell command line to execute on the entity or executable arguments
        path (str | None, optional): executable absolute path. Defaults to None.
        count (int | None, optional): repeat the execution 'count' times. Defaults to None.
        duration (float | None, optional): repeat the execution until 'duration' is raised. Defaults to None.
        interval (float | None, optional): interval between two executions. Defaults to None.
        ttl (float | None, optional): time to live of one execution. Defaults to None.
        timeout (float | None, optional): global execution timeout. Defaults to None.
        poll (float | None, optional): _description_. Defaults to None.
        raiseonttl (bool, optional): raise if ttl. Defaults to False.
        raiseontimeout (bool, optional): raise if timeout. Defaults to True.
        executein (bool, optional): execute immediately. Defaults to True.
        eid (str|tuple): eid of the entity to use for the command execution.

    Returns:
        iterator on execution results
    """
    with select(eid):
        from mlib.sh import advsh

    exe = advsh.execute(
        cmd,
        path=path,
        count=count,
        during=duration,
        interval=interval,
        ttl=ttl,
        timeout=timeout,
        poll=poll,
        raiseonttl=raiseonttl,
        raiseontimeout=raiseontimeout,
    )

    execute.mem.append(exe)

    if executein:
        for _ in exe:
            pass

    return exe


execute.mem = collections.deque(maxlen=EXEC_MEMORY_LEN)
execute.TimeoutExpired = madvsh.TimeoutExpired
execute.TTLExpired = madvsh.TTLExpired


def execute_mem_c():
    """clear execution memory"""
    execute.mem.clear()


def execute_mem_ce(pid: int):
    """clear one element from execution memory

    Args:
        pid (int): pid of the element to clear

    Raises:
        ValueError: when pid not found
    """
    for exe in execute.mem:
        for exe_info in exe.calls:
            if exe_info.proc.pid == pid:
                break
        else:
            continue

        break
    else:
        raise ValueError(f"pid {pid} not found")

    exe.remove(exe_info)

    if not exe.ncalls:
        execute.mem.remove(exe)


@bmy_func()
def which(path, wdir=None, *, eid):
    """
    Returns the path to an executable which would be run if the given path was called.

    Args:
        path (str): executable name
        wdir (str): working directory (default=Not set)

        eid (str): entity id

    Returns:
        str: absolute path if executable is found else None
    """
    with select(eid):
        from mlib.py import shutil, os

    if wdir:
        wdir = os.pathsep.join([wdir, os.environ.get("PATH", os.defpath)])

    path = shutil.which(path, path=wdir)

    if path:
        path = os.path.abspath(path)

    return path


@bmy_func(attr_type="entity")
def launch(cmd, wdir=None, *, eid: BmyEntity):
    """
    Launch a process on entity, and returns its pid

    The first argument should be a sequence of program arguments or else a single string.
    By default, the path of the program to execute is the first item in cmd if cmd is a sequence.

    Note:
        If the path of the program to execute is not an absolute path, a request is emit to the entity to determine its absolute path, if not found
        the cmd is executed as it is.

    Args:
        cmd (str,list): command to execute
        wdir (str,list): process working directory (default=Not set)

        eid (str): entity id

    Returns:
        int: pid of the new created process, 0 on failure

    """
    if not isinstance(cmd, (list, tuple)):
        cmd = mshlex.split(cmd, posix=eid.cfg.system.os == "posix")

    relcmd, params = cmd[0], cmd[1:]

    abscmd = None
    if not eid.runtime.myrrh_os.isabs(relcmd):
        try:
            abscmd = which(relcmd, wdir, eid=eid)
            log.debug('relative cmd path "%s" set to "%s"' % (relcmd, abscmd))
        except BmyException:
            pass
    else:
        abscmd = relcmd

    if not abscmd:
        log.debug('relative cmd path "%s" can not be resolve' % relcmd)
        abscmd = relcmd

    cmd = [eid.runtime.myrrh_os.fsencode(a) for a in [abscmd, *params]]
    wdir = None if wdir is None else eid.runtime.myrrh_os.fsencode(wdir)

    return eid.system.shell.spawn(cmd, working_dir=wdir)


@bmy_func(attr_type="entity")
def kill(pid, sig=signal.SIGTERM, *, eid: BmyEntity):
    """
    Send a signal to process

    Args:
        pid (int): process pid
        sig (int): signal to send (default: SIGTERM)

        eid (str): entity id
    """
    eid.system.shell.signal(pid, sig)


@bmy_func()
def edit(path, nl=False, edit=None, *, eid):
    """
    Edit a file from an entity

    Load a file from an entity and copy it to a temporary file on the localhost.
    After edition, the file is uploaded on the entity.
    User can specify the editor path to be called for file edition.
    after closing the file is updated on the entity.

    Args:
        path (str): path to the file to edit on the entity
        nl (bool): convert new line (default: False)
        edit (callable): this function is called with the temporary file path

        eid (str): entity id
    """

    def _edit(tmpfile):
        editor = edit if isinstance(edit, str) else os.getenv("Bmy_EDITOR", "notepad") if os.name == "nt" else os.getenv("Bmy_EDITOR", "xdg-open")

        os.system('""%s" "%s""' % (editor, tmpfile))

    import tempfile

    with select(eid):
        from mlib.py import os as eos

    filename = eos.path.basename(path)
    _, ext = eos.path.splitext(path)
    _edit = _edit if isinstance(edit, str) or edit is None else edit

    nl = None if nl else ""
    tmpfile = None
    try:
        with tempfile.NamedTemporaryFile(prefix=filename, suffix=ext, delete=False, newline=nl) as tmp:
            tmpfile = tmp.name
            eos.myrrh_syscall.stream_in(eos.fsencode(path), tmp)

        import click

        click.launch(tmpfile)

        with open(tmpfile, "rb") as tmp:
            eos.myrrh_syscall.stream_out(eos.fsencode(path), tmp)

    finally:
        if tmpfile:
            os.remove(tmpfile)


@bmy_func()
def push(src_path, dest_path, *, eid: str, chunk_size=None):
    """
    Upload local files to an entity (src_path may contain simple shell-style wildcards)

    Args:
        src_path (str): source local path (may be a directory. in such a case, full directory content is pushed on remote entity)
        dest_path (str): destination entity path

        eid (str): destination entity id

    Returns:
        tuple: (list of created dirs, list of uploaded files)

    """
    with select(eid):
        from mlib.fs import advfs
        from mlib.py import os

    chunk_size = advfs.CHUNK_SZ if chunk_size is None else chunk_size

    if os.local_os.path.isdir(src_path):
        return advfs.pushdir(src_path, dest_path, chunk_size=chunk_size)

    return list(), advfs.pushfile(src_path, dest_path)


@bmy_func()
def get(src_path, dest_path, *, eid: str, chunk_size=None):
    """
    Download a file from the selected entity to localhost

    Args:
        src_path (str): entity source path
        dest_path (str): local destination path

        eid (str): source entity id

    Returns:
        tuple: list of downloaded files
    """

    with select(eid):
        from mlib.fs import advfs
        from mlib.py import os

    chunk_size = advfs.CHUNK_SZ if chunk_size is None else chunk_size

    if os.path.isdir(src_path):
        return advfs.getdir(src_path, dest_path, chunk_size=chunk_size)

    return list(), advfs.getfile(src_path, dest_path)


@bmy_func()
def transfer(target_eid, src_path, dest_path, *, eid: str, chunk_size=None):
    """
    Transfer of files from a target entity to the selected entity


    Args:
        target_eid (str); destination entity id
        src_path (str): source entity path (directory or file)
        dest_path (str): destination local path

        eid (str): source entity id

    Returns:
        tuple[list[str],list[str]]: transferred dir list, transferred files list

    """

    with select(eid):
        from mlib.fs import advfs

    chunk_size = advfs.CHUNK_SZ if chunk_size is None else chunk_size

    return advfs.transfer(entities[target_eid], src_path, dest_path, chunk_size=chunk_size)


@bmy_func()
def fstat(path, follow=False, *, eid: str):
    """
    Get information about a file

    Args:
        path (str): filepath
        follow (bool): if True follows link, else get information of the link (default: False)

        eid (str): entity id

    Returns:
        dict(): a dictionary containing file information ('file', 'size', 'username', 'groupname', 'access', 'atime', 'mtime', 'ctime', 'stat')

    """
    with select(eid):
        from mlib.py import os

    st = os.stat(path) if follow else os.lstat(path)
    sz = st.st_size

    try:
        with select(eid):
            from mlib.py import pwd, grp
        username = pwd.getpwuid(st.st_uid).pw_name
        groupname = grp.getgrgid(st.st_gid).gr_name
    except Exception:
        username = "-"
        groupname = "-"

    for unit in ["", "Ki", "Gi"]:
        if abs(sz) < 1024:
            break
        sz /= 1024

    sz = "%.1f%sB" % (sz, unit if sz < 1024 else "T")

    return {
        "file": path,
        "size": sz,
        "username": username,
        "groupname": groupname,
        "access": filemode(st.st_mode),
        "atime": time.ctime(st.st_atime),
        "mtime": time.ctime(st.st_mtime),
        "ctime": time.ctime(st.st_ctime),
        "stat": st,
    }


@bmy_func()
def cp(from_path, to_path="", *, eid: str):
    """
    Copy file or directory on an entity

    Note:
        if the destination path exits, the file is overwritten

    Args:
        from_path (str): source file/folder path
        to_path (str): destination file/folder path

        eid (str): entity id
    """
    with select(eid):
        from mlib.fs import advfs
    advfs.copy(from_path, to_path)


@bmy_func()
def cptree(from_path, to_path, *, eid: str):
    """
    Deprecated use:func:`cp` instead
    """
    cp(from_path, to_path)


@bmy_func()
def move(from_path, to_path, *, eid: str):
    """
    Move file or directory on entity

    Args:
        from_path (str): source file/folder path
        to_path (str): destination file/folder path

        eid (str): entity id
    """
    with select(eid):
        from mlib.fs import advfs

    advfs.move(from_path, to_path)


@bmy_func()
def rm(path, *, eid: str):
    """
    Remove a file or a complete directory tree on an entity

    Path argument can use patterns according to the python mod:`glob` module

    Args:
        path (str): file path to delete

        eid (str): entity id
    """
    with select(eid):
        from mlib.fs import advfs

    advfs.rm(path)


@bmy_func()
def rmdir(path, force=False, *, eid: str):
    """
    deprecated use rm instead

    Remove a directory on an entity

    Path argument can use patterns according to the python mod:`glob` module

    Args:
        path (str): file path to delete
        force (bool): removes all directories and files in the specified directory

        eid (str): entity id
    """
    return rm(path, eid=eid)


@bmy_func()
def mkdir(path, *, eid: str):
    """
    Creates a directory on an entity  (creates all intermediate-level directories).

    Args:
        path (str): directory folder path

        eid (str): entity id
    """
    with select(eid):
        from mlib.py import os

    os.makedirs(path, exist_ok=True)


@bmy_func()
def chdir(path, *, eid: str) -> tuple[str, str]:
    """
    Change the current working directory on an entity.
    This may be useful in case of bmy.{execute,launch,lsdir,mkdir,info,...}  calls

    Args:
        path (str): new working directory path

        eid (str): entity id

    Returns:
        tuple(str, str): previous working directory, new working directory
    """
    with select(eid):
        from mlib.py import os

    cwd = os.getcwd()
    os.chdir(path)

    return cwd, os.getcwd()


@bmy_func(attr_type="runtime")
def pwd(*, eid: Runtime):
    """
    Return path of the current working directory

    Args:
        eid (str): entity id

    Returns:
        str: current working directory path
    """
    return eid.myrrh_os.getpath()


@bmy_func()
def lsdir(path=None, *, eid: str):
    """
    List entries in directories of an entity

    Paths argument can used patterns according to the python mod:`glob` module

    Args:
        path (str): folder path or pattern (default = current folder path)

        eid (str): entity id

    Returns:
        list[str]: list directory entries

    """
    with select(eid):
        from mlib.py import glob
        from mlib.py import os

    path = path or os.curdir

    if glob.has_magic(path):
        return glob.glob(path)

    return os.listdir(path)


def list_providers():
    """
    Return the list of installed provider
    """
    from myrrh.provider.registry import ProviderRegistry

    return list(ProviderRegistry.providers)


@bmy_func(attr_type="entity")
def setinfo(__category, *, eid: BmyEntity, **kwa):
    """
    Append information in the warehouse of the entity

    Args:
        __category (str): item category
        **kwargs : item data
        eid (str): entity id

    """

    from myrrh.warehouse import GenericItem

    item = GenericItem(type_=__category, **kwa)

    try:
        item.model_dump_json()
    except Exception:
        raise BmyInvalidParameter(eid=eid, msg="unable to serialize")

    eid.cfg.append(item)


@bmy_func(attr_type="entity")
def info(name=None, *, eid: BmyEntity):
    """
    Extract property/information on an entity

    Note:
        When name parameter is not set, the method returns the following default information: 'eid', 'manage address', 'location', 'os', 'system', 'host', 'vendor', 'working dir', 'warehouse'


    Args:
        name (list(str)|str): list of properties to retrieve or a property name

        eid (str): entity id

    Returns:
        Any : value of required property

    Raises:
        BmyInvalidParameter: when invalid parameter type is used

    """

    if name is not None and not isinstance(name, str) and not isinstance(name, (list, tuple)):
        raise BmyInvalidParameter(eid, 'invalid type for parameter "name"')

    infos = {
        "id": lambda: eid.cfg.id.id,
        "description": lambda: eid.cfg.system.description,
        "location": lambda: (eid.cfg.host.hostname, eid.cfg.host.loc),
        "os": lambda: eid.cfg.system.os,
        "services": lambda: eid._entity and eid._entity.provider.paths.get("0_") or list(),
        "catalog": lambda: eid._entity and eid._entity.provider.paths.get("1_") or list(),
        "cwd": lambda: eid.runtime.myrrh_os.getpath(),
        "warehouse": lambda: ",".join(eid.cfg.keys()),
    }

    entries = (name,) if isinstance(name, str) else name if isinstance(name, (list, tuple)) else tuple(infos) if name is None else ()

    info = collections.OrderedDict()

    for entry in entries:
        key, path = entry.split(".", 1) if "." in entry else (entry, "")

        if key not in infos:
            path = entry
            key = "warehouse"

        try:
            if key == "warehouse" and path:
                path = filter(None, path.split("."))
                cfg = eid.cfg
                for p in path:
                    cfg = cfg[p]
                info[entry] = cfg
            else:
                info[entry] = infos.get(entry, lambda: "na")()

        except Exception as e:
            info[entry] = f'entry "{entry}" can not be evaluated: %s' % e

    return info.get(name) if isinstance(name, str) else info


@bmy_func(attr_type="host")
def reboot(wait=False, force=False, *, eid: IHost):
    """
    Reboot entity

    Args:
        wait (bool): wait reboot complete.
        force (bool): hard reboot

        eid (str): entity id

    """
    eid.state.reset(wait=wait, force=force)


@bmy_func(attr_type="host")
def boot(wait=False, *, eid: IHost):
    """
    Boot an entity

    Args:
        wait (bool): wait boot complete
    """
    eid.state.start(wait=wait)


@bmy_func(attr_type="host")
def halt(force=False, wait=False, *, eid: IHost):
    """
    Halt entity

    Args:
        wait (bool): wait halt complete
        force (bool): hard shutdown

        eid (str): entity id

    """
    eid.state.stop(force=force, wait=wait)


@bmy_func(attr_type="host")
def snap(name, *, eid: IHost):
    """
    Take a snapshot of an entity

    Note:
        By default, perform a snapshot of the entity current state, if snapshot capability offered (by the manager)

    Args:
        name(str): name of the snapshot

        eid (str): entity id

    """
    eid.snap.new(name)


@bmy_func(attr_type="host")
def resnap(name, *, eid: IHost):
    """
    Restore a snapshot

    Note:
        If an entity does not support live snapshot, the new state of the entity is halted after being restored. (docker <v19.x)

    Args:
        name (str): name of the snapshot to restore

        eid (str): entity id

    """

    eid.snap.restore(name)


@bmy_func(attr_type="host")
def desnap(name, *, eid: IHost):
    """
    Delete a snapshot

    Args:
        name (str): name of the snapshot

        eid (str): entity id

    """
    eid.snap.delete(name)


@bmy_func(attr_type="host")
def snaps(eid: IHost):
    """
    Returns a list of available snapshots

    Args:
        eid (str): entity id

    Returns:
        list(): names of available snapshot

    """
    return eid.snap.names()


@bmy_func(attr_type="host")
def csnap(eid: IHost):
    """
    Return name of current snapshot

    Args:
        eid (str): entity id

    Returns:
        str: name of current snapshot
    """
    return eid.snap.current()


@bmy_func(attr_type="runtime")
def joinpath(*args, eid: Runtime):
    "Join one or more path warehouse"
    if not args:
        raise BmyInvalidParameter("a path is required")

    return eid.myrrh_os.fscast(args[0])(eid.myrrh_os.joinpath(*(eid.myrrh_os.f(a) for a in args)))


@bmy_func(attr_type="entity")
def realpath(path, eid: Runtime):
    "Return the canonical path of the specified filename"
    with select(eid):
        from mlib.py import os

    return os.realpath(path)


@bmy_func(attr_type="runtime")
def basename(path, eid: Runtime):
    "Return the base name part of a path"
    return eid.myrrh_os.fscast(path)(eid.myrrh_os.basename(eid.myrrh_os.f(path)))


@bmy_func(attr_type="runtime")
def dirname(path, eid: Runtime):
    "Return the directory name of the specified path"
    return eid.myrrh_os.fscast(path)(eid.myrrh_os.dirname(eid.myrrh_os.f(path)))


@bmy_func(attr_type="runtime")
def abspath(path, eid: Runtime):
    "Return the absolute path of the specified filename"
    return eid.myrrh_os.fscast(path)(eid.myrrh_os.getpathb(eid.myrrh_os.f(path)))


@bmy_func(attr_type="runtime")
def write(path, data=b"", *, encoding=None, errors=None, eid: Runtime):
    "Write data to file (!! overwrite existing one)"
    import io

    if isinstance(data, str):
        if not encoding:
            encoding = eid.myrrh_os.defaultencoding()

        data = data.encode(encoding, errors)

    with io.BytesIO(data) as e:
        eid.myrrh_syscall.stream_out(eid.myrrh_os.fsencode(path), e)


@bmy_func(attr_type="runtime")
def read(path, *, binary=False, encoding=None, errors=None, eid: Runtime):
    "Read file data and return it"
    import io

    if not encoding:
        encoding = eid.myrrh_os.defaultencoding
    if not errors:
        errors = "strict"

    with io.BytesIO() as data:
        eid.myrrh_syscall.stream_in(eid.myrrh_os.fsencode(path), data)
        return data.getvalue() if binary else data.getvalue().decode(encoding, errors)
