import click
import pprint


class _F:
    from myrrh.core.services import cfg_get, cfg_set, cfg_del  # type: ignore[misc]

    @staticmethod
    def dump(key, value, section, overwrite):
        return pprint.pformat(_F.cfg_get(key, section=section))

    @staticmethod
    def rm(key, value, section, overwrite):
        to_delete = _F.dump(key, value=value, section=section, overwrite=overwrite)
        to_delete = to_delete[:200] + " ..." if len(to_delete) >= 200 else to_delete
        if not overwrite:
            click.echo("the following code will be deleted from the myrrh config")
            click.echo("--")
            click.echo(to_delete)
            click.echo("--")
            if not click.confirm("Do you want to continue?"):
                return "Aborted !"

        _F.cfg_del(key, section=section)
        return f"{key}={to_delete} deleted"


__all__ = ["cfg"]


def _confirm_cbk(ctx, param, value):
    if value == "rm":
        _d = {p.name: p for p in ctx.command.params}
        print(dir(_d.get("section")))
        print(_d)
        if not click.confirm("Do you want to continue?"):
            ctx.abort()

    return param


@click.option("--dump", "action", flag_value="dump", default=True)
@click.option("--set", "action", flag_value="cfg_set", default=False)
@click.option("--rm", "action", flag_value="rm", default=False)
@click.option("-k", "--key", type=str, default="")
@click.option("-s", "--section", type=str, default="")
@click.option("-f", "--force", is_flag=True, default=False)
@click.option("-v", "--value", default="")
def cfg(action, key, section, force, value):
    if action:
        click.echo(getattr(_F, action)(key, value=value, section=section, overwrite=force))


if __name__ == "__main__":
    click.command(cfg)()
