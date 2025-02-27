import asyncio
import dataclasses
import logging
import typing

import circuit_breaker_box
import fastapi
import httpx
import pydantic
from redis import asyncio as aioredis

import base_client
from base_client import errors
from base_client.response import response_to_model


logger = logging.getLogger(__name__)


@dataclasses.dataclass
class TestRedisConnection(aioredis.Redis):  # type: ignore[type-arg]
    async def incr(self, host: str | bytes, amount: int = 1) -> int:
        logger.debug("host: %s, amount: %d{amount}", host, amount)
        return amount

    async def expire(self, *args: typing.Any, **kwargs: typing.Any) -> bool:  # noqa: ANN401
        logger.debug(args, kwargs)
        return True

    async def get(self, host: str | bytes) -> None:
        logger.debug("host: %s", host)


class SpecificResponse(pydantic.BaseModel):
    status: int


MAX_RETRIES = 4
CIRCUIT_BREAKER_MAX_FAILURE_COUNT = 2


class SomeSpecificClient(base_client.BaseClient):
    async def some_method(self, params: dict[str, str]) -> SpecificResponse:
        request = self.prepare_request(method="GET", url="/status/200", params=params, timeout=httpx.Timeout(5))
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
        raise fastapi.HTTPException(status_code=500, detail=f"Host R-Online {host} is unavailable")


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    circuit_breaker = CustomCircuitBreaker(
        reset_timeout_in_seconds=30,
        max_failure_count=CIRCUIT_BREAKER_MAX_FAILURE_COUNT,
        max_cache_size=1,
    )
    retrier_with_circuit_breaker = circuit_breaker_box.RetrierCircuitBreaker[httpx.Response](
        circuit_breaker=circuit_breaker,
        max_retries=MAX_RETRIES,
        exceptions_to_retry=(httpx.RequestError, errors.HttpStatusError),
    )
    client = SomeSpecificClient(
        client=httpx.AsyncClient(base_url="https://postman-echo.com", timeout=httpx.Timeout(1)),
        circuit_breaker=retrier_with_circuit_breaker,
    )
    answer = await client.some_method(params={"foo": "bar"})
    logger.debug(answer.model_dump())


if __name__ == "__main__":
    asyncio.run(main())
