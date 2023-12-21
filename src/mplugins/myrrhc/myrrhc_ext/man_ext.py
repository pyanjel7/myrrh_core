import importlib
import os
import sys
import click
from click.decorators import pass_context
import pdoc
import pathlib
import webbrowser


from myrrh.core.services import cfg_get

from myrrh.tools.myrrhc_ext import myrrhc_cmds, cmd

from myrrh.tools.myrrhc.__doc__ import alias

pdoc.render.configure(docformat="restructuredtext")


def man_complete(_ctx, _cli, _incomplet):
    return list(alias())


@myrrhc_cmds.command()
@cmd.argument("alias_or_module_name", required=False, default="", shell_complete=man_complete)
@cmd.argument("sub_commands", required=False, nargs=-1)
@cmd.option(
    "-f",
    "--force-build",
    is_flag=True,
    required=False,
    default=cmd.option_cfg_default("man_always_rebuild", False),
)
@cmd.option(
    "-d",
    "--directory",
    required=False,
    default=cmd.option_cfg_default("man_dir", os.path.join(cfg_get(key="@etc@")[0], "man")),
)
@pass_context
def man(ctx: click.Context, alias_or_module_name, force_build, sub_commands, directory):
    """
    Display help information about a command or a python module.
    """
    _tmpdir = pathlib.Path(directory)

    if not alias_or_module_name:
        alias_or_module_name = "myrrh"

    module_name = alias().get(alias_or_module_name, alias_or_module_name)
    module_name, _, qualname = alias().get(alias_or_module_name, alias_or_module_name).partition("#")

    if qualname:
        alias_or_module_name = module_name
        module_name = alias().get(alias_or_module_name, alias_or_module_name)

    tmpdir = _tmpdir.joinpath(module_name)
    os.makedirs(tmpdir, exist_ok=True)
    index = tmpdir.joinpath("index.html")

    if not os.path.exists(index) or force_build:
        docs = {}
        try:
            mod = importlib.import_module(f"{module_name}.__doc__")

            if hasattr(mod, "__doc__"):
                o = type(sys)(alias_or_module_name)
                o.__doc__ = mod.__doc__() if callable(mod.__doc__) else mod.__doc__
                o.__doc__ = o.__doc__.replace("_main_", alias_or_module_name)
                docs[alias_or_module_name] = pdoc.doc.Module(o)
                docs[alias_or_module_name].is_package = True

            if hasattr(mod, "__docgen__"):
                for name, txt in mod.__docgen__().items():
                    o = type(sys)(name)
                    o.__doc__ = txt.replace("_main_", name.split(".")[-1])
                    docs[f"{alias_or_module_name}.{name}"] = pdoc.doc.Module(o)

        except (ModuleNotFoundError, RuntimeError):
            docs = {module_name: pdoc.doc.Module.from_name(module_name)}

        for name, doc in docs.items():
            out = pdoc.render.html_module(module=doc, all_modules=docs)
            outfile = tmpdir / f"{name.replace('.', '/')}.html"
            outfile.parent.mkdir(parents=True, exist_ok=True)
            outfile.write_bytes(out.encode())

        index = pdoc.render.html_index(docs)
        if index:
            (tmpdir / "index.html").write_bytes(index.encode())

        search = pdoc.render.search_index(docs)
        if search:
            (tmpdir / "search.js").write_bytes(search.encode())

    if qualname:
        webbrowser.open(str(tmpdir / f"{alias_or_module_name.replace('.', '/')}" / f"{'/'.join((qualname.replace('.', '/'), *sub_commands))}.html"))
        return

    webbrowser.open(str(tmpdir / "index.html"))
