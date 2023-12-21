import typing
import click

import bmy


from myrrh.tools.myrrhc_ext import myrrhc_cmds, types, cmd
from myrrh.provider.registry import ProviderRegistry
from myrrh.warehouse.registry import ItemRegistry


@myrrhc_cmds.group()
def provider():
    "Provider management"
    pass


@provider.command(name="list")
def list_():
    "List all installed providers"
    for name in sorted(ProviderRegistry().providers, key=lambda n: n[0]):
        cmd.info("%s\t\t%s" % (name, ProviderRegistry().get_version(name)))


@provider.group()
def new():
    ...


for pname in sorted(ProviderRegistry().providers, key=lambda n: n[0]):

    def _(eid, pname=pname, **kw):
        eid = bmy.new(f"**/{pname}", eid=eid, **kw)
        bmy.select(eid)

    settings = ItemRegistry().provider_settings.get(pname)

    if settings:
        for field_name, field_info in settings.model_fields.items():
            if field_name != "name":
                types_ = [
                    a
                    for a in filter(
                        lambda t: not issubclass(t, None.__class__),
                        typing.get_args(field_info.annotation),
                    )
                ]

                if not types_:
                    type_ = field_info.annotation

                elif len(types_) == 1:
                    type_ = types_[0]

                else:

                    class Type_(click.ParamType):
                        name = f"{field_info.annotation}"
                        types_ = types_

                        def convert(self, value, param, ctx):
                            for t in self.types_:
                                try:
                                    return t(value)
                                except (TypeError, ValueError):
                                    pass

                            raise ValueError(f"invalid value for '{param}': '{value}' is not valid for '{self.name}' types")

                    type_ = Type_()
                nargs = typing.get_origin(field_info.annotation) and issubclass(typing.get_origin(field_info.annotation), (tuple, list))
                _ = cmd.option(
                    f"--{field_name}",
                    required=field_info.is_required(),
                    type=type_,
                    is_flag=type_ is bool,
                    multiple=nargs,
                    default=field_info.get_default(),
                    show_default=True,
                    help=field_info.description,
                )(_)

    _ = cmd.argument("eid", type=types.STRING)(_)
    new.command(name=pname)(_)
