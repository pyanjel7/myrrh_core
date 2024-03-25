import queue

from concurrent.futures import ThreadPoolExecutor
import weakref

from ...interfaces import ITask, IRuntimeObject, IMyrrhOs, IRuntimeTaskManager, IERegistrySupplier
from ..objects import RuntimeTask

__all__ = ("RuntimeTaskManager",)


class _WorkQueue(queue.SimpleQueue):
    def __init__(self, manager):
        self.manager = manager
        super().__init__()

    def put(self, item, block=True, timeout=None) -> None:
        if item is None or isinstance(item, RuntimeTask):
            return super().put(item, block, timeout)

        return super().put(item.fn, block, timeout)


class RuntimeTaskManager(IERegistrySupplier, ThreadPoolExecutor, IRuntimeTaskManager):  # type: ignore[misc]
    def __init__(self, myrrh_os: IMyrrhOs, max_pool_size, eid):
        self.name = f"@{eid}:"
        self._reg = myrrh_os.reg  # type: ignore[misc]

        super().__init__(max_pool_size, self.name)

        self._work_queue = _WorkQueue(self)
        self._tasks: weakref.WeakValueDictionary[int, RuntimeTask] = weakref.WeakValueDictionary()

    @property
    def reg(self):
        return self._reg
    
    def append(self, *objs: IRuntimeObject):
        for obj in objs:
            if isinstance(obj, ITask):
                task = RuntimeTask(obj, self)

                ehandle = getattr(obj, "ehandle", -1)
                if ehandle > 0:
                    self._tasks[obj.ehandle] = task

                super().submit(task)  # type: ignore[arg-type]

    def tget(self, ehandle: int) -> RuntimeTask | None:
        return self._tasks.get(ehandle)
