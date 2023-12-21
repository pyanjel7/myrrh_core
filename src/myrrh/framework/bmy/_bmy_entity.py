import threading

from myrrh import factory
from myrrh.core.services import groups
from myrrh.framework import Runtime

from ._bmy_exceptions import BmyNotReady


class BmyEntity:
    def __init__(self, assembly: factory.Assembly, eid: str):
        self._assembly = assembly
        self._eid = eid
        self._entity = None
        self._runtime = None
        self._used: list[int] = list()

    def __str__(self) -> str:
        return self._eid

    def build(self):
        if not self._entity:
            self._entity = self._assembly.build()

        return self._entity

    @property
    def eid(self):
        return self._eid

    @property
    def cfg(self):
        if not self.built:
            raise BmyNotReady(self._eid)

        return self._entity.cfg

    @property
    def system(self):
        if not self.built:
            raise BmyNotReady(self.eid)

        return self._entity.system

    @property
    def host(self):
        if not self.built:
            raise BmyNotReady(self.eid)

        return self._entity.host

    @property
    def vendor(self):
        if not self.built:
            raise BmyNotReady(self.eid)

        return self._entity.vendor

    @property
    def runtime(self):
        if not self._runtime:
            self._runtime = Runtime(self._entity.system)

        return self._runtime

    @groups.myrrh_group_sync_member
    def release(self):
        try:
            self._used.remove(threading.get_ident())
        except ValueError:
            pass

    @groups.myrrh_group_sync_member
    def acquire(self):
        self._used.append(threading.get_ident())

    @property
    def built(self):
        return self._entity is not None

    @property
    def used(self):
        return len(self._used) != 0
