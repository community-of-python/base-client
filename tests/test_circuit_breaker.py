import typing

import circuit_breaker_box
import httpx
import pytest
import respx

from examples.example_client_with_retry_circuit_breaker_redis import FakeRedisConnection
from tests.conftest import CLIENT_MAX_FAILURE_COUNT, TEST_BASE_URL, FakeClient


@pytest.mark.parametrize(
    "side_effect",
    [
        httpx.RequestError("RequestError message"),
        httpx.TransportError("TransportError message"),
        httpx.TimeoutException("TimeoutException message"),
        httpx.ConnectTimeout("ConnectTimeout message"),
        httpx.ReadTimeout("ReadTimeout message"),
        httpx.WriteTimeout("WriteTimeout message"),
        httpx.PoolTimeout("PoolTimeout message"),
        httpx.NetworkError("NetworkError message"),
        httpx.ConnectError("ConnectError message"),
        httpx.ReadError("ReadError message"),
        httpx.WriteError("WriteError message"),
        httpx.CloseError("CloseError message"),
        httpx.ProtocolError("ProtocolError message"),
        httpx.LocalProtocolError("LocalProtocolError message"),
        httpx.RemoteProtocolError("RemoteProtocolError message"),
        httpx.ProxyError("ProxyError message"),
        httpx.UnsupportedProtocol("UnsupportedProtocol message"),
        httpx.DecodingError("DecodingError message"),
        httpx.TooManyRedirects("TooManyRedirects message"),
    ],
)
@respx.mock
async def test_circuit_breaker_in_memory(
    test_client_with_circuit_breaker_in_memory: FakeClient, side_effect: Exception
) -> None:
    mocked_route = respx.get(TEST_BASE_URL).mock(side_effect=side_effect)

    with pytest.raises(circuit_breaker_box.HostUnavailableError, match=f"{httpx.URL(TEST_BASE_URL).host}"):
        await test_client_with_circuit_breaker_in_memory.fetch_async(
            test_client_with_circuit_breaker_in_memory.prepare_request(method="GET", url=TEST_BASE_URL)
        )

    assert mocked_route.called


@respx.mock
@pytest.mark.parametrize(
    ("side_effect", "errors_by_host_in_redis", "expected_raise"),
    [
        (httpx.ReadTimeout("ReadTimeout message"), CLIENT_MAX_FAILURE_COUNT - 1, httpx.RequestError),
        (httpx.ConnectTimeout("ConnectTimeout message"), CLIENT_MAX_FAILURE_COUNT, httpx.ConnectTimeout),
        (
            circuit_breaker_box.HostUnavailableError(TEST_BASE_URL),
            CLIENT_MAX_FAILURE_COUNT + 1,
            circuit_breaker_box.HostUnavailableError,
        ),
    ],
)
async def test_circuit_breaker_redis(
    side_effect: type[Exception],
    expected_raise: type[Exception],
    errors_by_host_in_redis: int,
    test_client_with_circuit_breaker_redis: FakeClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def mock_return(*args: typing.Any, **kwargs: typing.Any) -> int:  # noqa: ARG001, ANN401
        return errors_by_host_in_redis

    monkeypatch.setattr(FakeRedisConnection, "get", mock_return)

    respx.get(TEST_BASE_URL).mock(side_effect=side_effect)
    with pytest.raises(expected_raise):
        await test_client_with_circuit_breaker_redis.fetch_async(
            test_client_with_circuit_breaker_redis.prepare_request(method="GET", url=TEST_BASE_URL)
        )
