import re

from myrrh.utils import mshlex

from myrrh.core.services import cfg_init, cfg_get, cfg_del, cfg_set

from myrrh.tools.myrrhc_ext import myrrhc_cmds, cmd, getsession


cfg_init(
    "asetcfg",
    "setcfg --section myrrh.tools.myrrhc.alias",
    section="myrrh.tools.myrrhc.alias",
)


def _alias_cmd(name, value):
    args = list()
    nargs = len(re.split(r"{\d*}", value)) - 1
    for n in range(0, nargs):
        args.append(cmd.Argument((f"arg{n}",), required=True))

    if not nargs:
        nkwargs = re.findall(r"\{([a-zA-Z_]\w*)\}", value)
        for arg in nkwargs:
            args.append(cmd.Argument((arg,), required=True))

    @myrrhc_cmds.command(name=name)
    def _(**kwargs):
        f"""
        Alias for "{value}"
        """

        async def _():
            if nargs:
                cmdline = value.format(*kwargs.values())

            elif nkwargs:
                cmdline = f"{value} {mshlex.list2cmdlines(**kwargs)}"

            else:
                cmdline = f"{value}"

            return await getsession().command_call(cmdline)

        return _

    _.params.extend(args)
    _.help = f'Alias for "{value}"'


@myrrhc_cmds.command()
@cmd.argument("alias_name")
@cmd.argument("alias_value", default=None, required=False)
def alias(alias_name, alias_value):
    """
    Create an command alias
    """
    if alias_value is None:
        cfg_del(alias_name, section="myrrh.tools.myrrhc.alias")
        myrrhc_cmds.commands.pop(alias_name)
    else:
        cfg_set(alias_name, alias_value, section="myrrh.tools.myrrhc.alias")

    _reload()


@myrrhc_cmds.command()
def areload():
    """
    Reload all alias
    """
    _reload()


def _reload():
    for name, value in cfg_get(section="myrrh.tools.myrrhc.alias").items():
        _alias_cmd(name, value)


_reload()
