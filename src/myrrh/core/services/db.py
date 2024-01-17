import os
import pathlib
import json
import typing
import tinydb
import tinydb.middlewares

import hashlib
import importlib.resources

from .config import cfg_get, cfg_init

path = cfg_get(key="@etc@")[0]
path = cfg_init("dbpath", os.path.join(path, "db"), "myrrh.core.services.db")

__all__ = ["myrrhdb", "reload", "flush"]


class _MyrrhStorage(tinydb.Storage):
    def __init__(self, path, db="emyrrh") -> None:
        self.path = pathlib.Path(path) / db
        self.db = db
        self.memory = None

        self.path.mkdir(parents=True, exist_ok=True)

        if not self.path.is_dir():
            raise NotADirectoryError("invalid database storage path")

    def write(self, data: typing.Dict[str, typing.Dict[str, typing.Any]]) -> None:
        for table, documents in data.items():
            for document in documents.values():
                document_f = {k: v for k, v in document.items() if not k.startswith("@")}
                if "w" in document.get("@access@", ""):
                    document_f = {k: v for k, v in document.items() if not k.startswith("@")}
                    data = json.dumps(document_f, indent=2).encode()
                    hash = self._hash(data)
                    if document.get("@md5@") != hash:
                        name = document.get("@file@", hash)
                        (self.path / table).mkdir(parents=True, exist_ok=True)
                        (self.path / table / name).write_bytes(data)

        self.memory = None

    def _hash(self, data):
        return hashlib.md5(data).hexdigest()

    def _itertable(self, path: pathlib.Path, db: tinydb.TinyDB, table: str | None = None, access: str = "rw") -> typing.Dict[str, typing.Dict[str, typing.Any]]:
        table = table or path.name

        for p in path.iterdir():
            if p.is_dir():
                return self._itertable(p, db, table)

            with importlib.resources.as_file(p) as fpath:
                data = fpath.read_bytes()
                document = json.loads(data)
                document["@file@"] = fpath.name
                document["@md5@"] = self._hash(data)
                document["@access@"] = access

            db.table(table).insert(document)

        return document

    def _read_default(self):
        db = tinydb.TinyDB(storage=tinydb.storages.MemoryStorage)

        try:
            resource = importlib.resources.files(f"myrrh.resources.db.{self.db}")
        except ModuleNotFoundError:
            return db

        for d in resource.iterdir():
            self._itertable(d, db, access="ro")

        return db

    def read(self) -> typing.Dict[str, typing.Dict[str, typing.Any]] | None:
        if self.memory is None:
            db = self._read_default()

            for d in self.path.iterdir():
                self._itertable(d, db)

            self.memory = db.storage.memory

        return self.memory


def reload(flush: bool = True):
    global myrrhdb

    if flush:
        flush()

    myrrhdb = tinydb.TinyDB(path, storage=tinydb.middlewares.CachingMiddleware(_MyrrhStorage))


def flush():
    if myrrhdb is not None:
        myrrhdb.storage.flush()


myrrhdb = None
reload()
