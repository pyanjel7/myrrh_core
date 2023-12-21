import bmy
import os

from myrrh.core.services import cfg_init

__all__ = ("setUp", "setUpModule", "tearDownModule")

test_path = cfg_init("testdir", ".myrrh_tests", section="tests")

_eid: str | None = None
_name: str | None = None
_local_prev_cwd: str | None = None


def setUpModule():
    init(_name, eid=_eid)


def tearDownModule():
    try:
        clean(_name, eid=_eid)
    except Exception:
        ...


def setUp(name, eid=None):
    global _eid, _name
    _eid = eid
    _name = name

    if not _eid:
        # by default, we use local entity
        _eid = bmy.new("**/local", eid=f"test_{name}")

    bmy.build(eid=_eid)


def init(name, *, eid):
    global _local_prev_cwd, test_path

    @bmy.bmy_func()
    def init_entity(name, *, eid):
        bmy.build(eid=eid)

        with bmy.select(eid):
            path = bmy.joinpath(test_path, name, eid)
            bmy.mkdir(path)
            prev, _ = bmy.chdir(path)
            bmy.setinfo("myrrh_test", prev_path=prev)

    local_path = os.path.join(test_path, name, "local")
    os.makedirs(local_path, exist_ok=True)
    _local_prev_cwd = os.getcwd()
    os.chdir(local_path)

    if not eid:
        # by default, we use local entity
        eid = bmy.new("**/local", eid=f"test_{name}")

    init_entity(name, eid=eid)


def clean(name, *, eid):
    @bmy.bmy_func()
    def clean_entity(*, eid):
        os.chdir(_local_prev_cwd)

        with bmy.select(eid):
            prev_path = bmy.info("myrrh_test.prev_path")
            current, _ = bmy.chdir(prev_path)
            bmy.rmdir(current, force=True)

    clean_entity(eid=eid)

    local_path = os.path.join(test_path, "local", name)
    os.remove(local_path)
