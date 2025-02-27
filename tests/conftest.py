import circuit_breaker_box
import httpx
import pytest

import base_client
from examples.example_client import TestRedisConnection


TEST_BASE_URL = "http://example.com/"


class TestClient(base_client.BaseClient):
    async def fetch_async(self, request: httpx.Request) -> httpx.Response:
        return await self.send(request=request)


CLIENT_MAX_FAILURE_COUNT = 1
RESET_TIMEOUT_IN_SECONDS = 10
MAX_RETRIES = 4
MAX_CACHE_SIZE = 256


@pytest.fixture(name="test_client_with_circuit_breaker_redis")
def test_client_with_circuit_breaker_redis() -> TestClient:
    circuit_breaker = circuit_breaker_box.CircuitBreakerRedis(
        redis_connection=TestRedisConnection(),
        reset_timeout_in_seconds=RESET_TIMEOUT_IN_SECONDS,
        max_failure_count=CLIENT_MAX_FAILURE_COUNT,
    )
    retrier_with_circuit_breaker = circuit_breaker_box.RetrierCircuitBreaker[httpx.Response](
        circuit_breaker=circuit_breaker,
        max_retries=MAX_RETRIES,
        exceptions_to_retry=(httpx.RequestError, base_client.errors.HttpStatusError),
    )
    return TestClient(
        client=httpx.AsyncClient(base_url=TEST_BASE_URL, timeout=httpx.Timeout(1)),
        circuit_breaker=retrier_with_circuit_breaker,
    )


@pytest.fixture(name="test_client_with_circuit_breaker_in_memory")
def test_client_with_circuit_breaker_in_memory() -> TestClient:
    circuit_breaker = circuit_breaker_box.CircuitBreakerInMemory(
        reset_timeout_in_seconds=RESET_TIMEOUT_IN_SECONDS,
        max_cache_size=MAX_CACHE_SIZE,
        max_failure_count=CLIENT_MAX_FAILURE_COUNT,
    )
    retrier_with_circuit_breaker = circuit_breaker_box.RetrierCircuitBreaker[httpx.Response](
        circuit_breaker=circuit_breaker,
        max_retries=MAX_RETRIES,
        exceptions_to_retry=(httpx.RequestError, base_client.errors.HttpStatusError),
    )
    return TestClient(
        client=httpx.AsyncClient(base_url=TEST_BASE_URL, timeout=httpx.Timeout(1)),
        circuit_breaker=retrier_with_circuit_breaker,
    )


@pytest.fixture(name="test_client")
def fixture_test_client() -> TestClient:
    return TestClient(client=httpx.AsyncClient(base_url=TEST_BASE_URL, timeout=httpx.Timeout(1)))
