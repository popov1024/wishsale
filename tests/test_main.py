"""Тесты парсинга NOTIFY_CHAT_ID (main.py)."""
import pytest

from main import parse_recipients


def test_parse_recipients_simple():
    assert parse_recipients("123456789") == [(123456789, None)]


def test_parse_recipients_username():
    assert parse_recipients("@my_channel") == [("@my_channel", None)]


def test_parse_recipients_thread():
    assert parse_recipients("-100123:42") == [(-100123, 42)]


def test_parse_recipients_multiple():
    assert parse_recipients("123, @chan:7, -1009") == [
        (123, None),
        ("@chan", 7),
        (-1009, None),
    ]


def test_parse_recipients_empty_and_spaces():
    assert parse_recipients("") == []
    assert parse_recipients(" 123 , , 456 ") == [(123, None), (456, None)]


def test_parse_recipients_invalid_thread():
    with pytest.raises(ValueError):
        parse_recipients("123:abc")
