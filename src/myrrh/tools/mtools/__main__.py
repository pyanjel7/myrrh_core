import click

from myrrh.tools.mtools import cmds


@click.group()
def tools():
    ...


for cmd in cmds:
    tools.command(cmd)

tools()
