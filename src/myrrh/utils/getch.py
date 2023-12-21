# -*- coding: utf-8 -*-

"""
**like c getch implementation **

.. note:: this module should not be used outside Myrrh library.

This module implements a delegation solution for abstract method delegation

-----------

"""
import threading

import time
from collections import deque
from prompt_toolkit.input.defaults import create_input
from prompt_toolkit.key_binding import KeyPress

import asyncio

__all__ = ["getchIt", "getch", "getche"]


class _getChPromptToolkit:
    _lock = threading.RLock()
    _keys: deque[KeyPress] = deque()
    _keyevt = threading.Condition(_lock)
    _reader: threading.Thread | None = None
    _emergency = False

    @classmethod
    def abort(cls):
        with cls._lock:
            if not cls._reader:
                return

            cls._reader = None
            cls._keyevt.wait()

    @classmethod
    def _read_runner(cls):
        input = create_input()

        try:
            asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        with input.raw_mode():
            with input.detach():
                no_emergency = 3
                while True:
                    with cls._lock:
                        keys = input.read_keys()
                        # emergency escape
                        for k in keys:
                            if k.key == "c-c":
                                no_emergency -= 1
                            else:
                                no_emergency = 3

                        if not no_emergency:
                            keys.append(KeyPress("!", data="c-c"))

                        if keys:
                            cls._keys.extend(keys)

                        if keys or not cls._reader:
                            cls._keyevt.notifyAll()
                        if not cls._reader:
                            break
                    if not keys:
                        time.sleep(0.05)

    @classmethod
    def read(cls):
        with cls._lock:
            while True:
                if cls._keys:
                    return cls._keys.popleft()
                elif cls._reader:
                    cls._keyevt.wait()
                else:
                    return None

    @classmethod
    def unset(cls):
        with cls._lock:
            cls.abort()
            cls._keys = None

    @classmethod
    def set(cls, echo=False):
        with cls._lock:
            if not cls._reader:
                cls._keys = deque()
                cls._reader = threading.Thread(name="getch", target=cls._read_runner, daemon=True)
                cls._reader.start()


impl = _getChPromptToolkit


class getchIt(object):
    def __enter__(self):
        impl.set()
        return self

    def __exit__(self, *_err):
        impl.unset()

    def __iter__(self):
        return self

    def __next__(self):
        result = ""
        while not result:
            result = impl.read()
            if result is None:
                raise StopIteration
            if result.key == "!" and result.data == "c-c":
                raise KeyboardInterrupt

        return result.data


class getcheIt(getchIt):
    def __enter__(self):
        try:
            impl.set(echo=True)
        except RuntimeError:
            self.leave = False
        return self

    def __exit__(self, *_err):
        if self.leave:
            impl.unset()


def getch():
    with getchIt() as it:
        try:
            ch = next(it)
            return b"" if ch is None else ch
        except:  # noqa: E722
            return b""


def getche():
    with getcheIt() as it:
        ch = next(it)
        return b"" if ch is None else ch


def abort():
    impl.abort()
