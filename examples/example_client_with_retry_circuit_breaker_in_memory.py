import asyncio
import logging
import typing

import circuit_breaker_box
import fastapi
import httpx
import pydantic
import tenacity

import base_client
from base_client import errors
from base_client.response import response_to_model


logger = logging.getLogger(__name__)


class SpecificResponse(pydantic.BaseModel):
    status: int


MAX_RETRIES = 5
CIRCUIT_BREAKER_MAX_FAILURE_COUNT = 2
RESET_TIMEOUT_IN_SECONDS = 10
MAX_CACHE_SIZE = 1
SOME_HOST = "https://postman-echo.com"


class SomeSpecificClient(base_client.BaseClient):
    async def some_method(self, params: dict[str, str]) -> SpecificResponse:
        request = self.prepare_request(method="GET", url="/status/500", params=params, timeout=httpx.Timeout(5))
        response = await self.send(request=request)
        return response_to_model(model_type=SpecificResponse, response=response)

    async def validate_response(self, *, response: httpx.Response) -> None:
        msg = f"Status code is {response.status_code}"
        if httpx.codes.is_server_error(response.status_code):
            raise errors.HttpServerError(msg, response=response)
        if httpx.codes.is_client_error(response.status_code):
            raise errors.HttpClientError(msg, response=response)
        if not httpx.codes.is_success(response.status_code):
            raise errors.HttpStatusError(msg, response=response)


class CustomCircuitBreaker(circuit_breaker_box.CircuitBreakerInMemory):
    async def raise_host_unavailable_error(self, host: str) -> typing.NoReturn:
        raise fastapi.HTTPException(status_code=500, detail=f"Host {host} is unavailable")


async def main() -> None:
    logging.basicConfig(level=logging.DEBUG)
    circuit_breaker = CustomCircuitBreaker(
        reset_timeout_in_seconds=RESET_TIMEOUT_IN_SECONDS,
        max_failure_count=CIRCUIT_BREAKER_MAX_FAILURE_COUNT,
        max_cache_size=MAX_CACHE_SIZE,
    )
    retrier_with_circuit_breaker = circuit_breaker_box.Retrier[httpx.Response](
        circuit_breaker=circuit_breaker,
        stop_rule=tenacity.stop.stop_after_attempt(MAX_RETRIES),
        retry_cause=tenacity.retry_if_exception_type((httpx.RequestError, base_client.errors.HttpServerError)),
        wait_strategy=tenacity.wait_fixed(1),
    )
    client = SomeSpecificClient(
        client=httpx.AsyncClient(base_url=SOME_HOST, timeout=httpx.Timeout(1)),
        retrier=retrier_with_circuit_breaker,
    )
    answer = await client.some_method(params={})
    logger.debug(answer)


if __name__ == "__main__":
    asyncio.run(main())
