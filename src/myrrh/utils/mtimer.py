import time
import typing


class MTimer:
    class DelayExpired(TimeoutError):
        timer: typing.Optional["MTimer"] = None

    class CountExpired(TimeoutError):
        timer: typing.Optional["MTimer"] = None

    INFINITE = -1

    def __init__(self, timeout=None, count=None, step=None, raise_on_expired=False):
        """
        Create simple synchronous timer

        :param int timeout: timer expiration in second
        :param in count: timer expiration in discrete time count
        """
        self._count = count
        self._timeout = timeout
        self._step_sleep_time = step
        self._raise_on_expired = raise_on_expired

        self._idle_endtime = 0

        self.reset()

    def __enter__(self):
        self.reset()
        return self

    def __exit__(self, *_a, **_k):
        self.stop()

    def __bool__(self):
        return self.idle

    @property
    def _timeleft(self):
        return self._timeout is None or self._timeout and max(0, self._timeout - self.duration)

    @property
    def _countleft(self):
        return self._count is None or self._count == self.INFINITE or self._count and max(0, self._count - self._nbstep)

    @property
    def duration(self):
        _time = self._endtime or self._ctime
        return _time - self._starttime

    @property
    def count(self):
        return self._count

    @property
    def timeout(self):
        return self._timeout

    @property
    def step(self):
        return self._step_sleep_time

    @property
    def cstep(self):
        return self._nbstep

    @property
    def starttime(self):
        return self._starttime

    @property
    def endtime(self):
        return self._endtime

    @property
    def expired(self):
        return self._nbstep > 0 and (self._endtime or not self._timeleft or not self._countleft)

    @property
    def expired_on_count(self):
        return self._count and not self._countleft

    @property
    def expired_on_timeout(self):
        return self._timeout and not self._timeleft

    @property
    def idle(self):
        self._nbstep += 1

        if self.expired:
            self.stop()
            if self._raise_on_expired:
                expired = TimeoutError()
                if not self._count and not self._timeout:
                    expired = self.CountExpired()
                elif self.expired_on_timeout:
                    expired = self.DelayExpired()
                elif self.expired_on_count:
                    expired = self.CountExpired()
                else:
                    expired = TimeoutError()
                expired.timer = self
                raise expired
            else:
                return False
        if self._step_sleep_time:
            time.sleep(self.sleep_time)

        self._idle_endtime = self._ctime

        return True

    @property
    def sleep_time(self):
        if self._step_sleep_time:
            return min(self._step_sleep_time, self._timeleft) if self._timeout else self._step_sleep_time

    @property
    def timeleft(self):
        if self._timeout is not None:
            return self._timeleft

        # None

    @property
    def countleft(self):
        if self._count is not None:
            return self._countleft

        # None

    def reset(self):
        self._starttime = self._ctime
        self._nbstep = 0
        self._endtime = None

    def stop(self):
        self._endtime = self._ctime

    @property
    def _ctime(self):
        return time.monotonic()


class MVectorTimer(MTimer):
    def __init__(self, vectors, *a, **kw):
        super().__init__(*a, **kw)
        self._vectors = list(vectors)
        self._stamp = 0

    @property
    def sleep_time(self):
        vector = int((self.duration - self._stamp) / self._step_sleep_time)
        wait = self._vectors[min(len(self._vectors) - 1, vector)]
        return wait

    def stamp(self):
        self._stamp = self.duration


class MBurstTimer(MVectorTimer):
    _VECTOR = [0.01] * 10 + [0.1] * 10 + [0.2] * 30 + [0.3] * 50 + [0.5] * 500 + [1]
    _STEP = 0.1

    def __init__(self, vectors=None, timeout=None, count=None, step=None, raise_on_expired=False):
        super().__init__(
            vectors=vectors and list(vectors) or self._VECTOR,
            timeout=timeout,
            count=count,
            step=step or self._STEP,
            raise_on_expired=raise_on_expired,
        )
