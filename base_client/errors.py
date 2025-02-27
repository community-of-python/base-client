import typing

import httpx


class BaseClientError(Exception):
    def __init__(self, *args: typing.Any) -> None:  # noqa: ANN401
        super().__init__(*args)


class HttpStatusError(BaseClientError):
    """error raised when http status code is not 2xx."""

    def __init__(self, *args: typing.Any, response: httpx.Response) -> None:  # noqa: ANN401
        super().__init__(*args)
        self.response = response


class HttpClientError(HttpStatusError):
    """error raised when http status code is 4xx."""


class HttpServerError(HttpStatusError):
    """error raised when http status code is 5xx."""
