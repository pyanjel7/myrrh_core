import pprint
import click

__all__ = ["secret", "password"]


class _F:
    from myrrh.utils.secrets import set_key, clean_all_keys, clean_key_history, dump, backup_key, delete_key, use_key, rename_key, encrypt, decrypt  # type: ignore[misc]

    @classmethod
    def new_password(cls):
        click.password_option


def pecho(s, *a, **kwa):
    click.echo(pprint.pformat(s), *a, **kwa)


@click.option("-c", "--clean-history", "clean", flag_value="clean_key_history", default=False)
@click.option("--clean-all", "clean", flag_value="clean_all_keys", default=False)
@click.option("-d", "--dump", "dump", is_flag=True, default=False)
@click.option("-g", "--gen-key", "gen", is_flag=True, default=False)
@click.option("-f", "--force", is_flag=True, default=False)
@click.option("-b", "--backup-key", type=str, default=None)
@click.option("--delete-key", type=str, default=None)
@click.option("--rename-key", nargs=2, type=str, default=None)
@click.option("-u", "--use-key", type=str, default=None)
def secret(gen, clean, dump, backup_key, force, delete_key, use_key, rename_key):
    if clean:
        getattr(_F, clean)()

    if delete_key:
        _F.delete_key(delete_key)

    if rename_key:
        _F.rename_key(*rename_key)

    if backup_key:
        _F.backup_key(backup_key, overwrite=force)

    if gen:
        _F.set_key()

    if use_key:
        _F.use_key(use_key)

    if dump:
        pecho(_F / dump())


def prompt_password(ctx, param, value):
    if value == "-":
        value = click.prompt("New", hide_input=True, show_choices=False, confirmation_prompt=True)
    return value


@click.option(
    "-c",
    "encrypt",
    type=str,
    default="",
    callback=prompt_password,
    help="encrypt the given string",
)
@click.option("-d", "decrypt", type=str, default="", help="decrypt the given string")
@click.option("-k", "key", type=str, default="key")
def password(encrypt, decrypt, key):
    if encrypt:
        print(_F.encrypt(encrypt, key))
    if decrypt:
        print(_F.decrypt(decrypt, key))


if __name__ == "__main__":

    @click.group
    def main():
        ...

    main.command(secret)
    main.command(hash)

    main()
