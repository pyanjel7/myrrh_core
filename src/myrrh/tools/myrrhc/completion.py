import os
import stat
from click.core import BaseCommand

import click.shell_completion
from prompt_toolkit import completion, eventloop

from myrrh.utils import mshlex
import bmy


class ThreadedCompleter:
    def get_completions_async(self, document, complete_event):
        """
        Asynchronous generator of completions.
        This yields both Future and Completion objects.
        """
        return eventloop.generator_to_async_generator(lambda: self.get_completions(document, complete_event) or ())


class _ShellComplete(click.shell_completion.ShellComplete):
    def get_completion_args(self):
        try:
            args = mshlex.split(self.complete_var.text_before_cursor)
        except ValueError:
            # Invalid command, perhaps caused by missing closing quotation.
            return

        current_args = []

        try:
            while True:
                arg = args.pop()
                if arg not in ("&&", "||", ";"):
                    current_args.append(arg)
                else:
                    break

        except IndexError:
            pass

        current_args.reverse()
        args = current_args

        cursor_within_command = self.complete_var.text_before_cursor.rstrip() == self.complete_var.text_before_cursor
        if args and cursor_within_command:
            incomplete = args[-1]
            args = args[:-1]
        else:
            incomplete = ""

        return args, incomplete


class _ClickCompleter(completion.Completer, ThreadedCompleter):
    def __init__(self, cli: BaseCommand):
        self.cli = cli

    def get_completions(self, document, complete_event):
        shell_complete = _ShellComplete(self.cli, self.cli.context_settings, "", document)
        args, incomplete = shell_complete.get_completion_args()
        sh_completions = shell_complete.get_completions(args, incomplete) or []
        words = [a.value for a in sh_completions]

        return completion.WordCompleter(words).get_completions(document, complete_event=complete_event)


class _BmyPathShellComplete:
    def __init__(
        self,
        only_directories=False,
        get_paths=None,
        file_filter=None,
        min_input_len=0,
        expanduser=False,
        local=False,
        use_argument_for_eid="eid",
        file_text=None,
    ):
        assert get_paths is None or callable(get_paths)
        assert file_filter is None or callable(file_filter)
        assert isinstance(min_input_len, int)
        assert isinstance(expanduser, bool)

        self.only_directories = only_directories
        self.get_paths = get_paths or (lambda _: ["."])
        self.file_filter = file_filter or (lambda _: True)
        self.min_input_len = min_input_len
        self.expanduser = expanduser
        self.local = local
        self.use_argument_for_eid = use_argument_for_eid
        self.doc = None
        self.file_text = file_text or self._file_text

    def _file_text(self, dirent, ctx):
        if dirent.is_dir():
            filename = dirent.name + self._os(ctx).sep
        else:
            filename = dirent.name

        return filename

    def __call__(self, ctx, cli, incomplet):
        # Complete only when we have at least the minimal input length,
        # otherwise, we can too many results and autocompletion will become too
        # heavy.
        paths = []

        if len(incomplet) < self.min_input_len:
            return
        text = incomplet
        try:
            # Do tilde expansion.
            if self.expanduser:
                text = self._os(ctx).path.expanduser(text)

            # Directories where to look.
            dirname = self._os(ctx).path.dirname(text)
            if dirname.startswith(self._os(ctx).path.curdir) or dirname.startswith(self._os(ctx).path.pardir) or self._os(ctx).path.isabs(dirname):
                directories = [dirname]
            elif dirname:
                directories = [self._os(ctx).path.dirname(self._os(ctx).path.join(p, text)) for p in self.get_paths(ctx)]
            else:
                directories = self.get_paths(ctx)

            # Start of current file.
            prefix = self._os(ctx).path.basename(text)

            directories = sorted(filter(None, directories))

            # Get all filenames.
            for directory in directories:
                try:
                    # Look for matches in this directory.
                    files = filter(
                        lambda dirent: (dirent.name.startswith(prefix) and ((not self.only_directories or dirent.is_dir()) and self.file_filter(dirent))),
                        self._os(ctx).scandir(directory),
                    )
                    files = sorted(files, key=lambda d: d.name)
                    for dirent in files:
                        filename = self.file_text(dirent, ctx)
                        filename = self._os(ctx).path.sep + filename if text and text[-1] == self._os(ctx).path.sep else filename
                        completion = click.shell_completion.CompletionItem(filename, help=self._os(ctx).path.dirname(dirent.path))
                        paths.append(completion)
                except Exception:
                    pass

        except Exception:
            pass

        return paths

    def _os(self, ctx):
        eid = None

        eid = ctx.params.get(self.use_argument_for_eid, None) or bmy.current(ident=ctx.ident)
        if not bmy.isgroup(eid) and eid:
            eid = (eid,)

        if not eid:
            return os

        if len(eid) == 1:
            try:
                with bmy.select(eid=eid[0]):
                    from mlib.py import os
                return os
            except Exception:
                pass

        raise OSError


class _LocalPathShellComplete(_BmyPathShellComplete):
    def _os(self, ctx):
        return os


class _BmyExecutableShellComplete(_BmyPathShellComplete):
    """
    Complete only executable files in the current path.
    """

    def __init__(self):
        super().__init__(
            only_directories=False,
            min_input_len=1,
            get_paths=lambda ctx: self._os(ctx).environ.get("PATH", "").split(self._os(ctx).pathsep) + [self._os(ctx).getcwd()],
            file_filter=lambda dirent: stat.S_IMODE(dirent.stat().st_mode) & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH),
            expanduser=True,
        ),


class _LocalExecutableShellComplete(_BmyPathShellComplete):
    """
    Complete only executable files in the current local path.
    """

    def __init__(self):
        super().__init__(
            only_directories=False,
            min_input_len=1,
            get_paths=lambda ctx: self._os(ctx).environ.get("PATH", "").split(self._os(ctx).pathsep) + [self._os(ctx).getcwd()],
            file_filter=lambda ctx, dirent: self._os(ctx).access(dirent.path, os.X_OK),
            expanduser=True,
        )

    def _os(self, ctx):
        return os


def eids_completer(_ctx, _cli, _incomplet):
    return bmy.eids()


path_completer = _BmyPathShellComplete
path_executor = _BmyExecutableShellComplete
local_path_completer = _LocalPathShellComplete
local_path_executor = _LocalExecutableShellComplete

click_completer = _ClickCompleter
