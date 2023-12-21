import queue

from concurrent.futures import ThreadPoolExecutor
import weakref

from ...interfaces import ITask, IRuntimeObject
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


class RuntimeTaskManager(ThreadPoolExecutor):
    def __init__(self, max_pool_size, eid):
        self.name = f"@{eid}:"
        super().__init__(max_pool_size, self.name)

        self._work_queue = _WorkQueue(self)
        self._tasks = weakref.WeakValueDictionary()

    def append(self, *objs: IRuntimeObject):
        for obj in objs:
            if isinstance(obj, ITask):
                task = RuntimeTask(obj, self)  # type: ignore[arg-type]

                ehandle = getattr(obj, "ehandle", -1)
                if ehandle > 0:
                    self._tasks[obj.ehandle] = task

                super().submit(task)  # type: ignore[arg-type]

    def tget(self, ehandle: int) -> RuntimeTask:
        return self._tasks.get(ehandle)
