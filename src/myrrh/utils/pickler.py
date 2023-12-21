# -*- coding: utf-8 -*-

import xmlrpc.client

import pickle
import traceback

import myrrh

__all__ = ["encode_arg", "encode_arg_self", "decode_arg", "decode_arg_self"]


def _except_encode(exc, trcbck):
    raise xmlrpc.client.Fault(0, pickle.dumps((exc, trcbck)))


def _except_decode(fault):
    try:
        exc, trcbck = pickle.loads(fault.faultString.data)
    except Exception as e:
        exc = fault
        trcbck = traceback.format_tb(e.__traceback__)

    exc.straceback = trcbck

    myrrh.log.debug(f'{"".join(trcbck)}{str(exc)}\n')

    raise exc


def _encode(val):
    return pickle.dumps(val)


def _decode(val):
    if hasattr(val, "data"):
        return pickle.loads(val.data)
    return val


def encode_arg(proc):
    def wrapper(self, *args, **kwargs):
        try:
            return _decode(proc(self, _encode(args), _encode(kwargs)))
        except xmlrpc.client.Fault as fault:
            _except_decode(fault)

    return wrapper


def encode_arg_self(proc):
    def wrapper(*args, **kwargs):
        try:
            return _decode(proc(_encode(args), _encode(kwargs)))
        except xmlrpc.client.Fault as fault:
            _except_decode(fault)

    return wrapper


def decode_arg(proc):
    def wrapper(self, args, kwargs):
        try:
            return _encode(proc(self, *_decode(args), **_decode(kwargs)))
        except Exception as e:
            _except_encode(e, trcbck=traceback.format_tb(e.__traceback__))

    return wrapper


def decode_arg_self(proc):
    def wrapper(args, kwargs):
        try:
            return _encode(proc(*_decode(args), **_decode(kwargs)))
        except Exception as e:
            _except_encode(e, trcbck=traceback.format_tb(e.__traceback__))

    return wrapper
