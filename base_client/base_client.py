import dataclasses
import logging
import typing

import circuit_breaker_box
import httpx
from httpx._client import USE_CLIENT_DEFAULT, UseClientDefault
from httpx._types import (
    CookieTypes,
    HeaderTypes,
    QueryParamTypes,
    RequestContent,
    RequestData,
    RequestExtensions,
    RequestFiles,
    TimeoutTypes,
)

from base_client import errors


logger = logging.getLogger(__name__)


CallableT = typing.TypeVar("CallableT", bound=typing.Callable)  # type: ignore[type-arg]
T = typing.TypeVar("T")


@dataclasses.dataclass(kw_only=True, slots=True)
class BaseClient:
    client: httpx.AsyncClient
    retrier: circuit_breaker_box.Retrier[httpx.Response] | None = None

    async def send(self, *, request: httpx.Request) -> httpx.Response:
        if self.retrier:
            return await self.retrier.retry(self._process_request, request.url.host, request=request)
        return await self._process_request(request)

    def prepare_request(  # noqa: PLR0913
        self,
        method: str,
        url: httpx.URL | str,
        *,
        content: RequestContent | None = None,
        data: RequestData | None = None,
        files: RequestFiles | None = None,
        json: typing.Any | None = None,  # noqa: ANN401
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        extensions: RequestExtensions | None = None,
    ) -> httpx.Request:
        if isinstance(url, str):
            url = httpx.URL(url)

        assembled_params: dict[str, typing.Any] = {}
        if url.params:
            assembled_params.update(url.params)

        if isinstance(params, dict):
            assembled_params.update(params)

        if isinstance(params, list):
            assembled_params.update(dict(params))

        logger.debug("Client request:  method: %s, url: %s, params: %s, headers: %s", method, url, params, headers)
        return self.client.build_request(
            method=method,
            url=url,
            timeout=timeout,
            content=content,
            data=data,
            files=files,
            json=json,
            params=assembled_params,
            headers=headers,
            cookies=cookies,
            extensions=extensions,
        )

    async def _process_request(self, request: httpx.Request) -> httpx.Response:
        response = await self.client.send(request=request)
        return await self._postprocess_response(response)

    async def _postprocess_response(self, response: httpx.Response) -> httpx.Response:
        logger.debug(
            "Client response: status_code: %s, url: %s, text: %s, headers: %s",
            response.status_code,
            response.url,
            response.text,
            response.headers,
        )
        await self.validate_response(response=response)
        return response

    async def validate_response(self, *, response: httpx.Response) -> None:
        if httpx.codes.is_server_error(response.status_code):
            msg = f"Status code is {response.status_code}"
            raise errors.HttpServerError(msg, response=response)
