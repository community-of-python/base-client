import httpx
import multidict
import pydantic
import pytest
import respx

import base_client
from base_client.response import response_to_model
from tests.conftest import TEST_BASE_URL, FakeClient


@respx.mock
@pytest.mark.parametrize(
    "expected_request",
    [
        httpx.Request(
            method="GET",
            url=TEST_BASE_URL,
            params=multidict.MultiDict({"value": "1"}),
            headers=multidict.CIMultiDict({"headers_key": "headers_value"}),
        ),
        httpx.Request(
            method="GET",
            url=TEST_BASE_URL,
            params=multidict.MultiDict({"value": "2"}),
            headers=multidict.CIMultiDict({"headers_key": "headers_value"}),
            content=b"content",
        ),
        httpx.Request(
            method="GET",
            url=TEST_BASE_URL,
            params=multidict.MultiDict({"value": "3"}),
            headers=multidict.CIMultiDict({"headers_key": "headers_value"}),
            content=b'{"key": "value"}',
        ),
    ],
)
async def test_client_async(test_client: FakeClient, expected_request: httpx.Request) -> None:
    mocked_route = respx.get(expected_request.url).mock(return_value=httpx.Response(status_code=httpx.codes.OK))
    response = await test_client.fetch_async(expected_request)
    assert mocked_route.called
    assert response.status_code == httpx.codes.OK


@respx.mock
async def test_client_request_404(test_client: FakeClient) -> None:
    mocked_route = respx.get(TEST_BASE_URL).mock(return_value=httpx.Response(status_code=httpx.codes.NOT_FOUND))
    response = await test_client.fetch_async(test_client.prepare_request(method="GET", url=TEST_BASE_URL))
    assert mocked_route.called
    assert response.status_code == httpx.codes.NOT_FOUND


@respx.mock
@pytest.mark.parametrize(
    ("side_effect", "expected_raise"),
    [
        (httpx.RequestError("RequestError message"), httpx.RequestError),
        (httpx.TransportError("TransportError message"), httpx.TransportError),
        (httpx.TimeoutException("message"), httpx.TimeoutException),
        (httpx.ConnectTimeout("ConnectTimeout message"), httpx.ConnectTimeout),
        (httpx.ReadTimeout("ReadTimeout message"), httpx.ReadTimeout),
        (httpx.WriteTimeout("WriteTimeout message"), httpx.WriteTimeout),
        (httpx.PoolTimeout("PoolTimeout message"), httpx.PoolTimeout),
        (httpx.NetworkError("NetworkError message"), httpx.NetworkError),
        (httpx.ConnectError("ConnectError message"), httpx.ConnectError),
        (httpx.ReadError("ReadError message"), httpx.ReadError),
        (httpx.WriteError("WriteError message"), httpx.WriteError),
        (httpx.CloseError("CloseError message"), httpx.CloseError),
        (httpx.ProtocolError("ProtocolError message"), httpx.ProtocolError),
        (httpx.LocalProtocolError("LocalProtocolError message"), httpx.LocalProtocolError),
        (httpx.RemoteProtocolError("RemoteProtocolError message"), httpx.RemoteProtocolError),
        (httpx.ProxyError("ProxyError message"), httpx.ProxyError),
        (httpx.UnsupportedProtocol("UnsupportedProtocol message"), httpx.UnsupportedProtocol),
        (httpx.DecodingError("DecodingError message"), httpx.DecodingError),
        (httpx.TooManyRedirects("TooManyRedirects message"), httpx.TooManyRedirects),
    ],
)
async def test_retries(side_effect: type[Exception], expected_raise: type[Exception], test_client: FakeClient) -> None:
    mocked_route = respx.get(TEST_BASE_URL).mock(side_effect=side_effect)
    with pytest.raises(expected_raise):
        await test_client.fetch_async(test_client.prepare_request(method="GET", url=TEST_BASE_URL))

    assert mocked_route.called


@respx.mock
@pytest.mark.parametrize(
    ("side_effect", "expected_raise"),
    [
        (httpx.HTTPError("HTTPError message"), httpx.HTTPError),
        (httpx.InvalidURL("InvalidURL message"), httpx.InvalidURL),
        (httpx.CookieConflict("CookieConflict message"), httpx.CookieConflict),
        (httpx.StreamError("StreamError message"), httpx.StreamError),
        (httpx.StreamConsumed(), httpx.StreamConsumed),
        (httpx.StreamClosed(), httpx.StreamClosed),
        (httpx.ResponseNotRead(), httpx.ResponseNotRead),
        (httpx.RequestNotRead(), httpx.RequestNotRead),
    ],
)
async def test_wont_retry(
    side_effect: type[Exception], expected_raise: type[Exception], test_client: FakeClient
) -> None:
    mocked_route = respx.get(TEST_BASE_URL).mock(side_effect=side_effect)

    with pytest.raises(expected_raise):
        await test_client.fetch_async(test_client.prepare_request(method="GET", url=TEST_BASE_URL))

    assert mocked_route.called


@pytest.mark.parametrize(
    ("status_code", "side_effect"),
    [
        (500, base_client.HttpServerError),
        (599, base_client.HttpServerError),
    ],
)
async def test_validate_response(status_code: int, side_effect: type[Exception], test_client: FakeClient) -> None:
    response = httpx.Response(
        status_code=status_code,
        content=b"",
        headers=multidict.CIMultiDict(),
    )

    with pytest.raises(side_effect):
        await test_client.validate_response(response=response)


async def test_response_to_model() -> None:
    class TestModel(pydantic.BaseModel):
        status: int

    response = httpx.Response(status_code=httpx.codes.OK, json={"status": httpx.codes.BAD_GATEWAY})
    assert response_to_model(model_type=TestModel, response=response) == TestModel(status=httpx.codes.BAD_GATEWAY)


@pytest.mark.parametrize(
    ("url", "params", "expected_url"),
    [
        (TEST_BASE_URL, [("1", "2")], TEST_BASE_URL + "?1=2"),
        (TEST_BASE_URL + "?1=2", [("3", "4")], TEST_BASE_URL + "?1=2&3=4"),
        (TEST_BASE_URL, {"baz": "bar"}, TEST_BASE_URL + "?baz=bar"),
        (TEST_BASE_URL + "?foo=bar", {"baz": "bar"}, TEST_BASE_URL + "?foo=bar&baz=bar"),
        (httpx.URL(TEST_BASE_URL + "?foo=bar"), {"baz": "bar"}, TEST_BASE_URL + "?foo=bar&baz=bar"),
        (httpx.URL(TEST_BASE_URL + "?1=2"), [("3", "4")], TEST_BASE_URL + "?1=2&3=4"),
    ],
)
async def test_prepare_request(url: str, params: dict[str, str], expected_url: str, test_client: FakeClient) -> None:
    request = test_client.prepare_request(method="GET", url=url, params=params)
    assert request.url == expected_url
