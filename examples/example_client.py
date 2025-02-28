import asyncio
import logging

import httpx
import pydantic

import base_client
from base_client import errors
from base_client.response import response_to_model


logger = logging.getLogger(__name__)


class SpecificResponse(pydantic.BaseModel):
    status: int


SOME_HOST = "https://postman-echo.com"


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


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    client = SomeSpecificClient(client=httpx.AsyncClient(base_url=SOME_HOST, timeout=httpx.Timeout(1)))
    answer = await client.some_method(params={})
    logger.info(answer)


if __name__ == "__main__":
    asyncio.run(main())
