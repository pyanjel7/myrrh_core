from asyncio.events import get_event_loop
import os
import asyncio
import time
import logging
import threading

from prompt_toolkit import history, shortcuts, auto_suggest, document

from prompt_toolkit.application.current import get_app, get_app_session
from prompt_toolkit.filters import Condition, is_done
from prompt_toolkit.layout import (
    ConditionalContainer,
    Window,
    FormattedTextControl,
    Float,
)
from prompt_toolkit.layout.containers import FloatContainer, HSplit, VSplit, WindowAlign
from prompt_toolkit.key_binding import merge_key_bindings
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.patch_stdout import patch_stdout

import bmy

from myrrh.core.services import cfg_get
from myrrh.core.services.logging import log

from myrrh.utils import mshlex

from . import completion
from . import cmd
from . import bindings
from . import exceptions

from traceback import print_exc
from prompt_toolkit.auto_suggest import Suggestion

HISTORY_CHAR = "!"


class History(history.FileHistory):
    def __init__(self) -> None:
        super().__init__(os.path.expanduser(os.path.join(cfg_get("@etc@", default=["~"])[0], ".myrrhc.history")))


class AutoSuggest(auto_suggest.AutoSuggest):
    def __init__(self):
        super().__init__()
        self.auto_suggest = auto_suggest.AutoSuggestFromHistory()

    def get_suggestion(self, buffer, document):
        history = buffer.history

        text = document.text.rsplit("\n", 1)[-1]

        if text.startswith("!"):
            text = text[1:]

            for string in reversed(list(history.get_strings())):
                for line in reversed(string.splitlines()):
                    if line.startswith(text):
                        return auto_suggest.Suggestion(line[len(text) :])


def create_exit_confirmation(prompt, style="class:exit-confirmation"):
    def get_text_fragments():
        # Show "Do you really want to exit?"
        return [
            (style, "\n %s ([y]/n) " % prompt.exit_message),
            ("[SetCursorPosition]", ""),
            (style, "  \n"),
        ]

    visible = ~is_done & Condition(lambda: prompt.show_exit_confirmation)

    return ConditionalContainer(
        content=Window(FormattedTextControl(get_text_fragments, focusable=True), style=style),
        filter=visible,
    )


class PromptSession(shortcuts.PromptSession):
    TITLE = "myrrhc"
    INFO = """
 Welcome to Myrrhc Console (for test purpose only)
  - Use it with fairplay -
Type help, copyright, credits, license for more information

ctrl-D to exit console

"""
    COMPLETER = completion.click_completer

    def __init__(self, ctx):
        # message cache
        self.__message_cache = None
        self.__info_task = None

        self._group_ctx = ctx.parent or ctx
        self._group = self._group_ctx.command
        self._group.options_metavar = ""
        self._group.set_ident(threading.get_ident())

        repl_command_name = ctx.command.name
        if isinstance(self._group_ctx.command, cmd.CommandCollection):
            available_commands = {cmd_name: cmd_obj for source in self._group_ctx.command.sources for cmd_name, cmd_obj in source.commands.items()}
        else:
            available_commands = self._group_ctx.command.commands

        available_commands.pop(repl_command_name, None)

        # Currently show 'Do you really want to exit?'
        self.exit_message = "Do you really want to exit"
        self.show_exit_confirmation = False
        self.confirm_exit = True

        try:
            session = get_app_session()
            output = session.output
            shortcuts.set_title(self.TITLE)
        except Exception:
            from prompt_toolkit.output import DummyOutput

            output = DummyOutput()

        super().__init__(
            message=self._message_no_info,
            completer=self.COMPLETER(self._group),
            history=History(),
            enable_history_search=True,
            complete_style=shortcuts.CompleteStyle.MULTI_COLUMN,
            complete_in_thread=True,
            auto_suggest=AutoSuggest(),
            output=output,
        )

    def _create_layout(self):
        layout = super()._create_layout()

        bottom_toolbar = ConditionalContainer(
            VSplit(
                [
                    Window(
                        FormattedTextControl(
                            lambda: self._bottom_toolbar()[0],
                            style="class:bottom-toolbar.text",
                        ),
                        style="class:bottom-toolbar",
                        dont_extend_height=True,
                        height=Dimension(min=1),
                        align=WindowAlign.LEFT,
                    ),
                    Window(
                        FormattedTextControl(
                            lambda: self._bottom_toolbar()[1],
                            style="class:bottom-toolbar.text",
                        ),
                        style="class:bottom-toolbar",
                        dont_extend_height=True,
                        height=Dimension(min=1),
                        align=WindowAlign.CENTER,
                    ),
                    Window(
                        FormattedTextControl(
                            lambda: self._bottom_toolbar()[2],
                            style="class:bottom-toolbar.text",
                        ),
                        style="class:bottom-toolbar",
                        dont_extend_height=True,
                        height=Dimension(min=1),
                        align=WindowAlign.RIGHT,
                    ),
                ]
            ),
            filter=~is_done & Condition(lambda: get_app().renderer.height_is_known) & Condition(lambda: self._bottom_toolbar is not None),
        )

        self.exit_confirmation = create_exit_confirmation(self)

        new_layout = FloatContainer(
            content=HSplit([layout.container, bottom_toolbar]),
            floats=[
                Float(
                    left=2,
                    bottom=1,
                    content=self.exit_confirmation,
                )
            ],
        )

        return Layout(new_layout, layout.container)

    def _create_prompt_bindings(self):
        return merge_key_bindings(
            [
                super()._create_prompt_bindings(),
                bindings.load_prompt_bindings(self),
                bindings.load_confirm_exit_bindings(self),
            ]
        )

    def _bottom_toolbar(self):
        if not cmd.option_cfg_default("fetch_eid_info", True)():
            if self.__info_task:
                self.__info_task.cancel()
                self.__info_task = None

            self.__message_cache == ("info disabled", "", "")

        elif self.__info_task is None:
            self._info_task()

        return self.__message_cache

    def _info_task(self):
        def _get_pwd(ident, cancel_event):
            while not cancel_event.is_set():
                try:
                    eid = bmy.current(ident=ident)
                    if not bmy.isgroup(eid):
                        l_info = cmd.option_cfg_default("fetch_eid_info_left", "cwd")().split(",")
                        m_info = cmd.option_cfg_default("fetch_eid_info_middle", "id")().split(",")
                        r_info = cmd.option_cfg_default("fetch_eid_info_right", "location")().split(",")
                    else:
                        l_info = cmd.option_cfg_default("fetch_eids_info_left", "cwd")().split(",")
                        m_info = cmd.option_cfg_default("fetch_eids_info_middle", "id")().split(",")
                        r_info = cmd.option_cfg_default("fetch_eids_info_right", "")().split(",")

                    if not eid or not cmd.option_cfg_default("fetch_eid_info", True)() or not bmy.isbuilt(eid=eid):
                        l_text = os.getcwd()
                        m_text = "*"
                        r_text = "*"
                    else:
                        info = bmy.info(
                            [
                                *(k.strip() for k in l_info),
                                *(k.strip() for k in m_info),
                                *(k.strip() for k in r_info),
                            ],
                            eid=eid,
                        )
                        if not bmy.isgroup(eid):
                            l_text = "|".join((str(info[k.strip()] or "na") for k in l_info)) if l_info else "*"
                            m_text = "|".join((str(info[k.strip()] or "na") for k in m_info)) if m_info else "*"
                            r_text = "|".join((str(info[k.strip()] or "na") for k in r_info)) if r_info else "*"
                        else:
                            l_text = "|".join(str(info._d_[i][k.strip()] or "na") for k in l_info for i in bmy.groupkeys(info)) if l_info else "*"
                            m_text = "|".join(str(info._d_[i][k.strip()] or "na") for k in m_info for i in bmy.groupkeys(info)) if m_info else "*"
                            r_text = "|".join(str(info._d_[i][k.strip()] or "na") for k in r_info for i in bmy.groupkeys(info)) if r_info else "*"

                except Exception as e:
                    l_text = "Unable to fetch information: %s" % str(e)
                    m_text = "*"
                    r_text = "*"

                self.__message_cache = (l_text, m_text, r_text)

                time.sleep(cmd.option_cfg_default("fetch_eid_info_delay", 1)())

        async def _coro():
            cancel_evt = asyncio.Event()

            try:
                await asyncio.to_thread(_get_pwd, threading.get_ident(), cancel_evt)
            finally:
                cancel_evt.set()
                self.__info_task = None

        self.__info_task = get_event_loop().create_task(_coro(), name="info")

    def _message_no_info(self):
        prompt = cmd.option_cfg_default("prompt", "")()
        if prompt:
            return prompt
        return cmd.format_eid()

    async def run(self):
        cmd.info(self.INFO)
        self.__message_cache = "..."

        try:
            while True:
                try:
                    with patch_stdout():
                        command = await self.prompt_async()
                    await self.command_call(command)

                except KeyboardInterrupt:
                    pass
        finally:
            if self.__info_task:
                self.__info_task.cancel()

    async def command_call(self, command):
        prev_status = 0
        args = self._parse(command)
        try:
            while True:
                arg = args.pop(0)

                if isinstance(arg, (tuple, list)):
                    with self._group.make_context(None, arg) as ctx:
                        try:
                            res = self._group.invoke(ctx)
                            if res:
                                await res()
                            prev_status = 0
                        except (exceptions.Reboot, exceptions.Abort, exceptions.Exit):
                            raise
                        except exceptions.Failure:
                            prev_status = 1
                        except Exception:
                            if log.level >= logging.DEBUG:
                                print_exc()
                            prev_status = 1

                elif arg == "&&" and prev_status != 0:
                    args.pop(0)

                elif arg == "||" and prev_status == 0:
                    args.pop(0)

        except IndexError:
            pass

    def _parse(self, command):
        if command and command.startswith(HISTORY_CHAR):
            suggestion = self.auto_suggest.get_suggestion(self.app.current_buffer, document.Document(text=command)) or Suggestion(text="")
            command = "".join([command[1:], suggestion.text])

            if not command.strip():
                commands = self.history.get_strings()
                command = commands and commands[-1] or ""

            self.history.append_string(command)

        if not command:
            return []

        args = mshlex.split(command)

        commands = []
        cmd = []
        for arg in args:
            if arg not in ("&&", "||", ";"):
                cmd.append(arg)
            else:
                commands.append(cmd)
                commands.append(arg)
                cmd = []

        commands.append(cmd)
        return commands
