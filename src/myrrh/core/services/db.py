import os
import pathlib
import json
import typing
import difflib
import hashlib
import importlib.resources

import tinydb
import tinydb.middlewares

from tinydb import where

from myrrh.core.interfaces import IERegistry
from myrrh.core.services.config import cfg_get, cfg_init


path = cfg_get(key="@etc@")
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

                document["@registry@"] = dict()
                for item in document["items"]:
                    type_ = item.get("type_")
                    if type_:
                        document["@registry@"][type_] = item

                id_ = create_id(document["@registry@"])
                if id_:
                    document["@id@"] = id_

                document["@file@"] = fpath.name
                document["@md5@"] = self._hash(data)
                document["@access@"] = access

            doc_id = db.table(table).insert(document)
            
            for d in document["@registry@"].values():
                d["@tinydb.doc_id"] = doc_id

        return document

    def _read_default(self):
        db = tinydb.TinyDB(storage=tinydb.storages.MemoryStorage)

        try:
            resource = importlib.resources.files("myrrh.resources.db.warehouse")
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


def reload(force_flush: bool = True):
    global myrrhdb

    if force_flush:
        flush()

    myrrhdb = tinydb.TinyDB(path, storage=tinydb.middlewares.CachingMiddleware(_MyrrhStorage))

    myrrhdb.storage.read()


def flush():
    if myrrhdb is not None:
        myrrhdb.storage.flush()


def create_id(registry: dict, data: dict | None = None, type: str | None = None):
    id_ = data if type == "id" else registry.get("id") or dict()
    system_ = data if type == "system" else registry.get("system") or dict()

    return {
        "uuid": id_.get("uuid"),
        "os": system_.get("os"),
        "label": system_.get("label"),
        "tags": [t for item in registry.values() for tags in (item.get("tags") or list()) for t in tags.split(";")],
    }


def search_by(name, value):
    if value is None:
        return []

    return myrrhdb.table("emyrrh").search(where("@id@")[name] == value)


def best_match(docs, name: str, value: str):

    if not value:
        return

    value = value.lower()

    seq = {}
    for d in docs:
        dvalue = d["@id@"].get(name)
        if dvalue:
            dvalue.lower()
            seq[difflib.SequenceMatcher(None, value, dvalue).ratio()] = d

    v = max(seq)

    return seq[v]


def search(registry: IERegistry, data: dict, type: str):

    doc_id = registry.get_meta("@tinydb.doc_id")
    if doc_id:
        return myrrhdb.table("emyrrh").get(doc_id=doc_id)["@registry@"].get(type)

    id_ = create_id(registry, data, type)

    docs = search_by("uuid", id_["uuid"])
    if docs:
        return docs[0]['@registry@'].get(type)

    docs = search_by("os", id_["os"])

    if docs:
        doc = best_match(docs, "label", id_["label"])
        return doc['@registry@'].get(type)


myrrhdb = None
reload()
