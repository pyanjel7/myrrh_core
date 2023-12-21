import collections
import weakref
import threading

from functools import wraps

from myrrh.core.services import groups, cfg_init
from myrrh.core.services.logging import log

from ._bmy_exceptions import BmyInvalidEid, BmyEidInUsed
from ._bmy_entity import BmyEntity

__all__ = ["init"]


def _dispatch_on_eid_type(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        eid = kwargs.get("eid")

        if entities.isgroup(eid):
            kwargs["eid"] = groups.MyrrhGroup(keys=eid)
            return groups.myrrh_group(func)(*args, **kwargs)

        return func(*args, **kwargs)

    return wrapper


_histories: dict[int, object] = weakref.WeakValueDictionary()  # type: ignore[assignment]


def _get_thread_history(ident=None):
    ident = ident or threading.get_ident()
    return _histories.get(ident) or _BmyEntities._thread_locals.history


class _BmyHistoryCollection(collections.deque):
    def __init__(self, *a, **kwa):
        super().__init__(*a, **kwa)
        self.pos = 0
        self.n = 0
        _histories[threading.get_ident()] = self

    def inc(self):
        return min(self.pos + 1, self.n)

    def dec(self):
        return max(self.pos - 1, 0)

    def get_current(self):
        return self[self.pos]

    def get_next(self):
        return self[self.inc()]

    def get_previous(self):
        return self[self.dec()]

    def goto_next(self):
        self.pos = self.inc()
        return self.get_current()

    def goto_previous(self):
        self.pos = self.dec()
        return self.get_current()

    def push(self, value):
        self.n = self.pos + 1
        self.n = self.n % self.maxlen
        if not self[self.pos] is None:
            self.pos = self.inc()
        self[self.pos] = value


class _BmyEntitiesLocal(threading.local):
    _HISTORY_SZ = cfg_init("history_size", 20, section="myrrh.framework.bmy")

    def __init__(self):
        self.history = _BmyHistoryCollection((None,) * (self._HISTORY_SZ), maxlen=self._HISTORY_SZ)


class _BmyEntities:
    _entities: dict[str, BmyEntity] = {}
    _lock_entities = threading.RLock()
    _HISTORY_SZ = cfg_init("history_size", 20, section="myrrh.framework.bmy")

    _thread_locals = _BmyEntitiesLocal()

    def __init__(self, entities=[]):
        with self._lock_entities:
            for e in entities:
                self.append(e)

    @property
    def history(self):
        return self._thread_locals.history

    @property
    def eids(self):
        """
         Copy of current entity id list

        :type: list(str)
        """
        with self._lock_entities:
            return list(self._entities.keys())

    @property
    def entities(self):
        """
         Copy of current entity list

        :getter: return the current entity id list
        :type: list(:class:`myrrh.core.Entity`)
        """
        with self._lock_entities:
            return list(self._entities.values())

    @property
    def eid(self):
        """
         Default entity id

        :return: entity id
        :rtype: str
        """
        return self.history.get_current()

    @eid.setter
    def eid(self, eid):
        """
         Set the default entity eid

        :setter str eid: entity id

        :raises BmyInvalidEid: on unknown entity
        """
        if self.isgroup(eid):
            eid = groups.myrrh_group_keys(eid)

        with self._lock_entities:
            if self.eid:
                self.get(eid=self.eid).release()

            # history[i] = next eid

            self.history.push(str(eid) if isinstance(eid, BmyEntity) else eid)

            if self.eid:
                entities = self.get(eid=self.eid)
                entities.acquire()

        log.debug(f"bmy new entity selected {str(self.eid)}")

    @groups.myrrh_group_sync_member
    def eid_(self, ident=None):
        return _get_thread_history(ident).get_current()

    @groups.myrrh_group_sync_member
    def append(self, assembly, eid):
        bmy_entity = BmyEntity(assembly, eid)

        with self._lock_entities:
            self._entities[eid] = bmy_entity

            if len(self._entities) == 1 or self.eid == bmy_entity.eid:
                # select or reselect entity
                self.eid = bmy_entity.eid

        return bmy_entity.eid

    @_dispatch_on_eid_type
    @groups.myrrh_group_sync_member
    def remove(self, *, eid):
        with self._lock_entities:
            entity = self.get(eid)

            if entity.used:
                raise BmyEidInUsed(eid, msg='can not remove entity "%s", the entity is in used' % eid)

            self._entities.pop(eid, None)

    @_dispatch_on_eid_type
    @groups.myrrh_group_sync_member
    def get(self, *, eid) -> BmyEntity:
        with self._lock_entities:
            if eid is not None and eid not in self._entities:
                raise BmyInvalidEid(eid)

            if eid is None:
                eid = self.eid

            if eid is None:
                raise BmyInvalidEid(eid)

            return self._entities[eid]

    @groups.myrrh_group_sync_member
    def __getitem__(self, eid) -> BmyEntity:
        """
         x[eid] <=> x.__getitem__(eid)

        :param str eid: entity id
        :raises:class:`myrrh.framework.bmy.BmyInvalidEid`: on unknown entity
        """
        return self.get(eid=eid)

    @groups.myrrh_group_sync_member
    def current(self, eid=None, ident=None):
        if eid:
            if isinstance(eid, BmyEntity):
                return eid.eid

            try:
                self[eid]  # raises on invalid eid
            except BmyInvalidEid:
                return
            else:
                return eid

        if eid is None:
            eid = self.eid_(ident)
            if eid is not None and self.isgroup(eid) and len(eid) == 1:
                return groups.myrrh_group_keys(eid)[0]
            return eid

        if self.isgroup(eid):
            eid = self.eid_(ident)

            if not eid:
                return ()

            if not self.isgroup(eid):
                return groups.MyrrhGroup(eid, keys=(eid,))

            return eid

        return self.eid_(ident)

    @groups.myrrh_group_sync_member
    def isgroup(self, eid=None):
        if eid is None:
            eid = self.current(eid)  # avoid infinite recursion with current
        return groups.is_myrrh_group(eid) or isinstance(eid, (tuple, list))

    @groups.myrrh_group_sync_member
    def groupkeys(self, group):
        if self.isgroup(group):
            return groups.myrrh_group_keys(group)

        return (group,)

    @groups.myrrh_group_sync_member
    def groupvalues(self, group):
        if self.isgroup(group):
            return groups.myrrh_group_values(group)

        return (group,)


def init(_entities=[]):
    """
    Initialize/reset bmy entity manager

    Args:
        entities (dict): dictionary { id(str): entity(:class:`myrrh.core.entity.Entity`), ... } of already defined entities

    Note:
        this method is automatically called when the bmy module is loaded

    """
    global entities
    entities = _BmyEntities(_entities)


####

entities: _BmyEntities = None  # type: ignore[assignment]
init()
