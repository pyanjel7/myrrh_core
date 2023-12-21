from myrrh.provider.provider_ext import provider, cmd


@provider.group()
def local():
    ...


@local.command()
@cmd.option("--cwd", default=None, type=cmd.Path())
@cmd.argument("name")
def new(cwd, name):
    import bmy

    bmy.new("**/local", eid=name, cwd=cwd)
