import click
import sys
import os

import myrrh.factory
import pprint

__all__ = ["json"]


class _F:
    @staticmethod
    def dump_schema(factory):
        return factory.schema(indent=2)

    @staticmethod
    def dump_json(factory):
        if isinstance(factory, myrrh.factory.Assembly):
            return factory.json(indent=2)

    @staticmethod
    def dump_obj(factory):
        if isinstance(factory, myrrh.factory.Assembly):
            return factory.pformat()

    @staticmethod
    def dump_dict(factory):
        if isinstance(factory, myrrh.factory.Assembly):
            return pprint.pformat(factory.dict())


@click.option("-o", "--dump-obj", "dump", flag_value="dump_obj", default=False)
@click.option("-d", "--dump-dict", "dump", flag_value="dump_dict", default=False)
@click.option("-s", "--dump-schema", "dump", flag_value="dump_schema", default=True)
@click.option("-j", "--dump-json", "dump", flag_value="dump_json", default=False)
@click.option("-l", "--load", type=str, default="")
@click.option("-e", "--export", type=str, default="")
@click.option("-y", "--yes", is_flag=True, default=False)
def json(dump, load, export, yes):
    try:
        Factory = myrrh.factory.Assembly

        if load:
            Factory = myrrh.factory.Assembly.fromFile(load)

        try:
            CONT = True

            if export == "-":
                export = load

            CONT = not export or not os.path.exists(export) or yes or click.confirm(f"{export} file exist, overwrite?")

            if CONT and export:
                export = open(export, "w")

            if CONT and dump:
                click.echo(getattr(_F, dump)(Factory), file=export or sys.stdout)

        finally:
            if CONT and export:
                export.close()

    except Exception as e:
        raise
        click.echo(e, err=True)


if __name__ == "__main__":
    json("dump_schema", "", "", False)
