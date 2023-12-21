__all__ = ("MyrrhEnviron",)


class MyrrhEnviron:
    class _itemsview:
        def __init__(self, myrrh_environ):
            self.__myrrh_environ = myrrh_environ
            self.__it = iter(myrrh_environ)

        def __iter__(self):
            return self

        def __next__(self):
            k = next(self.__it)
            return k, self.__myrrh_environ[k]

    class _valuesview:
        def __init__(self, myrrh_environ):
            self.__myrrh_environ = myrrh_environ
            self.__it = iter(myrrh_environ)

        def __iter__(self):
            return self

        def __next__(self):
            return self.__myrrh_environ[next(self.__it)]

    class _keysview:
        def __init__(self, myrrh_environ):
            self.__myrrh_environ = myrrh_environ
            self.__it = iter(myrrh_environ._env)

        def __iter__(self):
            return self

        def __next__(self):
            result = next(self.__it)
            while result in self.__myrrh_environ._filter:
                result = next(self.__it)
            return self.__myrrh_environ._conv(result)

    def __init__(self, env, *, conv=None, keyformat=None, filter=[]):
        self.__env = env

        self._conv = conv or (lambda k: k)
        self._kfmt = (lambda k: self._conv(keyformat(k))) if keyformat else conv

        self.__filter = [self._kfmt(k) for k in filter]

    def __repr__(self):
        return "environ(%s)" % repr({k: v for k, v in self.items()})

    @property
    def _env(self):
        return self.__env

    @property
    def _filter(self):
        return self.__filter

    def __eq__(self, environ):
        return {k: v for k, v in self.items()} == {self._kfmt(k): self._conv(v) for k, v in environ.items()}

    def __setitem__(self, key, value):
        self._env[self._kfmt(key)] = value

    def __getitem__(self, key):
        try:
            return self._conv(self._env[self._kfmt(key)])
        except KeyError:
            raise KeyError(key) from None

    def __delitem__(self, key):
        try:
            del self._env[self._kfmt(key)]
        except KeyError:
            raise KeyError(key) from None

    def __iter__(self):
        return iter(self._keysview(self))

    def __contains__(self, key):
        return self._env.__contains__(self._kfmt(key))

    def __len__(self):
        return self._env.__len__()

    def __str__(self):
        return self._env.__str__()

    def clear(self):
        self._env.clear()

    def copy(self):
        return MyrrhEnviron(self._env.copy(), conv=self._conv, keyformat=self._kfmt, filter=self._filter)

    def get(self, key, default=None):
        return self._conv(self._env.get(self._kfmt(key), default))

    def items(self):
        return self._itemsview(self)

    def keys(self):
        return self._keysview(self)

    def values(self):
        return self._valuesview(self)

    def pop(self, key, *args, **kwargs):
        if len(kwargs) > 1 or len(args) > 1:
            raise ValueError("pop is called with too many arguments")

        try:
            default = args[0] if len(args) > 0 else kwargs.pop("default")
            return self._conv(self._env.pop(self._kfmt(key), self._conv(default)))
        except KeyError:
            return self._conv(self._env.pop(self._kfmt(key)))

    def popitem(self):
        k, v = self._env.popitem()
        return self._conv(k), self._conv(v)

    def setdefault(self, key, default=None):
        return self._conv(self._env.setdefault(self._kfmt(key), self._conv(default)))

    def update(self, other={}, **kwargs):
        kwargs.update(other)
        for k, v in kwargs.items():
            self._env.update({self._kfmt(k): self._conv(v)})
