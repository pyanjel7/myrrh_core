from myrrh.tools.myrrhc_ext import myrrhc_cmds, cmd
from myrrh.provider.registry import ProviderRegistry


@myrrhc_cmds.group()
def provider():
    "Provider management"
    pass


@provider.command()
def list():
    "List all installed providers"
    for name in sorted(ProviderRegistry().providers, key=lambda n: n[0]):
        cmd.info("%s\t\t%s" % (name, ProviderRegistry().get_version(name)))
