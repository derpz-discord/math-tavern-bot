import datetime
import random

import pytest
from derpz_botlib.utils import parse_human_time


@pytest.mark.parametrize(
    "human_time, expected",
    [
        ("1d", datetime.timedelta(days=1)),
        ("1 day", datetime.timedelta(days=1)),
        ("1 days", datetime.timedelta(days=1)),
        ("1h", datetime.timedelta(hours=1)),
        ("1 hour", datetime.timedelta(hours=1)),
        ("1 hours", datetime.timedelta(hours=1)),
        ("1m", datetime.timedelta(minutes=1)),
        ("1 min", datetime.timedelta(minutes=1)),
        ("1 minute", datetime.timedelta(minutes=1)),
        ("1 minutes", datetime.timedelta(minutes=1)),
        ("1s", datetime.timedelta(seconds=1)),
        ("1 sec", datetime.timedelta(seconds=1)),
        ("1 second", datetime.timedelta(seconds=1)),
        ("1 seconds", datetime.timedelta(seconds=1)),
        (
            "100 days 100 hours 100 minutes 100 seconds",
            datetime.timedelta(days=100, hours=100, minutes=100, seconds=100),
        ),
        ("1d 1h", datetime.timedelta(days=1, hours=1)),
        ("1d 1h 1m", datetime.timedelta(days=1, hours=1, minutes=1)),
        ("1d 1h 1m 1s", datetime.timedelta(days=1, hours=1, minutes=1, seconds=1)),
        ("1d1h 1m 1s", datetime.timedelta(days=1, hours=1, minutes=1, seconds=1)),
        ("1d1h1m 1s", datetime.timedelta(days=1, hours=1, minutes=1, seconds=1)),
        ("1d1h1m1s", datetime.timedelta(days=1, hours=1, minutes=1, seconds=1)),
    ],
)
def test_parse_human_time(human_time: str, expected: datetime.timedelta):
    assert parse_human_time(human_time) == expected
