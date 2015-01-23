# coding: utf-8

from eventlet import GreenPool, sleep
from eventlet.event import Event
import pytest

from nameko.utils import fail_fast_imap, repr_safe_str, safe_for_json

OBJECT_REPR = "<type 'object'>"


def test_fail_fast_imap():
    # A failing call...
    failing_exception = Exception()

    def failing_call():
        raise failing_exception

    # ...and an eventually successful call.
    slow_call_returned = Event()

    def slow_call():
        sleep(5)
        slow_call_returned.send()

    identity_fn = lambda x: x()
    calls = [slow_call, failing_call]

    pool = GreenPool(2)

    # fail_fast_imap fails as soon as the exception is raised
    with pytest.raises(Exception) as raised_exc:
        list(fail_fast_imap(pool, identity_fn, calls))
    assert raised_exc.value == failing_exception

    # The slow call won't go past the sleep as it was killed
    assert not slow_call_returned.ready()
    assert pool.free() == 2


@pytest.mark.parametrize("value, repr_safe_value", [
    ("bytestr", b"bytestr"),
    ("bÿtestr", b"b\xc3\xbftestr"),
    (u"unicode", b"unicode"),
    (u"unicøde", b"unic\xc3\xb8de"),
    (None, b"None"),  # cannot encode non-string
    (object, b"<type 'object'>"),  # cannot encode non-string
])
def test_repr_safe_str(value, repr_safe_value):
    res = repr_safe_str(value)
    assert res == repr_safe_value
    assert isinstance(res, bytes)


@pytest.mark.parametrize("value, safe_value", [
    ('str', 'str'),
    (object, OBJECT_REPR),
    ([object], [OBJECT_REPR]),
    ({object}, [OBJECT_REPR]),
    ({'foo': 'bar'}, {'foo': 'bar'}),
    ({object: None}, {OBJECT_REPR: 'None'}),
    ({None: object}, {'None': OBJECT_REPR}),
    ((1, 2), ['1', '2']),
    ([1, [2]], ['1', ['2']]),
])
def test_safe_for_json(value, safe_value):
    assert safe_for_json(value) == safe_value


def test_safe_for_json_bad_str():
    class BadStr(object):
        def __str__(self):
            raise Exception('boom')

    obj = BadStr()
    safe = safe_for_json(obj)
    assert isinstance(safe, basestring)
    assert 'failed' in safe
