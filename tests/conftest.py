import circuit_breaker_box
import httpx
import pytest
import tenacity

import base_client
from examples.example_client_with_retry_circuit_breaker_redis import FakeRedisConnection


TEST_BASE_URL = "http://example.com/"


class FakeClient(base_client.BaseClient):
    async def fetch_async(self, request: httpx.Request) -> httpx.Response:
        return await self.send(request=request)


CLIENT_MAX_FAILURE_COUNT = 1
RESET_TIMEOUT_IN_SECONDS = 10
MAX_RETRIES = 4
MAX_CACHE_SIZE = 256


@pytest.fixture(name="test_client_with_circuit_breaker_redis")
def test_client_with_circuit_breaker_redis() -> FakeClient:
    circuit_breaker = circuit_breaker_box.CircuitBreakerRedis(
        redis_connection=FakeRedisConnection(),
        reset_timeout_in_seconds=RESET_TIMEOUT_IN_SECONDS,
        max_failure_count=CLIENT_MAX_FAILURE_COUNT,
    )
    retrier_with_circuit_breaker = circuit_breaker_box.Retrier[httpx.Response](
        circuit_breaker=circuit_breaker,
        stop_rule=tenacity.stop.stop_after_attempt(MAX_RETRIES),
        retry_cause=tenacity.retry_if_exception_type((httpx.RequestError, base_client.errors.HttpStatusError)),
        wait_strategy=tenacity.wait_none(),
    )
    return FakeClient(
        client=httpx.AsyncClient(base_url=TEST_BASE_URL, timeout=httpx.Timeout(1)),
        retrier=retrier_with_circuit_breaker,
    )


@pytest.fixture(name="test_client_with_circuit_breaker_in_memory")
def test_client_with_circuit_breaker_in_memory() -> FakeClient:
    circuit_breaker = circuit_breaker_box.CircuitBreakerInMemory(
        reset_timeout_in_seconds=RESET_TIMEOUT_IN_SECONDS,
        max_cache_size=MAX_CACHE_SIZE,
        max_failure_count=CLIENT_MAX_FAILURE_COUNT,
    )
    retrier_with_circuit_breaker = circuit_breaker_box.Retrier[httpx.Response](
        circuit_breaker=circuit_breaker,
        stop_rule=tenacity.stop.stop_after_attempt(MAX_RETRIES),
        retry_cause=tenacity.retry_if_exception_type((httpx.RequestError, base_client.errors.HttpStatusError)),
        wait_strategy=tenacity.wait_none(),
    )
    return FakeClient(
        client=httpx.AsyncClient(base_url=TEST_BASE_URL, timeout=httpx.Timeout(1)),
        retrier=retrier_with_circuit_breaker,
    )


@pytest.fixture(name="test_client")
def fixture_test_client() -> FakeClient:
    return FakeClient(client=httpx.AsyncClient(base_url=TEST_BASE_URL, timeout=httpx.Timeout(1)))
