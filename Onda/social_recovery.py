"""Bounded recovery for public social metadata, shared by PC and Android."""

import json
import time
from html.parser import HTMLParser
from urllib.error import URLError
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

TRANSIENT_STATUS = {429, 500, 502, 503, 504}


def _cause(error):
    seen = set()
    for _ in range(5):
        if id(error) in seen:
            break
        seen.add(id(error))
        nested = getattr(error, 'cause', None) or error.__cause__
        if not isinstance(nested, BaseException):
            break
        error = nested
    return error


def retry_delay(error):
    error = _cause(error)
    response = getattr(error, 'response', None)
    status = (
        getattr(response, 'status_code', None)
        or getattr(error, 'status', None)
        or getattr(error, 'code', None)
    )
    if status is not None:
        if status not in TRANSIENT_STATUS:
            return None
        headers = (
            getattr(response, 'headers', None) or getattr(error, 'headers', {}) or {}
        )
        try:
            delay = float(headers.get('Retry-After', '0.5'))
        except (TypeError, ValueError):
            try:
                until = parsedate_to_datetime(headers.get('Retry-After', ''))
                if until.tzinfo is None:
                    until = until.replace(tzinfo=timezone.utc)
                delay = max(0, (until - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                delay = 0.5
        # Never turn rate limiting into an unbounded wait/retry loop.
        return max(0.5, delay) if 0 <= delay <= 5 else None
    if isinstance(error, requests.exceptions.SSLError):
        return None
    if isinstance(
        error,
        (
            requests.Timeout,
            requests.ConnectionError,
            requests.exceptions.ChunkedEncodingError,
            TimeoutError,
            ConnectionError,
        ),
    ):
        return 0.5
    if isinstance(error, URLError) and isinstance(
        error.reason, (TimeoutError, ConnectionError)
    ):
        return 0.5
    return None


def retry_metadata(operation):
    for attempt in range(2):
        try:
            return operation()
        except Exception as error:
            delay = retry_delay(error)
            if attempt or delay is None:
                raise
            time.sleep(delay)


def public_response(session, url, **kwargs):
    def request():
        response = session.get(url, **kwargs)
        try:
            response.raise_for_status()
        except Exception:
            response.close()
            raise
        return response

    return retry_metadata(request)


def public_html(
    session, url, *, headers=None, max_bytes=8 * 1024 * 1024, with_url=False
):
    def request():
        with session.get(
            url, headers=headers, stream=True, timeout=(15, 20)
        ) as response:
            response.raise_for_status()
            data = bytearray()
            for chunk in response.iter_content(65536):
                data.extend(chunk)
                if len(data) > max_bytes:
                    raise ValueError('Página da rede social acima do limite.')
            html = data.decode('utf-8', errors='replace')
            return (html, response.url) if with_url else html

    return retry_metadata(request)


def script_json(html, identity):
    class Scripts(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.active = False
            self.parts = []
            self.value = None

        def handle_starttag(self, tag, attrs):
            if tag == 'script':
                self.active = dict(attrs).get('id') == identity
                self.parts = []

        def handle_data(self, data):
            if self.active:
                self.parts.append(data)

        def handle_endtag(self, tag):
            if tag == 'script' and self.active:
                try:
                    value = json.loads(''.join(self.parts))
                except (ValueError, TypeError):
                    pass
                else:
                    if self.value is None:
                        self.value = value
                self.active = False

    parser = Scripts()
    parser.feed(html)
    return parser.value
