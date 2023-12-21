import click
from click.core import Group
from .cmd import myrrhc_cmds

__all__ = ["__doc__", "HelpFormatter"]


class HelpFormatter(click.HelpFormatter):
    """This class helps with formatting text-based help pages.  It's
    usually just needed for very special internal cases, but it's also
    exposed so that developers can write their own fancy outputs.

    At present, it always writes into memory.

    :param indent_increment: the additional increment for each level.
    :param width: the width for the text.  This defaults to the terminal
                  width clamped to a maximum of 78.
    """

    def write_usage(self, prog: str, args: str = "", prefix=None) -> None:
        """Writes a usage line into the buffer.

        :param prog: the program name.
        :param args: whitespace separated list of arguments.
        :param prefix: The prefix for the first line. Defaults to
            ``"Usage: "``.
        """
        if prefix is None:
            prefix = "Usage"

        # The prefix is too long, put the arguments on the next line.
        self.write_heading(prefix)
        self.write(f"{prog} ")
        self.write(args)
        self.write("\n")

    def write_heading(self, heading: str) -> None:
        self.write(f"{'':>{self.current_indent}}{heading}\n---\n")

    def write_dl(
        self,
        rows,
        col_max: int = 30,
        col_spacing: int = 2,
    ) -> None:
        """Writes a definition list into the buffer.  This is how options
        and commands are usually formatted.

        :param rows: a list of two item tuples for the terms and values.
        :param col_max: the maximum width of the first column.
        :param col_spacing: the number of spaces between the first and
                            second column.
        """
        rows = list(rows)
        widths = click.formatting.measure_table(rows)
        if len(widths) != 2:
            raise TypeError("Expected two columns for definition list")

        self.write('<table border="1" cellpadding="8">')
        for first, second in click.formatting.iter_rows(rows, len(widths)):
            self.write("<tr>")

            if not first.startswith("-"):
                self.write(f'<th><a href="_main_/{first}.html">{first}</a></th>')
            else:
                self.write(f"<th>{first}</th>")

            if not second:
                self.write("</tr>")
                continue
            lines = second.splitlines()

            if lines:
                self.write(f"<td>{lines[0]}</td>")

                for line in lines[1:]:
                    self.write(f"<td>{line}</td>")

            self.write("</tr>")
        self.write("</table>")


def __doc__():  # type: ignore[no-redef]
    ctx = myrrhc_cmds.make_context("myrrhc", ["$"], None, resilient_parsing=True)
    formatter = HelpFormatter()
    ctx.command.format_help(ctx, formatter)

    return formatter.getvalue()


_alias = {"commands": "myrrh.tools.myrrhc"}


def alias():
    _alias.update({cmdname: f"commands#{cmdname}" for cmdname in myrrhc_cmds.commands.keys() if not cmdname.startswith("-")})

    return _alias


def register_alias(alias_dict):
    _alias.update(alias_dict)


def __docgen__(cmdname=None, group=myrrhc_cmds):
    ctx = group.make_context("myrrhc", ["$"], None, resilient_parsing=True)
    cmdnames = [cmdname] if cmdname else [cmdname for cmdname in group.commands.keys() if not cmdname.startswith("-")]

    result = dict()
    for cname in cmdnames:
        cmd = group.get_command(ctx, cname)
        sub_ctx = cmd.make_context(cname, [cname], ctx, resilient_parsing=True)
        formatter = HelpFormatter()
        sub_ctx.command.format_help(sub_ctx, formatter)
        result[cname] = formatter.getvalue()

        if isinstance(cmd, Group):
            for k, txt in __docgen__(group=cmd).items():
                result[f"{cname}.{k}"] = txt

    return result
