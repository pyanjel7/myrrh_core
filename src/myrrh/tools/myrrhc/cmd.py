import os
import click
import typing
import logging
import asyncio
import itertools

from traceback import format_exc
from click.core import MultiCommand


import bmy

from .exceptions import Abort, Exit, Failure, Reboot
from . import completion

from myrrh.core.services import (
    cfg_get,
    cfg_init,
    __version__,
    __license__,
    __copyright__,
    PID,
)
from myrrh.core.services.logging import log
from myrrh.core.services.groups import myrrh_group_keys

from prompt_toolkit.shortcuts import print_container
from prompt_toolkit.formatted_text import to_formatted_text, ANSI
from prompt_toolkit.widgets import Label
from prompt_toolkit.layout import VSplit, HSplit, Dimension as D
from prompt_toolkit.application.current import get_app_session


class EidOuput:
    def __init__(self, eid: str):
        self.output = get_app_session().output

        self.texts: dict[str, str] = dict()

        eid = bmy.current(eid)  # type: ignore[attr-defined]

        if eid and bmy.isgroup(eid):  # type: ignore[attr-defined]
            for e in bmy.groupkeys(eid):  # type: ignore[attr-defined]
                self.texts[e] = ""
        else:
            self.texts[eid] = ""

    def __enter__(self):
        return self

    def __getitem__(self, eid):
        return Output(self, eid)

    def _print_container(self):
        frames = list()
        bodies = dict()
        pages = list()

        output = get_app_session().output
        rows = output.get_size().rows

        for e, m in self.texts.items():
            if not m:
                continue

            header = e and Label(to_formatted_text([("class:bold italic", e)])) or None
            lines = m.splitlines()
            max_line_len = D(preferred=max(*map(len, lines)))

            bodies[e] = list()
            bodies[e].append(max_line_len)
            while lines:
                body = Label(
                    to_formatted_text(ANSI("\n".join(lines[: rows - 1]))),
                    width=max_line_len,
                )

                lines = lines[rows - 1 :]

                bodies[e].append(header and [header, body] or [body])
                header = None

        pages = list(itertools.zip_longest(*bodies.values()))

        if not pages:
            return

        lens = pages[0]
        pages = pages[1:]
        for p in pages:
            p = [*(([Label("", width=lens[i])] if v is None else v) for i, v in enumerate(p))]

            hsplit = list(map(HSplit, p))
            frames.append(VSplit(hsplit))

        for f in frames:
            print_container(f)

    def write(self, message, eid=None):
        if not message:
            return

        if eid is None:
            for k, v in self.texts.items():
                self.texts[k] = v + message

        elif bmy.isgroup(eid):
            for eid in bmy.groupkeys(eid):
                self.texts[eid] = self.texts.get(eid, "") + message
        else:
            self.texts[eid] = self.texts.get(eid, "") + message

    def __exit__(self, *a, **kwa):
        self.close()

    def close(self):
        self._print_container()


class Output:
    def __init__(self, writer: EidOuput, eid):
        self.writer = writer
        self.eid = eid

    def fileno(self):
        return self.writer.output.fileno()

    def flush(self):
        self.writer.output.flush()

    def write(self, data):
        self.writer.write(data, self.eid)

    def isatty(self):
        try:
            return self.writer.output.stdout.isatty()
        except AttributeError:
            return False


def secho(message=None, eid=None, output=None, nl=True, *args, **kwargs):
    write_output = output

    if nl:
        message = message and (message + os.linesep) or os.linesep

    if not write_output and bmy.isgroup(message):
        write_output = EidOuput(bmy.groupkeys(message))

    try:
        if write_output:
            if bmy.isgroup(message):
                for e, m in message._d_.items():
                    click.secho(m, write_output[e], False, *args, **kwargs)
            else:
                click.secho(message, write_output[eid], False, *args, **kwargs)
        else:
            click.secho(message, None, False, *args, **kwargs)
    finally:
        if not output and write_output:
            write_output.close()


def error(message=None, level=None, *args, **kwargs):
    if not level or log.isEnabledFor(level):
        secho(message.capitalize(), *args, **kwargs, err=True, fg="red")


def success(message=None, *args, **kwargs):
    secho(message.capitalize(), *args, **kwargs, fg="green")


def info(message=None, *args, **kwargs):
    secho(message, *args, **kwargs)


def print_table(message, cols, *args, **kwargs):
    line = ""

    count = 0
    for sz in cols:
        s = len(message) > count and message[count].replace("\n", "\\n").replace("\r", "\\r") or ""

        txt_sz = max(0, sz - 2) or sz
        expand_sz = sz + 4

        if len(s) >= txt_sz:
            s = s[0] + s[1 : txt_sz - 4] + "..." + s[-1]

        line = "".join([line, ("%s\t" % s).expandtabs(expand_sz)])

        count += 1

    info(line, *args, **kwargs)


def format_eid(eid=None, info=None):
    try:
        eid = bmy.current(eid)

        result = eid

        if bmy.isgroup(eid):
            val = myrrh_group_keys(eid)
            if len(val) == 1:
                result = val[0]
            else:
                result = ",".join(("[%s]" % e) if bmy.isbuilt(eid=e) else ("(%s)" % e) for e in eid)
                info = None

        if info.__class__.__name__ == "_bmy_async_result":
            info = info._d_(eid)

        bro, brc = ("[", "]") if bmy.isbuilt(eid=eid) else ("(", ")")
        return "".join((bro, ":".join(filter(None, (result, info))), brc))

    except bmy.BmyInvalidEid:
        return "(%s)" % (info or "myrrhc")


progressbar = click.progressbar
style = click.style


class Path(click.ParamType):
    pass


class Argument(click.Argument):
    pass


class Option(click.Option):
    pass


class Context(click.Context):
    def __init__(
        self,
        command: "Command",
        parent: typing.Self | None = None,
        info_name: str | None = None,
        obj: typing.Any = None,
        auto_envvar_prefix: str | None = None,
        default_map: dict[str, typing.Any] | None = None,
        terminal_width: int | None = None,
        max_content_width: int | None = None,
        resilient_parsing: bool = False,
        allow_extra_args: bool | None = None,
        allow_interspersed_args: bool | None = None,
        ignore_unknown_options: bool | None = None,
        help_option_names: list[str] | None = None,
        token_normalize_func: typing.Callable[[str], str] | None = None,
        color: bool | None = None,
        show_default: bool | None = None,
        *,
        cmdline: str = "",
        ident: int | None = None,
    ) -> None:
        super().__init__(
            command,
            parent=parent,
            info_name=info_name,
            obj=obj,
            auto_envvar_prefix=auto_envvar_prefix,
            default_map=default_map,
            terminal_width=terminal_width,
            max_content_width=max_content_width,
            resilient_parsing=resilient_parsing,
            allow_extra_args=allow_extra_args,
            allow_interspersed_args=allow_interspersed_args,
            ignore_unknown_options=ignore_unknown_options,
            help_option_names=help_option_names,
            token_normalize_func=token_normalize_func,
            color=color,
            show_default=show_default,
        )
        self.cmdline = cmdline
        self.ident = ident or parent and parent.ident  # type: ignore[has-type]
        self.help_option_names = ["-h", "--help"]

    def exit(self, code=0):
        raise Failure()


class Command(click.Command):
    context_class = Context

    @property
    def command_class(self):
        return Command

    def make_context(self, info_name: str | None, args: typing.List[str], parent: Context | None = None, **extra: typing.Any) -> Context:  # type: ignore[override]
        info_name = args[0] if args and not (isinstance(args, str) and args[0].startswith("-")) and (not parent or isinstance(parent.command, Group)) else None
        self.context_settings["cmdline"] = parent and parent.cmdline or " ".join(args)
        return super().make_context(info_name, args, parent=parent, **extra)  # type: ignore[return-value]


class Group(click.Group):
    context_class = Context
    command_class = Command
    ident: int | None = None

    @property
    def group_class(self):
        return Group

    def set_ident(self, ident):
        self.context_settings["ident"] = ident

    def invoke(self, ctx):
        try:
            return super().invoke(ctx)

        except (Abort, Exit, Reboot):
            raise

        except click.ClickException as e:
            error("[%s]: %s" % (ctx.command_path, e.format_message()))

        except bmy.BmyException as e:
            error(format_exc(), logging.DEBUG, eid=e.eid and str(e.eid))
            error("[%s]: %s" % (ctx.command_path, str(e)), eid=e.eid and str(e.eid))

        except Exception as e:
            error(format_exc(), logging.DEBUG)
            error(str(e))

        raise Failure

    def get_command(self, ctx, cmd_name):
        command = self.commands.get(cmd_name, self.commands.get("-default"))
        return command

    def make_context(self, info_name: str | None, args: typing.List[str], parent: Context | None = None, **extra: typing.Any) -> Context:  # type: ignore[override]
        info_name = args[0] if args and not args[0].startswith("-") and (not parent or isinstance(parent.command, Group)) else None
        self.context_settings["cmdline"] = parent and parent.cmdline or " ".join(args)
        return super().make_context(info_name, args, parent=parent, **extra)  # type: ignore[return-value]


class DefaultCommand(MultiCommand):
    context_class = Context
    command_class = Command
    ident: int | None = None

    def __init__(self, group, name="-default", *args, **kwargs):
        super().__init__(name, *args, no_args_is_help=False, invoke_without_command=True, **kwargs)
        self.group = group

    def get_command(self, ctx, cmd_name):
        return self.group.get_command(ctx, cmd_name)

    def list_commands(self, ctx: Context) -> typing.List[str]:  # type: ignore[override]
        return self.group.list_commands(ctx)

    def make_context(self, info_name: str | None, args: typing.List[str], parent: Context | None = None, **extra: typing.Any) -> Context:  # type: ignore[override]
        self.context_settings["cmdline"] = parent and parent.cmdline or " ".join(args)
        return super().make_context("", [], parent=parent, **extra)  # type: ignore[return-value]


def group(name=None, **attrs):
    return click.group(name=name, cls=Group, **attrs)


def command(name=None, **attrs):
    return click.command(name=name, cls=Command, **attrs)


def argument(*param_decls, **attrs):
    shell_complete = attrs.pop("shell_complete", None)

    if isinstance(shell_complete, (list, tuple)):
        return click.argument(
            *param_decls,
            shell_complete=lambda _ctx, _cli, _incomplet: shell_complete,
            **attrs,
            cls=Argument,
        )

    return click.argument(*param_decls, shell_complete=shell_complete, **attrs, cls=Argument)


def option(*param_decls, **attrs):
    return click.option(*param_decls, **attrs, cls=Option)


def pass_option_eid(func):
    return option(
        "--eid",
        multiple=True,
        default=None,
        type=click.STRING,
        shell_complete=completion.eids_completer,
        help="entity id",
    )(func)


def pass_option_wdir(func):
    return option(
        "-w",
        "--working_dir",
        default=None,
        type=click.STRING,
        shell_complete=completion.path_completer(),
        help="working directory",
    )(func)


def option_cfg_default(name, default_value, section="myrrh.tools.myrrhc"):
    cfg_init(name, default_value, section)

    def default():
        return cfg_get(name, default_value, section=section)

    return default


def option_cfg_get(name, default_value=None, section="myrrh.tools.myrrhc"):
    return cfg_get(name, default_value, section=section)


def option_cfg_init(name, default_value=None, section="myrrh.tools.myrrhc"):
    cfg_init(name, default_value, section=section)


def print_version(ctx, param, value):
    if not value:
        return
    info("%s" % __version__)
    if param:
        ctx.exit()


def verbose(ctx, param, value):
    if not value:
        return

    if value:
        level = [logging.CRITICAL, logging.ERROR, logging.INFO, logging.DEBUG][min(3, value - 1)]
        bmy.debug(level=level)


pass_context = click.pass_context
CommandCollection = click.CommandCollection


@group(invoke_without_command=True)
@option("-v", "--verbose", count=True, callback=verbose, expose_value=False, is_eager=True)
@option("--version", is_flag=True, callback=print_version, expose_value=False, is_eager=True)
@click.help_option()
@pass_context
def myrrhc_cmds(ctx):
    pass


@myrrhc_cmds.command()
def license():
    """
    Display the full license text
    """
    info(__license__)


@myrrhc_cmds.command()
def copyright():
    """
    Display the full license text
    """
    info(__copyright__)


@myrrhc_cmds.command()
@pass_context
def interact(ctx):
    """
      Start an interactive shell. All subcommands are available in it.

    :param old_ctx: The current Click context.
    :param prompt_kwargs: Parameters passed to
        :py:func:`prompt_toolkit.shortcuts.prompt`.

      If stdin is not a TTY, no prompt will be printed, but only commands read
      from stdin.
    """
    from . import prompt

    loop = asyncio.get_event_loop()
    if not loop.is_running():
        loop.run_until_complete(prompt.PromptSession(ctx).run())


@myrrhc_cmds.command()
@pass_context
def version(ctx):
    "Quit the console"
    print_version(ctx, None, True)


@myrrhc_cmds.command()
@pass_context
@argument("commands", required=False, default=None, nargs=-1)
def help(ctx, commands):
    "Show help"
    cmd = myrrhc_cmds
    for command in commands:
        cmd = cmd.get_command(ctx, command)
    info(cmd.get_help(ctx))
    ctx.exit()


@myrrhc_cmds.command(hidden=True)
def cls():
    "Clear the console"
    click.clear()


@myrrhc_cmds.command()
def pid():
    "Return the pid of the current console"
    info(f"{PID}")
