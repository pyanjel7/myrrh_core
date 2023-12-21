import colorama
import logging
import os
import signal
import prompt_toolkit

import bmy

from myrrh.utils import mstring
from myrrh.core.services import log, myrrh_sys, cfg_get, cfg_set, cfg_del
from myrrh.core.services import rebase as rebase_

from myrrh.tools.myrrhc_ext import myrrhc_cmds, cmd
from myrrh.tools.myrrhc import completion
from myrrh.tools.myrrhc import types

from prompt_toolkit.application.run_in_terminal import run_in_terminal

colorama.init()

cmd.option_cfg_init("editor")


@myrrhc_cmds.command(hidden=True, cls=cmd.DefaultCommand, group=myrrhc_cmds)
@cmd.pass_context
def _default(ctx):
    if ctx.cmdline:
        if not bmy.current():

            def _in_terminal():
                os.system(ctx.cmdline)

            run_in_terminal(_in_terminal)
        else:
            system([ctx.cmdline], standalone_mode=False, parent=ctx)


@myrrhc_cmds.command()
@cmd.argument("level", shell_complete=["debug", "info", "error", "warning", "disable"])
def debug(level):
    "(De)Activate Log at LEVEL"

    bmy.debug(level=None if level == "disable" else level)
    cmd.info("debug mode set to %s" % ("disabled" if log.disabled else logging.getLevelName(log.level)))


@myrrhc_cmds.command()
@cmd.argument("path", default=None, type=cmd.Path(), required=False, shell_complete=completion.local_path_completer(file_filter=lambda f: f.is_dir() or f.name == myrrh_sys))
def rebase(path):
    "Rebase myrrh system variables on file or directory where myrrh.msys is present"
    import json

    cmd.info(json.dumps(rebase_(path), indent=2))


def _setcfg_completer_key(ctx, cli, incomplet):
    section = ctx.params["section"]

    return [k for k in cfg_get(section=section, default={}) if not k.startswith("@")]


def _setcfg_completer_section(ctx, cli, incomplet):
    return [k.strip("__") for k in cfg_get() if k.startswith("__")]


def _setcfg_completer_value(ctx, cli, incomplet):
    section = ctx.params["section"]
    key = ctx.params["key"]
    value = cfg_get(key, section=section) if key else None
    return [value] if isinstance(value, str) else []


@myrrhc_cmds.command()
@cmd.option("-s", "--section", default="", type=types.STRING, required=False, shell_complete=_setcfg_completer_section)
@cmd.option("-r", "--rebase", flag_value=True)
@cmd.option("-e", "--edit", flag_value=True)
@cmd.argument("key", default=None, type=types.STRING, required=False, shell_complete=_setcfg_completer_key)
@cmd.argument("value", default=None, type=types.STRING, required=False, nargs=-1, shell_complete=_setcfg_completer_value)
def setcfg(key, edit, rebase, value, section):
    "Add or delete config entry in myrrh system variables (set no value to delete)"

    if rebase:
        rebase_()

    if not key and not edit:
        import json

        cmd.info(json.dumps(cfg_get(section=section), indent=2))
        return

    if key:
        if not value:
            cfg_del(key, section)
        else:
            cfg_set(key, mstring.str2int(" ".join(value)), section)

    if edit:
        import click

        click.edit(filename=cfg_get("@mbase@"), editor=cmd.option_cfg_get("editor"))
        rebase_()


@myrrhc_cmds.command()
@cmd.argument("path", type=cmd.Path(), shell_complete=completion.local_path_completer())
def load(path):
    "Load an entity"
    eid = bmy.load(
        path,
    )
    cmd.success(f'new entity "{eid}" loaded , build required.')


@myrrhc_cmds.command()
@cmd.pass_option_eid
@cmd.option("--full", flag_value=False)
@cmd.argument("path", type=cmd.Path(), shell_complete=completion.local_path_completer())
def save(path, eid, full):
    "Save an entity"
    bmy.save(path, full=full, eid=eid)
    cmd.success(f'entity "{eid}" saved on path.')


@myrrhc_cmds.command()
@cmd.pass_option_eid
def build(eid):
    "Build an entity"
    eid = bmy.build(eid=eid)
    cmd.success(f'entity "{eid}" built')


@myrrhc_cmds.command(name="list")
def list():
    for eid in bmy.eids():
        cmd.info(cmd.format_eid(eid))


@myrrhc_cmds.command()
@cmd.argument("eids", nargs=-1, shell_complete=completion.eids_completer)
def select(eids):
    bmy.select(eid=eids)


@myrrhc_cmds.command()
def unselect():
    bmy.unselect()


@myrrhc_cmds.command()
@cmd.pass_option_eid
@cmd.argument("attribute", required=False, nargs=-1)
def info(eid, attribute):
    "Print information on a entity"

    info = bmy.info(attribute or None, eid=eid)
    if info is None:
        cmd.info("no info available")
        return

    for eid, val in info._d_.items():
        lenjust = len(max(val.keys(), key=len))
        for k, v in val.items():
            cmd.info(f"{k.ljust(lenjust)} {v}", eid=eid)


@myrrhc_cmds.command()
def adv():
    "Myrrhc advanced mode"

    async def pyembed():
        import importlib

        locals = {e: bmy.entity(e) for e in bmy.eids()}
        locals.update({"bmy": bmy, "log": log, "exit": lambda: importlib.import_module("sys").exit(), "quit": lambda: importlib.import_module("sys").exit()})

        banner = """Myrrhc Advanced mode:
    exit() to return to normal BmyMode
    <entity_id>. to access entity instance

    list of entities:
    """
        for e in bmy.eids():
            banner = "%s\t%s\n" % (banner, e)

        # iconsole = code.InteractiveConsole(locals)
        # for line in pre_src.splitlines():
        #     iconsole.push(line)
        # iconsole.interact(banner=banner)

        cmd.info(banner)
        from ptpython.repl import embed

        try:
            await embed(globals(), locals, return_asyncio_coroutine=True, patch_stdout=True)
        except EOFError:
            pass
        except SystemExit:
            pass
        except KeyboardInterrupt:
            pass

    return pyembed


@myrrhc_cmds.command()
@cmd.pass_option_eid
@cmd.option("-w", "--wait", is_flag=True, default=False, help="wait for boot completion (default: no wait)")
def boot(eid, wait):
    "Boot the entity"
    bmy.boot(eid=eid, wait=wait)


@myrrhc_cmds.command()
@cmd.pass_option_eid
@cmd.option("-w", "--wait", is_flag=True, default=False, help="wait for reboot completion (default: no wait)")
@cmd.option("-f", "--force", is_flag=True, default=False, help="force reboot (default: do not force)")
def reboot(eid, wait, force):
    "Soft reboot of the entity"
    bmy.reboot(wait=wait, force=force, eid=eid)


@myrrhc_cmds.command()
@cmd.pass_option_eid
@cmd.option("-w", "--wait", is_flag=True, default=False, help="wait for entity halted (default: no wait)")
@cmd.option("-f", "--force", is_flag=True, default=False, help="force halt (default: do not force)")
def halt(eid, wait, force):
    "Soft halt of the entity"
    bmy.halt(eid=eid, wait=wait, force=force)


@myrrhc_cmds.command()
@cmd.pass_option_eid
@cmd.argument("name", type=types.STRING)
def snap(eid, name):
    "Take a snapshot of the entity"
    bmy.snap(name, eid=eid)


@myrrhc_cmds.command()
@cmd.pass_option_eid
@cmd.argument("name", type=types.STRING)
def resnap(eid, name):
    "Restore a snapshot of the entity"
    bmy.resnap(name, eid=eid)


@myrrhc_cmds.command()
@cmd.pass_option_eid
@cmd.argument("name", type=types.STRING)
def desnap(eid, name):
    "Delete a snapshot of the entity"
    bmy.desnap(name, eid=eid)


@myrrhc_cmds.command()
@cmd.pass_option_eid
def snaps(eid):
    "List available snapshots on an entity"
    names = bmy.snaps(eid=eid)

    for e, name in names._d_.items():
        cmd.info("%s:" % e)
        cmd.info("\n".join(name))


@myrrhc_cmds.command()
@cmd.pass_option_eid
def csnap(eid):
    "name of current entity snapshot"
    name = bmy.csnap(eid=eid)
    cmd.info(name)


@myrrhc_cmds.command()
@cmd.pass_option_eid
@cmd.argument("command", shell_complete=completion.path_executor())
def system(eid, command):
    "System execution"
    cmd.info('call system shell with "%s"' % command, bold=True)
    bmy.system(command, eid=eid)


@myrrhc_cmds.command(name="exec")
@cmd.pass_option_eid
@cmd.pass_context
@cmd.option("-c", "--count", type=types.INT, help="stop after count execution of the command", default=1)
@cmd.option("-i", "--interval", type=types.FLOAT, help="wait interval between execution of two commands in second", default=None)
@cmd.option("-t", "--ttl", type=types.FLOAT, help="command execution time to live in second", default=None)
@cmd.option("-w", "--timeout", type=types.FLOAT, help="time to wait before stop execution loop in second", default=None)
@cmd.option("-d", "--duration", type=types.INT, help="execute command until end of duration", default=None)
@cmd.argument("command", shell_complete=completion.path_executor())
@cmd.argument("params", nargs=-1, required=False, shell_complete=completion.path_completer())
class _exec:
    """
    Execute a command into selected entity

    Special command:
        ? [pid]: show the last execution result, if pid then show only the selected process
    """

    last_exec = None

    def _print_pid(self, pid):
        for eid, lastexec in _exec.last_exec._d_.items():
            for e in lastexec:
                if e.proc.pid == pid:
                    break
            else:
                continue

            col = (10, 22, 10, 8)
            cmd.print_table(('"%s"' % lastexec.cmd, "state", "time", "rval"), col, bold=True, eid=eid)
            cmd.print_table(("[%d]" % e.proc.pid, "%(state)s" % e, "%(time).5f" % e, "%(rval)s" % e), col, eid=eid)

            cmd.info(eid=eid)
            cmd.info("---stdout--", bold=True, eid=eid)
            if e.out:
                cmd.info(e.out, eid=eid)
            else:
                cmd.info("<empty>", eid=eid)
            cmd.info("---stderr--", bold=True, eid=eid)
            if e.err:
                cmd.error(e.err, eid=eid)
            else:
                cmd.info("<empty>", eid=eid)

    def __init__(self, ctx, count, duration, interval, ttl, timeout, command, params, eid):
        if command != "?":
            cmd.info('execute "%s" on %s' % (" ".join([command, *params]), cmd.format_eid(eid)), bold=True)
            cmd.info()
            _exec.last_exec = bmy.execute(" ".join([command, " ".join(params)]), count=count, timeout=timeout, interval=interval, duration=duration, ttl=ttl, raiseonttl=False, raiseontimeout=False, eid=eid)
            self._pids = None
        else:
            self._pids = params

    async def __call__(self):
        pids = self._pids and [mstring.str2int(p) for p in self._pids] or None

        if pids and len(pids) == 1:
            self._print_pid(pids[0])
            return

        col = (15, 22, 10, 22, 8)
        for eid, lastexec in _exec.last_exec._d_.items():
            cmd.print_table(('"%s"' % lastexec.cmd, "state", "time", "outputs", "rval"), col, bold=True, eid=eid)

            count = 0
            for e in lastexec:
                if not pids or e.pid in pids:
                    count += 1
                    cmd.print_table(("[%d]" % e.proc.pid, "%(state)s" % e, "%(time).5f" % e, '"%(out)s"' % e, "%(rval)s" % e), col, eid=eid)
                    cmd.print_table(("", "", "", '"%(err)s"' % e, ""), col, eid=eid)

            cmd.info(eid=eid)
            cmd.info(
                "%(label_ncalls)s: %(ncalls)d, %(label_times)s: %(time)0.1fs, %(label_means)s: %(means)0.1fs, %(label_var)s: %(var)0.5fs"
                % {
                    "label_ncalls": cmd.style("Total calls", bold=True),
                    "label_times": cmd.style("Total times", bold=True),
                    "label_means": cmd.style("Means", bold=True),
                    "label_var": cmd.style("Variance", bold=True),
                    "ncalls": lastexec.ncalls,
                    "time": lastexec.time or -1,
                    "means": lastexec.mtime or -1,
                    "var": lastexec.vtime or -1,
                },
                eid=eid,
            )


@myrrhc_cmds.command()
@cmd.pass_option_eid
@cmd.pass_option_wdir
@cmd.argument("commands", nargs=-1, metavar="command args...")
def launch(commands, eid, working_dir):
    "Launch a process in background"
    pid = bmy.launch(commands, wdir=working_dir, eid=eid)

    for eid, pid in pid._d_.items():
        cmd.info("[%s]" % pid, eid=eid)


@myrrhc_cmds.command()
@cmd.pass_option_eid
@cmd.pass_option_wdir
@cmd.argument("filename")
def which(filename, eid, working_dir):
    "Locate a command"
    locate = bmy.which(filename, wdir=working_dir, eid=eid)
    for eid, locate in locate._d_.items():
        if locate:
            cmd.info(locate, eid=eid)
        else:
            cmd.error("%s not found in PATH" % filename, eid=eid)


@myrrhc_cmds.command()
@cmd.pass_option_eid
@cmd.option("-s", "--sig", type=types.INT, help="signal number", default=signal.SIGTERM)
@cmd.argument("pid", type=types.INT)
def kill(pid, sig, eid):
    "Kill a process on an entity"
    bmy.kill(pid, sig, eid=eid)


@myrrhc_cmds.command()
@cmd.pass_option_eid
@cmd.argument("path", nargs=-1, type=types.STRING, required=False, shell_complete=completion.path_completer(only_directories=True))
def lsdir(path, eid):
    "List directories on the selected entity"
    dirs = bmy.lsdir(path, eid=eid)
    for eid, listdir in dirs._d_.items():
        for d, flist in listdir:
            if len(listdir) > 1:
                cmd.info('result%s for "%s":' % ("s" if len(flist) > 1 else "", d), eid=eid)
            for f in flist:
                cmd.info("%s%s" % ("\t" if len(listdir) > 1 else "", f), eid=eid)


@myrrhc_cmds.command()
@cmd.pass_option_eid
@cmd.argument("path", type=types.STRING, shell_complete=completion.path_completer(only_directories=True))
def cd(path, eid):
    "Change the current directory on the selected entity"
    if bmy.current(eid):
        bmy.chdir(path, eid=eid)
    else:
        os.chdir(path)


@myrrhc_cmds.command()
@cmd.pass_option_eid
@cmd.argument("path", type=types.STRING, shell_complete=completion.path_completer())
def rm(path, eid):
    "Remove a file on the selected entity"
    bmy.rm(path, eid=eid)


@myrrhc_cmds.command()
@cmd.pass_option_eid
@cmd.option("-f", "--force", is_flag=True, default=False, help="force remove directory and its contents")
@cmd.argument("path", type=types.STRING, shell_complete=completion.path_completer(only_directories=True))
def rmdir(force, path, eid):
    "Remove a directory on the selected entity"
    bmy.rmdir(path, force, eid=eid)


@myrrhc_cmds.command()
@cmd.pass_option_eid
@cmd.argument("path", type=types.STRING, shell_complete=completion.path_completer(only_directories=True))
def mkdir(path, eid):
    "Create a directory on the selected entity"
    bmy.mkdir(path, eid=eid)


@myrrhc_cmds.command()
@cmd.pass_option_eid
@cmd.option("--nl", is_flag=True, help="nl: converting new line in host format, no conversion by default")
@cmd.option("--editor", shell_complete=completion.local_path_executor(), help="editor executable path", default=None)
@cmd.argument("path", type=types.STRING, shell_complete=completion.path_completer())
def edit(path, editor, nl, eid):
    "Edit a file on the entity"
    bmy.edit(path, nl=nl, edit=editor, eid=eid)


@myrrhc_cmds.command()
@cmd.pass_option_eid
@cmd.argument("from_path", type=types.STRING, shell_complete=completion.local_path_completer())
@cmd.argument("to_path", required=False, default="", shell_complete=completion.path_completer())
def push(from_path, to_path, eid):
    "Upload file(s) to the selected entity"

    fcount = 0
    dcount = 0

    for eid, (ds, fs) in bmy.push(from_path, to_path, eid=eid)._d_.items():
        fcount = len(fs)
        dcount = len(ds)

    if dcount:
        cmd.success("%d dir%s created successfully" % (dcount, (dcount > 1) and "s" or ""))

    cmd.success("%d file%s pushed successfully" % (fcount, (fcount > 1) and "s" or ""))


@myrrhc_cmds.command()
@cmd.pass_option_eid
@cmd.argument("from_path", type=types.STRING, shell_complete=completion.path_completer())
@cmd.argument("to_path", required=False, default="", shell_complete=completion.local_path_completer())
def get(from_path, to_path, eid):
    "Download file(s) from the selected entity"

    fcount = 0
    dcount = 0

    for eid, (ds, fs) in bmy.get(from_path, to_path, eid=eid)._d_.items():
        fcount = len(fs)
        dcount = len(ds)

    if dcount:
        cmd.success("%d director%s created successfully" % (dcount, (dcount > 1) and "ies" or "y"))
    cmd.success("%d file%s got successfully" % (fcount, (fcount > 1) and "s" or ""))


@myrrhc_cmds.command()
@cmd.pass_option_eid
@cmd.argument("from_path", type=types.STRING, shell_complete=completion.path_completer())
@cmd.argument("to_path", type=types.STRING, shell_complete=completion.path_completer())
def cp(from_path, to_path, eid):
    "Copy file/directory on entity"
    bmy.cp(from_path, to_path, eid=eid)


@myrrhc_cmds.command()
@cmd.pass_option_eid
@cmd.argument("from_path", type=types.STRING, shell_complete=completion.path_completer())
@cmd.argument("target_eid", shell_complete=completion.eids_completer)
@cmd.argument("to_path", required=False, default="", shell_complete=completion.path_completer(use_argument_for_eid="target_eid"))
def transfer(from_path, to_path, eid, target_eid):
    "Download file(s) from the selected entity"

    for eid, (ds, fs) in bmy.transfer(target_eid, from_path, to_path, eid=eid)._d_.items():
        fcount = len(fs)
        dcount = len(ds)

    if dcount:
        cmd.success("%d director%s transferred successfully" % (dcount, (dcount > 1) and "ies" or "y"))
    cmd.success("%d file%s transferred successfully" % (fcount, (fcount > 1) and "s" or ""))


@myrrhc_cmds.command()
@cmd.pass_option_eid
@cmd.argument("paths", nargs=-1, type=types.STRING, required=True)
def joinpath(paths, eid):
    "Join one or more path warehouse"
    cmd.info(bmy.joinpath(*paths, eid=eid))


@myrrhc_cmds.command()
@cmd.pass_option_eid
@cmd.argument("path", type=types.STRING, required=True)
def realpath(path, eid):
    "Return the canonical path of the specified filename"
    cmd.info(bmy.realpath(path, eid=eid))


@myrrhc_cmds.command()
@cmd.pass_option_eid
@cmd.argument("path", type=types.STRING, required=True)
def basename(path, eid):
    "Return the base name part of a path"
    cmd.info(bmy.basename(path, eid=eid))


@myrrhc_cmds.command()
@cmd.pass_option_eid
@cmd.argument("path", type=types.STRING, required=True)
def dirname(path, eid):
    "Return the directory name of the specified path"
    cmd.info(bmy.dirname(path, eid=eid))


@myrrhc_cmds.command()
@cmd.pass_option_eid
@cmd.argument("path", type=types.STRING, required=True, shell_complete=completion.path_completer())
def read(path, eid):
    "Display file content to console output"

    async def read():
        data = bmy.read(path, eid=eid)

        if not bmy.isgroup(data):
            data = {bmy.current(eid=eid): data}
        else:
            data = data._d_

        binding = prompt_toolkit.key_binding.KeyBindings()

        @binding.add("c-d")
        @binding.add("q")
        def _(event):
            "Quit."
            event.app.exit()

        search_field = prompt_toolkit.widgets.SearchToolbar(text_if_not_searching=[("class:not-searching", "Press '/' to start searching")])

        for _eid, data in data.items():

            def get_status_bar_text():
                return [("class:status", _eid + " - " + path)]

            text_area = prompt_toolkit.widgets.TextArea(
                text=data,
                read_only=True,
                scrollbar=True,
                line_numbers=False,
                search_field=search_field,
            )

            root_container = prompt_toolkit.layout.containers.HSplit([prompt_toolkit.layout.containers.Window(content=prompt_toolkit.layout.controls.FormattedTextControl(get_status_bar_text)), text_area, search_field])

            application = prompt_toolkit.application.application.Application(layout=prompt_toolkit.layout.layout.Layout(root_container), key_bindings=binding, enable_page_navigation_bindings=True)

            await application.run_async()

    return read


@myrrhc_cmds.command()
@cmd.pass_option_eid
@cmd.argument("path", type=types.STRING, required=True, shell_complete=completion.path_completer())
@cmd.argument("text", type=types.STRING, required=False, default=None)
def write(path, text, eid):
    "Write a text to a file"
    if text is not None:
        bmy.write(path, data=text.encode(), eid=eid)
        return

    async def write():
        text = await prompt_toolkit.shortcuts.PromptSession("== %s ==\n" % path, multiline=True, bottom_toolbar="<esc> <enter> to quit", editing_mode=prompt_toolkit.enums.EditingMode.VI, enable_open_in_editor=True).prompt_async()
        cmd.info("== eof ==")
        bmy.write(path, data=text.encode(), eid=eid)

    return write
