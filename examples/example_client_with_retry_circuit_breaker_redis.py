import asyncio
import dataclasses
import logging
import typing

import circuit_breaker_box
import httpx
import pydantic
import tenacity
from redis import asyncio as aioredis

import base_client
from base_client import errors
from base_client.response import response_to_model


logger = logging.getLogger(__name__)


@dataclasses.dataclass
class FakeRedisConnection(aioredis.Redis):  # type: ignore[type-arg]
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


MAX_RETRIES = 10
CIRCUIT_BREAKER_MAX_FAILURE_COUNT = 2
RESET_TIMEOUT_IN_SECONDS = 10
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


async def main() -> None:
    logging.basicConfig(level=logging.DEBUG)
    circuit_breaker = circuit_breaker_box.CircuitBreakerRedis(
        reset_timeout_in_seconds=RESET_TIMEOUT_IN_SECONDS,
        max_failure_count=CIRCUIT_BREAKER_MAX_FAILURE_COUNT,
        redis_connection=FakeRedisConnection(),
    )
    retrier_with_circuit_breaker = circuit_breaker_box.Retrier[httpx.Response](
        circuit_breaker=circuit_breaker,
        stop_rule=tenacity.stop.stop_after_attempt(MAX_RETRIES),
        retry_cause=tenacity.retry_if_exception_type((httpx.RequestError, base_client.errors.HttpServerError)),
        wait_strategy=tenacity.wait_none(),
    )
    client = SomeSpecificClient(
        client=httpx.AsyncClient(base_url=SOME_HOST, timeout=httpx.Timeout(1)),
        retrier=retrier_with_circuit_breaker,
    )
    answer = await client.some_method(params={"foo": "bar"})
    logger.debug(answer.model_dump())


if __name__ == "__main__":
    asyncio.run(main())
