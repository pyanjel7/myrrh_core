__all__ = [
    "BmyException",
    "BmyExecutionFailure",
    "BmyInvalidParameter",
    "BmyInvalidEid",
    "BmyMyrrhFailure",
    "BmyNotReady",
    "BmyTimeout",
]


class BmyException(Exception):
    def __init__(self, eid=None, func=None, msg="unexpected exception"):
        super().__init__(msg)
        self.eid = eid
        self.func = func


class BmyMyrrhFailure(BmyException):
    pass


class BmyExecutionFailure(BmyException):
    pass


class BmyInvalidParameter(BmyException):
    pass


class BmyInvalidEid(BmyInvalidParameter):
    def __init__(self, eid, func=None, msg=None):
        msg = msg or (eid and "invalid entity id: %s" % eid or "no entity id selected")
        super().__init__(eid, func, msg=msg)


class BmyEidInUsed(BmyInvalidParameter):
    def __init__(self, eid, func=None, msg=None):
        msg = msg or 'entity "%s" is in used' % eid
        super().__init__(eid, func, msg=msg)


class BmyNotReady(BmyException):
    def __init__(self, eid):
        msg = 'entity "%s" not ready, built is required' % eid
        super().__init__(msg=msg)
        self.eid = eid


class BmyTimeout(BmyException):
    def __init__(
        self,
        subject=None,
        reason=None,
        period=None,
        max_period=None,
        entity=None,
        msg=None,
    ):
        msg = msg or 'period expired for "%s", %s:%.3f>%.3f' % (
            subject,
            reason,
            period,
            max_period,
        )
        super().__init__(entity=entity, msg=msg)
        self.subject = subject
        self.reason = reason
        self.period = period
        self.max_period = max_period


class MyrrhCalibrationFailure(BmyException):
    pass
