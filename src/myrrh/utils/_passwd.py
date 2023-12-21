# -*- coding: utf-8 -*-
"""
**Myrrh password manager module**

    This module contains necessary functionalities for **volatile** storing of passwords.
"""

import getpass

__all__ = ["Passwd"]


class CacheData(object):
    def __init__(self):
        pass


class Passwd:
    __hostlist: dict[str, dict[str, str]] = {}

    class NotAcquired(Exception):
        @classmethod
        def raised(cls):
            raise cls()

    @classmethod
    def getPass(cls, host, user, pwd=None):
        if host not in Passwd.__hostlist:
            Passwd.__hostlist[host] = {}

        if user in Passwd.__hostlist[host]:
            return Passwd.__hostlist[host][user]

        pwd = pwd if pwd is not None else getpass.getpass(("Please enter needed password for user %s on %s\npassword:" % (user, host)).encode("ascii"))

        Passwd.__hostlist[host][user] = ("%s" % pwd).strip()

        return Passwd.__hostlist[host][user]

    @classmethod
    def getData(cls, host, name, value=None, acquire=lambda: Passwd.NotAcquired.raised()):
        if host not in Passwd.__hostlist:
            Passwd.__hostlist[host] = {}

        if value is None and name in Passwd.__hostlist[host]:
            return Passwd.__hostlist[host][name]

        if name in Passwd.__hostlist[host] and value != Passwd.__hostlist[host][name]:
            Passwd.__hostlist[host][name] = value

        try:
            Passwd.__hostlist[host][name] = acquire() if value is None else value
        except Passwd.NotAcquired:
            return None

        return Passwd.__hostlist[host][name]

    @classmethod
    def invalidPass(cls, host, user=None):
        if user is None:
            Passwd.__hostlist.pop(host)
        else:
            Passwd.__hostlist[host].pop(user, None)
